"""Integration tests for the interpretation API endpoint.

Tests cover:
- Starting an interpretation job (requires analysis first)
- Polling job status
- Error handling for missing datasets / packs / analysis
"""
import io
import os
from unittest.mock import patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def _upload_and_analyze(
    client, fixture_name: str = "messy_xrf.csv", pack_id: str = "paleoclimate_xrf"
) -> int:
    """Helper: upload CSV, confirm mapping, run analysis, return dataset_id."""
    fixture_path = os.path.join(
        os.path.dirname(__file__), "fixtures", fixture_name
    )
    with open(fixture_path, "rb") as f:
        upload_resp = client.post(
            "/api/v1/datasets/upload",
            files={"file": (fixture_name, f, "text/csv")},
        )
    assert upload_resp.status_code == 200
    data = upload_resp.json()
    dataset_id = data["dataset_id"]
    schema = data["detected_schema"]

    # Build a default mapping
    mappings = []
    for col in schema:
        role = "sample_id" if col["role"] == "sample_id" else "measurement"
        mappings.append({
            "name": col["name"],
            "role": role,
            "confidence": col["confidence"],
            "unit": col.get("unit"),
            "data_type": col.get("data_type", "numeric"),
        })

    map_resp = client.post(
        f"/api/v1/datasets/{dataset_id}/confirm-mapping",
        json={"mappings": mappings},
    )
    assert map_resp.status_code == 200

    # Run analysis
    analysis_resp = client.post(
        f"/api/v1/datasets/{dataset_id}/analyze?pack_id={pack_id}"
    )
    assert analysis_resp.status_code == 200

    return dataset_id


VALID_LLM_RESPONSE = {
    "per_sample": [
        {
            "sample_id": "5621_6",
            "classification": "Strong chemical weathering",
            "rationale": "Rb/Sr=3.39 indicates advanced weathering; Al/Si=0.64 confirms clay.",
        },
        {
            "sample_id": "6821-6",
            "classification": "Weak chemical weathering",
            "rationale": "Rb/Sr=0.86 indicates minor weathering; Al/Si=0.25 suggests primary.",
        },
    ],
    "overall_narrative": "5621_6 shows strong weathering (Rb/Sr=3.39), while 6821-6 shows weak (Rb/Sr=0.86).",  # noqa: E501
    "citations": [
        {
            "authors": "Chen, J.",
            "year": 1999,
            "title": "Rb/Sr ratios in loess-paleosol sequences",
            "venue": "EPSL",
            "doi_or_url": "10.1016/S0012-821X(99)00066-5",
        }
    ],
}


class TestInterpretationEndpoint:
    def test_start_interpretation_requires_analysis_first(self, client):
        """A dataset with no analysis should return 400."""
        _upload_and_analyze(client)
        df = pd.DataFrame({
            "Sample ID": ["S1"],
            "Rb": [100.0],
            "Sr": [50.0],
        })
        csv_buffer = io.BytesIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        upload_resp = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("no_analysis.csv", csv_buffer, "text/csv")},
        )
        assert upload_resp.status_code == 200
        new_ds_id = upload_resp.json()["dataset_id"]

        # Confirm mapping
        client.post(
            f"/api/v1/datasets/{new_ds_id}/confirm-mapping",
            json={"mappings": [
                {"name": "Sample ID", "role": "sample_id", "confidence": 0.95, "data_type": "string"},  # noqa: E501
                {"name": "Rb", "role": "measurement", "confidence": 0.90, "data_type": "numeric"},
                {"name": "Sr", "role": "measurement", "confidence": 0.90, "data_type": "numeric"},
            ]},
        )

        # Try to interpret without analysis
        resp = client.post(f"/api/v1/datasets/{new_ds_id}/interpret")
        assert resp.status_code == 400
        assert "analysis" in resp.json()["detail"].lower()

    def test_start_interpretation_nonexistent_dataset(self, client):
        resp = client.post("/api/v1/datasets/99999/interpret")
        assert resp.status_code == 404

    def test_start_interpretation_nonexistent_pack(self, client):
        dataset_id = _upload_and_analyze(client)
        resp = client.post(
            f"/api/v1/datasets/{dataset_id}/interpret?pack_id=nonexistent"
        )
        assert resp.status_code == 404

    @patch("api.tasks.interpret_dataset_task.delay")
    def test_start_interpretation_returns_job_id(self, mock_task, client):
        """Starting an interpretation should return a job_id and status_url."""
        mock_task.return_value.id = "test-job-123"
        dataset_id = _upload_and_analyze(client)

        resp = client.post(f"/api/v1/datasets/{dataset_id}/interpret")
        assert resp.status_code == 202
        data = resp.json()
        assert "job_id" in data
        assert "status_url" in data

    def test_get_job_status_pending(self, client):
        """Polling a non-existent job_id returns failure."""
        resp = client.get("/api/v1/jobs/nonexistent-job")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("pending", "failed")
