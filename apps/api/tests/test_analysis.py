"""Tests for analysis pack discovery, compatibility, and execution."""

import io
import os

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def _upload_and_map(client, fixture_name: str) -> int:
    """Helper: upload a CSV, guess schema, confirm mapping, return dataset_id."""
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

    # Build a default mapping: first column = sample_id, rest = measurement
    mappings = []
    for col in data["detected_schema"]:
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
    return dataset_id


class TestPackDiscovery:
    def test_list_packs_returns_paleoclimate(self):
        response = self._get_client().get("/api/v1/packs")
        assert response.status_code == 200
        packs = response.json()
        pack_ids = {p["id"] for p in packs}
        assert "paleoclimate_xrf" in pack_ids

    def test_pack_has_required_columns(self):
        response = self._get_client().get("/api/v1/packs")
        packs = response.json()
        xrf = next(p for p in packs if p["id"] == "paleoclimate_xrf")
        assert "Rb" in xrf["required_columns"]
        assert "Sr" in xrf["required_columns"]
        assert "Ba" in xrf["required_columns"]
        assert "Al" in xrf["required_columns"]
        assert "Si" in xrf["required_columns"]

    def _get_client(self):
        return TestClient(app)


class TestPackCompatibility:
    def test_compatible_with_xrf_dataset(self, client):
        dataset_id = _upload_and_map(client, "messy_xrf.csv")
        response = client.get(f"/api/v1/datasets/{dataset_id}/compatible-packs")
        assert response.status_code == 200
        packs = response.json()
        pack_ids = {p["id"] for p in packs}
        assert "paleoclimate_xrf" in pack_ids

    def test_incompatible_with_missing_columns(self, client):
        """A dataset missing Rb or Sr should not list paleoclimate_xrf as compatible."""
        import pandas as pd
        df = pd.DataFrame({
            "Sample ID": ["S1", "S2"],
            "Al": [10.0, 20.0],
            "Si": [30.0, 40.0],
            # Missing Rb, Sr, Ba
        })
        csv_buffer = io.BytesIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        upload_resp = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("no_xrf.csv", csv_buffer, "text/csv")},
        )
        assert upload_resp.status_code == 200
        dataset_id = upload_resp.json()["dataset_id"]
        upload_resp.json()

        # Confirm mapping
        mappings = [
            {"name": "Sample ID", "role": "sample_id", "confidence": 0.95, "data_type": "string"},
            {"name": "Al", "role": "measurement", "confidence": 0.90, "data_type": "numeric"},
            {"name": "Si", "role": "measurement", "confidence": 0.90, "data_type": "numeric"},
        ]
        map_resp = client.post(
            f"/api/v1/datasets/{dataset_id}/confirm-mapping",
            json={"mappings": mappings},
        )
        assert map_resp.status_code == 200, map_resp.text

        response = client.get(f"/api/v1/datasets/{dataset_id}/compatible-packs")
        assert response.status_code == 200
        packs = response.json()
        pack_ids = {p["id"] for p in packs}
        assert "paleoclimate_xrf" not in pack_ids


class TestAnalysisExecution:
    def test_analyze_paleoclimate_reference_values(self, client):
        """Verify reference numbers from the prompt:
        sample 5621_6 → Rb/Sr ≈ 3.39, Al/Si ≈ 0.64
        sample 6821-6 → Rb/Sr ≈ 0.86, Al/Si ≈ 0.25
        """
        dataset_id = _upload_and_map(client, "paleoclimate_reference.csv")

        response = client.post(
            f"/api/v1/datasets/{dataset_id}/analyze?pack_id=paleoclimate_xrf"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pack"] == "paleoclimate_xrf"
        assert data["version"] == 1

        # Build lookup: proxy_id -> sample_id -> value
        lookup: dict[str, dict[str, float | None]] = {}
        for r in data["results"]:
            if r["proxy_id"] not in lookup:
                lookup[r["proxy_id"]] = {}
            lookup[r["proxy_id"]][r["sample_id"]] = r["value"]

        # Verify reference values
        assert lookup["rb_sr_ratio"]["5621_6"] is not None
        assert abs(lookup["rb_sr_ratio"]["5621_6"] - 3.39) < 0.01

        assert lookup["al_si_ratio"]["5621_6"] is not None
        assert abs(lookup["al_si_ratio"]["5621_6"] - 0.64) < 0.01

        assert lookup["rb_sr_ratio"]["6821-6"] is not None
        assert abs(lookup["rb_sr_ratio"]["6821-6"] - 0.86) < 0.01

        assert lookup["al_si_ratio"]["6821-6"] is not None
        assert abs(lookup["al_si_ratio"]["6821-6"] - 0.25) < 0.01

    def test_analyze_versioning(self, client):
        """Running analysis twice should produce version 1 and version 2."""
        dataset_id = _upload_and_map(client, "paleoclimate_reference.csv")

        resp1 = client.post(
            f"/api/v1/datasets/{dataset_id}/analyze?pack_id=paleoclimate_xrf"
        )
        assert resp1.status_code == 200
        assert resp1.json()["version"] == 1

        resp2 = client.post(
            f"/api/v1/datasets/{dataset_id}/analyze?pack_id=paleoclimate_xrf"
        )
        assert resp2.status_code == 200
        assert resp2.json()["version"] == 2

    def test_analyze_missing_dataset(self, client):
        response = client.post("/api/v1/datasets/99999/analyze?pack_id=paleoclimate_xrf")
        assert response.status_code == 404

    def test_analyze_missing_pack(self, client):
        dataset_id = _upload_and_map(client, "messy_xrf.csv")
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/analyze?pack_id=non_existent_pack"
        )
        assert response.status_code == 404

    def test_analyze_division_by_zero_returns_null(self, client):
        """Division by zero in a proxy formula should result in null, not crash."""
        import pandas as pd
        df = pd.DataFrame({
            "Sample ID": ["S1"],
            "Rb": [100.0],
            "Sr": [0.0],  # will cause Rb/Sr = division by zero
            "Ba": [50.0],
            "Al": [10.0],
            "Si": [20.0],
            "Ca": [30.0],
        })
        csv_buffer = io.BytesIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        upload_resp = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("zero_sr.csv", csv_buffer, "text/csv")},
        )
        dataset_id = upload_resp.json()["dataset_id"]

        mappings = [
            {"name": "Sample ID", "role": "sample_id", "confidence": 0.95, "data_type": "string"},
            {"name": "Rb", "role": "measurement", "confidence": 0.90, "data_type": "numeric"},
            {"name": "Sr", "role": "measurement", "confidence": 0.90, "data_type": "numeric"},
            {"name": "Ba", "role": "measurement", "confidence": 0.90, "data_type": "numeric"},
            {"name": "Al", "role": "measurement", "confidence": 0.90, "data_type": "numeric"},
            {"name": "Si", "role": "measurement", "confidence": 0.90, "data_type": "numeric"},
            {"name": "Ca", "role": "measurement", "confidence": 0.90, "data_type": "numeric"},
        ]
        client.post(
            f"/api/v1/datasets/{dataset_id}/confirm-mapping",
            json={"mappings": mappings},
        )

        response = client.post(
            f"/api/v1/datasets/{dataset_id}/analyze?pack_id=paleoclimate_xrf"
        )
        assert response.status_code == 200
        data = response.json()

        # Find rb_sr_ratio for S1 — it should be null (division by zero)
        rb_sr_results = [r for r in data["results"] if r["proxy_id"] == "rb_sr_ratio"]
        assert len(rb_sr_results) == 1
        assert rb_sr_results[0]["value"] is None

        # ba_sr_ratio and al_si_ratio should still be computed
        ba_sr_results = [r for r in data["results"] if r["proxy_id"] == "ba_sr_ratio"]
        assert len(ba_sr_results) == 1
        assert ba_sr_results[0]["value"] is not None
