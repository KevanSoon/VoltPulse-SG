"""Base encoder abstract class."""

from abc import ABC, abstractmethod
from typing import List
import numpy as np


class BaseEncoder(ABC):
    """Base class for text encoders.

    Provides a common interface for encoding text into vector embeddings.
    Implementations can use different models (SeaLion, OpenAI, etc.).
    """

    @property
    @abstractmethod
    def embedding_dimension(self) -> int:
        """Return the native embedding dimension of this encoder."""
        pass

    @abstractmethod
    async def encode(self, text: str) -> np.ndarray:
        """Encode a single text into a vector.

        Args:
            text: The text to encode.

        Returns:
            A numpy array of shape (embedding_dimension,).
        """
        pass

    @abstractmethod
    async def encode_batch(self, texts: List[str]) -> np.ndarray:
        """Encode multiple texts into vectors (batch processing).

        Args:
            texts: List of texts to encode.

        Returns:
            A numpy array of shape (len(texts), embedding_dimension).
        """
        pass
