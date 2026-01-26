"""LLM-powered extraction of structured consumption data from Singapore electricity bill OCR text."""

import json
from typing import Optional
from models.utility_bill import ElectricityBillExtraction, SG_ELECTRICITY_PROVIDERS


EXTRACTION_SYSTEM_PROMPT = """You are an expert Singapore electricity bill parser.

Analyze the provided OCR text from a Singapore electricity bill and extract ALL available information into structured JSON format.

## Singapore Electricity Market Context

### Retailers (Open Electricity Market)
- SP Services (regulated default)
- Geneco, Keppel Electric, Senoko Energy, Tuas Power
- PacificLight, Union Power, Ohm Energy, iSwitch
- Best Electricity, Diamond Electric, Sunseap

### Key Rates and Fees
- GST: 9% (as of 2024)
- Tariff rates set quarterly by Energy Market Authority (EMA)
- Typical residential rate: ~$0.25-0.35/kWh (varies by plan)

### Account Number Formats
- SP Services: 10-digit numeric
- Other retailers: Various formats (alphanumeric)

## Extraction Guidelines

1. **Parse dates** in any format (DD/MM/YYYY, DD MMM YYYY, DD-MMM-YY, etc.) and convert to ISO format (YYYY-MM-DD)

2. **Extract numerical values** with care:
   - kWh readings (consumption, meter readings)
   - Currency amounts in SGD (S$, SGD, $)
   - Remove thousands separators (,)

3. **Identify the provider** from letterhead, logo text, or company mentions

4. **Calculate derived values** if not explicit:
   - billing_days = billing_period_end - billing_period_start
   - daily_average_kwh = consumption_kwh / billing_days

5. **Handle tariff tiers** if bill shows tiered pricing breakdown

6. **Set extraction_confidence** (0.0-1.0):
   - 0.9-1.0: All key fields extracted clearly
   - 0.7-0.9: Most fields extracted, some uncertainty
   - 0.5-0.7: Partial extraction, OCR quality issues
   - Below 0.5: Poor quality, many fields missing

7. **Add extraction_warnings** for:
   - Ambiguous values
   - OCR artifacts (misread characters)
   - Missing expected fields
   - Unusual values that may be errors

8. **If a field cannot be extracted**, leave it as null

IMPORTANT: Respond ONLY with valid JSON matching the ElectricityBillExtraction schema. Do not include any explanation text."""


class ConsumptionExtractor:
    """Service for extracting structured consumption data from OCR text using LLM."""

    def __init__(self, llm=None):
        """Initialize the extractor with an LLM instance.

        Args:
            llm: A LangChain-compatible LLM (e.g., ChatOllama)
        """
        self.llm = llm

    async def extract(self, ocr_text: str) -> ElectricityBillExtraction:
        """Extract structured data from OCR text using LLM.

        Args:
            ocr_text: Raw text extracted via OCR from electricity bill image

        Returns:
            ElectricityBillExtraction with parsed fields

        Raises:
            ValueError: If LLM not initialized
        """
        if not self.llm:
            raise ValueError("LLM not initialized")

        try:
            # Use structured output for reliable JSON parsing
            structured_llm = self.llm.with_structured_output(ElectricityBillExtraction)

            result = await structured_llm.ainvoke([
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": f"Extract data from this Singapore electricity bill:\n\n{ocr_text}"}
            ])

            # Store original text for debugging
            result.raw_ocr_text = ocr_text
            return result

        except Exception as e:
            # If structured output fails, try manual JSON parsing
            return await self._fallback_extract(ocr_text, str(e))

    async def _fallback_extract(self, ocr_text: str, error_msg: str) -> ElectricityBillExtraction:
        """Fallback extraction when structured output fails.

        Uses plain LLM call and manual JSON parsing.
        """
        try:
            response = await self.llm.ainvoke([
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": f"Extract data from this Singapore electricity bill:\n\n{ocr_text}"}
            ])

            # Try to parse JSON from response
            content = response.content
            # Find JSON block if wrapped in markdown
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            data = json.loads(content.strip())
            result = ElectricityBillExtraction(**data)
            result.raw_ocr_text = ocr_text
            return result

        except Exception as fallback_error:
            # Return empty extraction with error
            return ElectricityBillExtraction(
                extraction_confidence=0.0,
                extraction_warnings=[
                    f"Primary extraction failed: {error_msg}",
                    f"Fallback extraction failed: {str(fallback_error)}"
                ],
                raw_ocr_text=ocr_text
            )

    async def extract_with_retry(
        self,
        ocr_text: str,
        max_retries: int = 2
    ) -> ElectricityBillExtraction:
        """Extract with retry logic for robustness.

        Args:
            ocr_text: Raw OCR text
            max_retries: Number of retry attempts (default: 2)

        Returns:
            ElectricityBillExtraction with best extraction attempt
        """
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                result = await self.extract(ocr_text)
                # If extraction has reasonable confidence, return it
                if result.extraction_confidence > 0.3:
                    return result
                # Otherwise, try again if we have retries left
                if attempt < max_retries:
                    continue
                return result
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    continue

        # All retries failed
        return ElectricityBillExtraction(
            extraction_confidence=0.0,
            extraction_warnings=[f"Extraction failed after {max_retries + 1} attempts: {str(last_error)}"],
            raw_ocr_text=ocr_text
        )

    def format_summary(self, extraction: ElectricityBillExtraction) -> str:
        """Format extraction as a human-readable summary.

        Args:
            extraction: The extracted bill data

        Returns:
            Formatted string summary
        """
        lines = ["## Electricity Bill Summary\n"]

        if extraction.provider_name:
            lines.append(f"**Provider:** {extraction.provider_name}")

        if extraction.account_number:
            lines.append(f"**Account:** {extraction.account_number}")

        if extraction.billing_period_start and extraction.billing_period_end:
            lines.append(
                f"**Period:** {extraction.billing_period_start} to {extraction.billing_period_end}"
                + (f" ({extraction.billing_days} days)" if extraction.billing_days else "")
            )

        if extraction.consumption_kwh is not None:
            lines.append(f"\n### Consumption")
            lines.append(f"- **Total:** {extraction.consumption_kwh:.1f} kWh")
            if extraction.daily_average_kwh:
                lines.append(f"- **Daily Average:** {extraction.daily_average_kwh:.1f} kWh/day")

        if extraction.total_amount is not None:
            lines.append(f"\n### Charges")
            lines.append(f"- **Total Amount:** S${extraction.total_amount:.2f}")
            if extraction.energy_charges:
                lines.append(f"- **Energy Charges:** S${extraction.energy_charges:.2f}")
            if extraction.gst_amount:
                lines.append(f"- **GST (9%):** S${extraction.gst_amount:.2f}")

        if extraction.tariff_tiers:
            lines.append(f"\n### Tariff Breakdown")
            for tier in extraction.tariff_tiers:
                if tier.tier_name and tier.amount:
                    lines.append(f"- {tier.tier_name}: S${tier.amount:.2f}")

        if extraction.extraction_warnings:
            lines.append(f"\n### Warnings")
            for warning in extraction.extraction_warnings:
                lines.append(f"- {warning}")

        lines.append(f"\n*Confidence: {extraction.extraction_confidence:.0%}*")

        return "\n".join(lines)
