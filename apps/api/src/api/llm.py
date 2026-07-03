"""LLM interpretation engine — DeepSeek integration.

This module constructs prompts from computed proxy results only (never raw
measurements) and parses the LLM's JSON response against the strict schema.
"""
import json
from typing import Any

import httpx

from api.config import settings
from api.logging import logger
from api.models.analysis import AnalysisPack, ProxyResult
from api.models.interpretation import LLMInterpretationResponse

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"


class DeepSeekEngine:
    """Calls DeepSeek chat completions API with a structured prompt."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.deepseek_api_key

    def interpret(
        self, pack: AnalysisPack, results: list[ProxyResult], max_retries: int = 1
    ) -> LLMInterpretationResponse:
        """Send proxy results to DeepSeek and parse the JSON response.

        Raises:
            ValueError: if the API key is missing or the response is invalid after retries.
            httpx.HTTPError: if the API call fails.
        """
        if not self.api_key:
            raise ValueError("DeepSeek API key is not configured")

        prompt = self._build_prompt(pack, results)

        last_error: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                raw = self._call_deepseek(prompt)
                parsed = self._parse_response(raw)
                return parsed
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("llm_parse_retry", attempt=attempt, error=str(e))
                last_error = e
                if attempt < max_retries:
                    prompt += (
                        "\n\nYour previous response was not valid JSON"
                        " matching the required schema. "
                        "Please return ONLY valid JSON"
                        " matching the exact format specified."
                    )

        raise ValueError(
            f"Failed to parse LLM response after {max_retries + 1} attempts:"
            f" {last_error}"
        )

    def _build_prompt(self, pack: AnalysisPack, results: list[ProxyResult]) -> str:
        """Build the LLM prompt from computed proxy results only — never raw data."""
        system_prompt = pack.interpretation_prompt or (
            f"Interpret the {pack.name} analysis results for this dataset."
        )

        # Group results by sample
        samples: dict[str, dict[str, Any]] = {}
        for r in results:
            if r.sample_id not in samples:
                samples[r.sample_id] = {}
            samples[r.sample_id][r.proxy_id] = {
                "label": r.label,
                "value": r.value,
                "unit": r.unit,
            }

        # Build the data section with computed proxies only
        data_lines = ["## Computed Proxy Results"]
        data_lines.append("")
        for sid, proxies in samples.items():
            data_lines.append(f"### Sample: {sid}")
            for _pid, info in proxies.items():
                val_str = f"{info['value']:.4f}" if info['value'] is not None else "N/A"
                unit_str = f" {info['unit']}" if info['unit'] else ""
                data_lines.append(f"  - {info['label']}: {val_str}{unit_str}")
        data_section = "\n".join(data_lines)

        prompt = f"""{system_prompt}

{data_section}

You MUST respond with ONLY valid JSON in the following format
— no markdown, no explanation outside the JSON:

{{
  "per_sample": [
    {{
      "sample_id": "...",
      "classification": "brief classification label",
      "rationale": "scientific rationale referencing specific proxy values"
    }}
  ],
  "overall_narrative": "Paragraph synthesizing the overall scientific interpretation.",
  "citations": [
    {{
      "authors": "Author, A.",
      "year": 2020,
      "title": "Full paper title",
      "venue": "Journal Name or 'Unpublished'",
      "doi_or_url": "DOI or URL if available"
    }}
  ]
}}

Requirements:
- Every numeric claim in the narrative must reference a computed proxy value from the data above.
- Do NOT compute any new ratios or values — only interpret what is provided.
- Citations should be real, published, relevant papers. If you are unsure, omit the citation.
- Return valid JSON only."""
        return prompt

    def _call_deepseek(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "You are a scientific data interpreter. Respond in valid JSON only."},  # noqa: E501
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,  # Low temperature for more deterministic output
            "max_tokens": 4096,
        }

        logger.info("llm_call_start", model="deepseek-chat")
        with httpx.Client(timeout=120.0) as client:
            response = client.post(DEEPSEEK_API_URL, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            logger.info("llm_call_success", tokens=len(content))
            return content

    def _parse_response(self, raw: str) -> LLMInterpretationResponse:
        """Parse and validate LLM response against the strict Pydantic schema.

        Handles the common case where the LLM wraps JSON in markdown code fences.
        """
        text = raw.strip()

        # Strip markdown code fences if present
        if "```" in text:
            lines = text.splitlines()
            cleaned: list[str] = []
            in_code = False
            for line in lines:
                if line.strip().startswith("```"):
                    in_code = not in_code
                    continue
                if in_code:
                    cleaned.append(line)
            if cleaned:
                text = "\n".join(cleaned).strip()

        parsed = json.loads(text)
        return LLMInterpretationResponse.model_validate(parsed)
