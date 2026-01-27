"""OpenAI Vision-based extraction of structured data from Singapore utility bills.

Replaces PaddleOCR with OpenAI Vision for better text AND chart understanding.
"""

import base64
import json
import os
from typing import Optional

from openai import AsyncOpenAI
from models.utility_bill import ElectricityBillExtraction


VISION_EXTRACTION_PROMPT = """You are an expert Singapore utility bill analyzer with computer vision capabilities.

Analyze this Singapore SP Group utility bill image and extract ALL information including:

## 1. TEXT EXTRACTION
- Account number, customer name, address
- Billing period dates, bill date, due date
- All monetary amounts (charges, GST, totals)
- Provider names for each service

## 2. CONSUMPTION VALUES
For each service (Electricity, Gas, Water):
- Current period usage and units
- Charges in SGD

## 3. BAR CHART ANALYSIS (CRITICAL)
The bill contains consumption trend bar charts. You MUST read these charts carefully:

For each bar chart (Electricity, Gas, Water):
- Read the Y-axis scale and units (kWh for electricity/gas, Cu M for water)
- Extract the value for EACH month shown (typically 6 months: DEC, JAN, FEB, MAR, APR, MAY or similar)
- Note the dotted line showing "Neighbour average"
- Note the solid line showing "National average"
- Determine if consumption is trending up, down, or stable

## 4. ADDITIONAL DETAILS
- Refuse removal charges if shown
- Any rebates or adjustments
- Payment instructions
- Deposit amount

Return ONLY valid JSON matching this exact schema:

{
  "account_number": "string or null",
  "customer_name": "string or null",
  "premise_address": "string or null",
  "billing_period_start": "YYYY-MM-DD or null",
  "billing_period_end": "YYYY-MM-DD or null",
  "bill_date": "YYYY-MM-DD or null",
  "due_date": "YYYY-MM-DD or null",
  "billing_days": "integer or null",

  "consumption_kwh": "float - electricity usage in kWh",
  "previous_reading": "float or null",
  "current_reading": "float or null",
  "meter_number": "string or null",
  "daily_average_kwh": "float or null",

  "gas_usage_kwh": "float - gas usage in kWh or null",
  "gas_charges": "float - gas charges in SGD or null",
  "gas_provider": "string or null",

  "water_usage_cu_m": "float - water usage in Cu M or null",
  "water_charges": "float - water charges in SGD or null",
  "water_provider": "string or null",

  "consumption_trends": [
    {
      "service_type": "Electricity",
      "monthly_data": [
        {"month": "DEC", "value": 253, "unit": "kWh"},
        {"month": "JAN", "value": 241, "unit": "kWh"},
        ...
      ],
      "neighbour_average": "float from dotted line or null",
      "national_average": "float from solid line or null",
      "trend_direction": "increasing/decreasing/stable"
    },
    {
      "service_type": "Gas",
      "monthly_data": [...],
      ...
    },
    {
      "service_type": "Water",
      "monthly_data": [...],
      ...
    }
  ],

  "total_amount": "float - total current charges in SGD",
  "energy_charges": "float - electricity charges in SGD or null",
  "gst_amount": "float - GST amount or null",
  "other_charges": "float - other charges or null",
  "previous_balance": "float or null",

  "provider_name": "string - main provider (SP Services, etc.)",
  "plan_name": "string or null",

  "extraction_confidence": "float 0.0-1.0",
  "extraction_warnings": ["list of any issues or uncertainties"]
}

IMPORTANT:
- For bar charts, estimate values by reading the bar heights against the Y-axis scale
- Include ALL months shown in the charts
- If a value is unclear, provide your best estimate and add a warning
- Dates should be in ISO format (YYYY-MM-DD)
- All monetary values are in SGD"""


class VisionExtractor:
    """Service for extracting structured data from utility bill images using OpenAI Vision."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        """Initialize the vision extractor.

        Args:
            api_key: OpenAI API key. If not provided, reads from OPENAI_API_KEY env var.
            model: OpenAI model to use (default: gpt-4o for best vision capabilities)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY env var or pass api_key.")

        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = model

    @staticmethod
    def encode_image(image_path: str) -> str:
        """Encode an image file to base64 string.

        Args:
            image_path: Path to the image file

        Returns:
            Base64 encoded string of the image
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    @staticmethod
    def encode_image_bytes(image_bytes: bytes) -> str:
        """Encode image bytes to base64 string.

        Args:
            image_bytes: Raw image bytes

        Returns:
            Base64 encoded string of the image
        """
        return base64.b64encode(image_bytes).decode("utf-8")

    def _get_media_type(self, filename: str) -> str:
        """Get MIME type from filename extension."""
        ext = filename.lower().split(".")[-1] if filename else "png"
        media_types = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp",
            "bmp": "image/bmp",
        }
        return media_types.get(ext, "image/png")

    async def extract_from_path(self, image_path: str) -> ElectricityBillExtraction:
        """Extract bill data from an image file path.

        Args:
            image_path: Path to the utility bill image

        Returns:
            ElectricityBillExtraction with all extracted data
        """
        base64_image = self.encode_image(image_path)
        media_type = self._get_media_type(image_path)
        return await self._extract(base64_image, media_type)

    async def extract_from_bytes(
        self,
        image_bytes: bytes,
        filename: Optional[str] = None
    ) -> ElectricityBillExtraction:
        """Extract bill data from image bytes.

        Args:
            image_bytes: Raw image bytes
            filename: Optional filename for determining media type

        Returns:
            ElectricityBillExtraction with all extracted data
        """
        base64_image = self.encode_image_bytes(image_bytes)
        media_type = self._get_media_type(filename or "image.png")
        return await self._extract(base64_image, media_type)

    async def _extract(
        self,
        base64_image: str,
        media_type: str
    ) -> ElectricityBillExtraction:
        """Internal extraction method using OpenAI Vision API.

        Args:
            base64_image: Base64 encoded image
            media_type: MIME type of the image

        Returns:
            ElectricityBillExtraction with extracted data
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": VISION_EXTRACTION_PROMPT
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{base64_image}",
                                    "detail": "high"  # Use high detail for better chart reading
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4096,
                temperature=0.1  # Low temperature for more consistent extraction
            )

            # Parse the response
            content = response.choices[0].message.content

            # Extract JSON from response (handle markdown code blocks)
            json_str = content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]

            data = json.loads(json_str.strip())

            # Store raw response for debugging
            data["raw_ocr_text"] = f"[OpenAI Vision extraction - model: {self.model}]"

            return ElectricityBillExtraction(**data)

        except json.JSONDecodeError as e:
            return ElectricityBillExtraction(
                extraction_confidence=0.0,
                extraction_warnings=[
                    f"Failed to parse JSON response: {str(e)}",
                    f"Raw response: {content[:500]}..."
                ],
                raw_ocr_text=content
            )
        except Exception as e:
            return ElectricityBillExtraction(
                extraction_confidence=0.0,
                extraction_warnings=[f"Vision extraction failed: {str(e)}"],
            )

    async def extract_with_retry(
        self,
        image_bytes: bytes,
        filename: Optional[str] = None,
        max_retries: int = 2
    ) -> ElectricityBillExtraction:
        """Extract with retry logic for robustness.

        Args:
            image_bytes: Raw image bytes
            filename: Optional filename
            max_retries: Number of retry attempts

        Returns:
            ElectricityBillExtraction with best extraction attempt
        """
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                result = await self.extract_from_bytes(image_bytes, filename)
                if result.extraction_confidence > 0.3:
                    return result
                if attempt < max_retries:
                    continue
                return result
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    continue

        return ElectricityBillExtraction(
            extraction_confidence=0.0,
            extraction_warnings=[
                f"Extraction failed after {max_retries + 1} attempts: {str(last_error)}"
            ],
        )
