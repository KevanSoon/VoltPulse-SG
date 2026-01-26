"""SeaLion encoder for ASEAN multilingual form analysis.

Uses SeaLion chat API to analyze donor/volunteer forms and extract
structured features for embedding generation. SeaLion is chosen for its
knowledge of ASEAN nations and multilingual capabilities.

API Details:
- Base URL: Set via SEALION_ENDPOINT environment variable
- Endpoint: POST /chat
- Request: {"prompt": "...", "system": "..."}
- Response: OpenAI-compatible format with choices[0].message.content
"""

import os
import httpx
import json
import hashlib
import numpy as np
from typing import List, Optional, Dict, Any
from .base import BaseEncoder


# Feature categories for encoding (used for vector generation)
CAUSE_CATEGORIES = [
    "education", "health", "environment", "poverty", "children",
    "elderly", "disability", "animals", "arts", "sports",
    "disaster_relief", "human_rights", "technology", "agriculture", "housing"
]

ASEAN_COUNTRIES = ["SG", "MY", "TH", "VN", "ID", "PH", "MM", "KH", "LA", "BN"]

LANGUAGES = ["en", "ms", "th", "vi", "id", "tl", "my", "km", "lo", "zh"]

AVAILABILITY_TYPES = ["weekends", "evenings", "flexible", "full_time", "event_based"]

DONOR_TYPES = ["individual", "corporate", "foundation"]

VOLUNTEER_TYPES = ["regular", "event_based", "skilled"]


class SeaLionEncoder(BaseEncoder):
    """SeaLion encoder using chat API for form analysis.

    Uses SeaLion's ASEAN knowledge and multilingual capabilities to:
    1. Analyze form content semantically
    2. Extract structured features
    3. Generate embeddings suitable for similarity matching

    The encoder combines:
    - Feature extraction via SeaLion chat API
    - Deterministic feature hashing for categorical data
    - Semantic scoring from LLM analysis
    """

    # Fixed embedding dimension (matches Supabase EMBED_DIMENSION)
    _feature_dimension: int = 1024

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 3
    ):
        """Initialize SeaLion encoder.

        Args:
            endpoint_url: The SeaLion API base URL. If not provided,
                         reads from SEALION_ENDPOINT environment variable.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retry attempts on failure.
        """
        url = endpoint_url or os.getenv("SEALION_ENDPOINT")
        if not url:
            raise ValueError("SEALION_ENDPOINT environment variable is required")
        self.endpoint_url = url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    @property
    def embedding_dimension(self) -> int:
        """Return the embedding dimension (fixed at 1024)."""
        return self._feature_dimension

    def _build_system_prompt(self) -> str:
        """Build system prompt for SeaLion analysis."""
        return """You are an ASEAN donor/volunteer profile analyzer. Your task is to analyze form data and extract structured features for matching.

Analyze the provided form and respond with a JSON object containing these fields:

1. "causes": List of relevant cause categories from: education, health, environment, poverty, children, elderly, disability, animals, arts, sports, disaster_relief, human_rights, technology, agriculture, housing

2. "cause_scores": Object with scores (0.0-1.0) for each relevant cause based on text sentiment and context

3. "engagement_level": Score from 0.0 to 1.0 indicating commitment level (based on frequency, bio, motivation)

4. "experience_level": Score from 0.0 to 1.0 indicating prior experience

5. "financial_capacity": Score from 0.0 to 1.0 for donors (based on amount range, donor type)

6. "skills_diversity": Score from 0.0 to 1.0 for volunteers (based on skills listed)

7. "language_diversity": Score from 0.0 to 1.0 based on languages spoken

8. "motivation_themes": List of key themes extracted from bio/motivation/goals text

9. "regional_focus": Score from 0.0 to 1.0 indicating focus on ASEAN vs global causes

Respond ONLY with valid JSON, no explanation."""

    async def _call_sealion(self, prompt: str) -> str:
        """Call SeaLion chat API.

        Args:
            prompt: The user prompt to send.

        Returns:
            The response text from SeaLion.

        Raises:
            httpx.HTTPStatusError: If request fails after retries.
        """
        last_error = None

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries):
                try:
                    response = await client.post(
                        f"{self.endpoint_url}/chat",
                        headers={"Content-Type": "application/json"},
                        json={
                            "prompt": prompt,
                            "system": self._build_system_prompt()
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    # Handle OpenAI-compatible format (choices array)
                    if 'choices' in data and len(data['choices']) > 0:
                        choice = data['choices'][0]
                        if 'message' in choice:
                            return choice['message'].get('content', '')
                        if 'text' in choice:
                            return choice['text']
                    # Fallback to simple format
                    return data.get("response", "")
                except httpx.HTTPStatusError as e:
                    last_error = e
                    if e.response.status_code >= 500:
                        continue
                    raise
                except httpx.RequestError as e:
                    last_error = e
                    continue

            if last_error:
                raise last_error
            raise RuntimeError("SeaLion API call failed")

    def _parse_sealion_response(self, response: str) -> Dict[str, Any]:
        """Parse SeaLion JSON response.

        Args:
            response: Raw response text from SeaLion.

        Returns:
            Parsed JSON dictionary, or empty dict if parsing fails.
        """
        try:
            # Try to extract JSON from response (may have extra text)
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        return {}

    def _hash_to_vector(self, text: str, dimension: int, offset: int = 0) -> np.ndarray:
        """Convert text to a deterministic vector using hashing.

        Args:
            text: Text to hash.
            dimension: Output vector dimension.
            offset: Offset into the full embedding space.

        Returns:
            A sparse vector contribution.
        """
        vector = np.zeros(self._feature_dimension, dtype=np.float32)
        if not text:
            return vector

        # Use SHA256 for deterministic hashing
        hash_bytes = hashlib.sha256(text.lower().encode()).digest()

        # Convert to indices and values
        for i in range(0, min(len(hash_bytes), dimension), 2):
            idx = (hash_bytes[i] + offset) % self._feature_dimension
            val = (hash_bytes[i + 1] / 255.0) * 2 - 1  # Normalize to [-1, 1]
            vector[idx] += val

        return vector

    def _encode_categorical(
        self,
        value: str,
        categories: List[str],
        start_idx: int
    ) -> np.ndarray:
        """One-hot encode a categorical value.

        Args:
            value: The value to encode.
            categories: List of possible categories.
            start_idx: Starting index in the embedding vector.

        Returns:
            Embedding contribution from this categorical.
        """
        vector = np.zeros(self._feature_dimension, dtype=np.float32)
        value_lower = value.lower() if value else ""

        for i, cat in enumerate(categories):
            if cat.lower() in value_lower or value_lower in cat.lower():
                idx = (start_idx + i) % self._feature_dimension
                vector[idx] = 1.0
                break

        return vector

    def _encode_multi_categorical(
        self,
        values: List[str],
        categories: List[str],
        start_idx: int
    ) -> np.ndarray:
        """Multi-hot encode a list of categorical values.

        Args:
            values: List of values to encode.
            categories: List of possible categories.
            start_idx: Starting index in the embedding vector.

        Returns:
            Embedding contribution from these categoricals.
        """
        vector = np.zeros(self._feature_dimension, dtype=np.float32)
        values_lower = [v.lower() for v in values] if values else []

        for i, cat in enumerate(categories):
            cat_lower = cat.lower()
            for val in values_lower:
                if cat_lower in val or val in cat_lower:
                    idx = (start_idx + i) % self._feature_dimension
                    vector[idx] = 1.0
                    break

        return vector

    def _build_embedding_from_features(
        self,
        form_text: str,
        features: Dict[str, Any]
    ) -> np.ndarray:
        """Build final embedding from extracted features.

        Combines:
        - Deterministic text hashing (semantic coverage)
        - One-hot/multi-hot categorical encoding
        - Continuous scores from SeaLion analysis

        Args:
            form_text: Original form text for hashing.
            features: Extracted features from SeaLion.

        Returns:
            Final embedding vector of shape (1024,).
        """
        embedding = np.zeros(self._feature_dimension, dtype=np.float32)

        # Section 1 (indices 0-255): Text hash for semantic similarity
        embedding += self._hash_to_vector(form_text, 256, offset=0)

        # Section 2 (indices 256-511): Cause categories
        causes = features.get("causes", [])
        embedding += self._encode_multi_categorical(causes, CAUSE_CATEGORIES, 256)

        # Section 3 (indices 512-527): Cause scores
        cause_scores = features.get("cause_scores", {})
        for i, cause in enumerate(CAUSE_CATEGORIES):
            idx = 512 + i
            if cause in cause_scores:
                embedding[idx] = float(cause_scores[cause])

        # Section 4 (indices 528-537): Country encoding
        # Extract country from form text
        for i, country in enumerate(ASEAN_COUNTRIES):
            if country.lower() in form_text.lower():
                embedding[528 + i] = 1.0

        # Section 5 (indices 538-547): Language encoding
        for i, lang in enumerate(LANGUAGES):
            if lang.lower() in form_text.lower():
                embedding[538 + i] = 1.0

        # Section 6 (indices 548-557): Continuous scores
        embedding[548] = features.get("engagement_level", 0.5)
        embedding[549] = features.get("experience_level", 0.5)
        embedding[550] = features.get("financial_capacity", 0.5)
        embedding[551] = features.get("skills_diversity", 0.5)
        embedding[552] = features.get("language_diversity", 0.5)
        embedding[553] = features.get("regional_focus", 0.5)

        # Section 7 (indices 558-600): Donor/volunteer type encoding
        embedding += self._encode_categorical(
            form_text, DONOR_TYPES, 558
        )
        embedding += self._encode_categorical(
            form_text, VOLUNTEER_TYPES, 563
        )
        embedding += self._encode_categorical(
            form_text, AVAILABILITY_TYPES, 568
        )

        # Section 8 (indices 600-1023): Motivation themes hash
        themes = features.get("motivation_themes", [])
        if themes:
            themes_text = " ".join(themes)
            embedding += self._hash_to_vector(themes_text, 424, offset=600)

        # Normalize the embedding
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    async def encode(self, text: str) -> np.ndarray:
        """Encode form text using SeaLion analysis.

        Process:
        1. Send form text to SeaLion for semantic analysis
        2. Parse extracted features from response
        3. Build embedding from features + text hashing

        Args:
            text: The form text to encode.

        Returns:
            A numpy array of shape (1024,).
        """
        # Get SeaLion analysis
        response = await self._call_sealion(
            f"Analyze this donor/volunteer form:\n\n{text}"
        )
        features = self._parse_sealion_response(response)

        # Build embedding from features
        return self._build_embedding_from_features(text, features)

    async def encode_batch(self, texts: List[str]) -> np.ndarray:
        """Encode multiple form texts.

        Note: This makes sequential API calls since the SeaLion API
        doesn't support batch requests.

        Args:
            texts: List of form texts to encode.

        Returns:
            A numpy array of shape (len(texts), 1024).
        """
        if not texts:
            return np.zeros((0, self._feature_dimension), dtype=np.float32)

        embeddings = []
        for text in texts:
            emb = await self.encode(text)
            embeddings.append(emb)

        return np.vstack(embeddings)
