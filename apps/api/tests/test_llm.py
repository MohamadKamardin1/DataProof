"""Tests for the DeepSeek LLM interpretation engine."""

import json
from unittest.mock import Mock, patch

import pytest

from api.llm import DeepSeekEngine
from api.models.analysis import AnalysisPack, ProxyDef, ProxyResult
from api.models.interpretation import LLMInterpretationResponse

SAMPLE_PACK = AnalysisPack(
    id="test_pack",
    name="Test Pack",
    description="A test analysis pack",
    required_columns=["Rb", "Sr", "Al", "Si"],
    proxies=[
        ProxyDef(
            id="rb_sr",
            label="Rb/Sr",
            formula="Rb / Sr",
            unit="ratio",
        ),
        ProxyDef(
            id="al_si",
            label="Al/Si",
            formula="Al / Si",
            unit="ratio",
        ),
    ],
    interpretation_prompt="Interpret the geochemical data focusing on weathering regimes.",
)

SAMPLE_PROXY_RESULTS = [
    ProxyResult(
        proxy_id="rb_sr",
        label="Rb/Sr",
        sample_id="S1",
        value=3.39,
        unit="ratio",
    ),
    ProxyResult(
        proxy_id="al_si",
        label="Al/Si",
        sample_id="S1",
        value=0.64,
        unit="ratio",
    ),
    ProxyResult(
        proxy_id="rb_sr",
        label="Rb/Sr",
        sample_id="S2",
        value=0.86,
        unit="ratio",
    ),
    ProxyResult(
        proxy_id="al_si",
        label="Al/Si",
        sample_id="S2",
        value=0.25,
        unit="ratio",
    ),
]

VALID_LLM_RESPONSE = {
    "per_sample": [
        {
            "sample_id": "S1",
            "classification": "Strong chemical weathering",
            "rationale": "Rb/Sr=3.39 indicates advanced weathering; Al/Si=0.64 suggests clay.",
        },
        {
            "sample_id": "S2",
            "classification": "Weak chemical weathering",
            "rationale": "Rb/Sr=0.86 indicates minor weathering; Al/Si=0.25 suggests primary.",
        },
    ],
    "overall_narrative": "S1 (Rb/Sr=3.39, Al/Si=0.64) shows strong weathering.",  # noqa: E501
    "citations": [
        {
            "authors": "Chen, J.",
            "year": 1999,
            "title": "Rb/Sr ratios in loess-paleosol sequences",
            "venue": "Earth and Planetary Science Letters",
            "doi_or_url": "10.1016/S0012-821X(99)00066-5",
        }
    ],
}


class TestDeepSeekEngine:
    def test_build_prompt_includes_proxy_values_only(self):
        """Prompt must contain computed proxy values, never raw data."""
        engine = DeepSeekEngine(api_key="test-key")
        prompt = engine._build_prompt(SAMPLE_PACK, SAMPLE_PROXY_RESULTS)

        # Prompt should include proxy values
        assert "Rb/Sr: 3.3900" in prompt
        assert "Al/Si: 0.6400" in prompt

        # Prompt should NOT contain the word "raw" in this context
        assert "Raw Data" not in prompt
        assert "measurement" not in prompt.lower()

    def test_build_prompt_uses_interpretation_prompt_from_pack(self):
        engine = DeepSeekEngine(api_key="test-key")
        prompt = engine._build_prompt(SAMPLE_PACK, SAMPLE_PROXY_RESULTS)

        assert "weathering regimes" in prompt

    def test_parse_response_valid_json(self):
        engine = DeepSeekEngine(api_key="test-key")
        raw = json.dumps(VALID_LLM_RESPONSE)
        parsed = engine._parse_response(raw)

        assert isinstance(parsed, LLMInterpretationResponse)
        assert len(parsed.per_sample) == 2
        assert parsed.per_sample[0].sample_id == "S1"
        assert parsed.per_sample[0].classification == "Strong chemical weathering"
        assert len(parsed.citations) == 1
        assert parsed.citations[0].authors == "Chen, J."

    def test_parse_response_strips_markdown_fences(self):
        engine = DeepSeekEngine(api_key="test-key")
        raw = f"```json\n{json.dumps(VALID_LLM_RESPONSE)}\n```"
        parsed = engine._parse_response(raw)
        assert parsed.per_sample[0].sample_id == "S1"

    def test_parse_response_strips_markdown_without_lang(self):
        engine = DeepSeekEngine(api_key="test-key")
        raw = f"```\n{json.dumps(VALID_LLM_RESPONSE)}\n```"
        parsed = engine._parse_response(raw)
        assert parsed.per_sample[0].sample_id == "S1"

    def test_parse_response_invalid_json_raises(self):
        engine = DeepSeekEngine(api_key="test-key")
        with pytest.raises(json.JSONDecodeError):
            engine._parse_response("this is not valid json")

    def test_parse_response_missing_fields_raises(self):
        engine = DeepSeekEngine(api_key="test-key")
        bad_response = {
            "per_sample": [{"sample_id": "S1"}],  # missing classification and rationale
        }
        with pytest.raises(ValueError):
            engine._parse_response(json.dumps(bad_response))

    @patch("api.llm.httpx.Client")
    def test_interpret_success(self, mock_client_class):
        mock_client = Mock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(VALID_LLM_RESPONSE)}}]
        }
        mock_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_response

        engine = DeepSeekEngine(api_key="test-key")
        result = engine.interpret(SAMPLE_PACK, SAMPLE_PROXY_RESULTS)

        assert result.per_sample[0].classification == "Strong chemical weathering"

    @patch("api.llm.httpx.Client")
    def test_interpret_retries_on_bad_json(self, mock_client_class):
        mock_client = Mock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        call_count = [0]

        def mock_post(*args, **kwargs):
            call_count[0] += 1
            mock_response = Mock()
            if call_count[0] <= 1:
                mock_response.json.return_value = {
                    "choices": [{"message": {"content": "not json"}}]
                }
            else:
                mock_response.json.return_value = {
                    "choices": [{"message": {"content": json.dumps(VALID_LLM_RESPONSE)}}]
                }
            mock_response.raise_for_status = Mock()
            return mock_response

        mock_client.post.side_effect = mock_post

        engine = DeepSeekEngine(api_key="test-key")
        result = engine.interpret(SAMPLE_PACK, SAMPLE_PROXY_RESULTS, max_retries=1)

        assert call_count[0] == 2
        assert result.per_sample[0].sample_id == "S1"

    def test_interpret_missing_api_key(self):
        engine = DeepSeekEngine(api_key="")
        with pytest.raises(ValueError, match="API key is not configured"):
            engine.interpret(SAMPLE_PACK, SAMPLE_PROXY_RESULTS)
