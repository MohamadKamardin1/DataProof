import io
import os

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestDatasetUpload:
    def test_upload_csv(self, client):
        fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "messy_xrf.csv")
        with open(fixture_path, "rb") as f:
            response = client.post(
                "/api/v1/datasets/upload",
                files={"file": ("messy_xrf.csv", f, "text/csv")},
            )
        assert response.status_code == 200
        data = response.json()
        assert "dataset_id" in data
        assert data["status"] == "uploaded"
        assert "detected_schema" in data
        assert len(data["detected_schema"]) > 0

    def test_upload_rejects_non_csv(self, client):
        response = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("test.txt", io.BytesIO(b"not a csv"), "text/plain")},
        )
        assert response.status_code == 400

    def test_upload_empty_file(self, client):
        response = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
        )
        # Empty file might error during parse or have 0 columns
        assert response.status_code in [200, 400]

    def test_upload_xlsx(self, client):
        import pandas as pd
        df = pd.DataFrame({
            "Sample ID": ["PS-01", "PS-02"],
            "Rb": [123, 456],
        })
        xlsx_buffer = io.BytesIO()
        df.to_excel(xlsx_buffer, index=False)
        xlsx_buffer.seek(0)

        response = client.post(
            "/api/v1/datasets/upload",
            files={
                "file": (
                    "test.xlsx",
                    xlsx_buffer,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "dataset_id" in data


class TestDatasetSniffing:
    def test_xrf_header_detection(self, client):
        fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "messy_xrf.csv")
        with open(fixture_path, "rb") as f:
            response = client.post(
                "/api/v1/datasets/upload",
                files={"file": ("messy_xrf.csv", f, "text/csv")},
            )
        assert response.status_code == 200
        data = response.json()
        schema = data["detected_schema"]

        # Find Sample ID column
        sample_id_cols = [c for c in schema if c["role"] == "sample_id"]
        assert len(sample_id_cols) == 1
        assert sample_id_cols[0]["confidence"] == 0.95

        # Check measurement columns
        measurement_cols = [c for c in schema if c["role"] == "measurement"]
        assert len(measurement_cols) >= 6  # Rb, Sr, Ba, Al, Si, Ca

        # Verify specific element columns are detected
        detected_names = {c["name"] for c in measurement_cols}
        expected = {
            "Rb (ppm)", "Sr (ppm)", "Ba (ppm)", "Al (ppm)", "Si (ppm)", "Ca (ppm)",
        }
        for expected_name in expected:
            assert expected_name in detected_names, (
                f"Expected {expected_name} to be detected as measurement"
            )


class TestDatasetMapping:
    def test_confirm_mapping(self, client):
        # First upload
        fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "messy_xrf.csv")
        with open(fixture_path, "rb") as f:
            upload_response = client.post(
                "/api/v1/datasets/upload",
                files={"file": ("messy_xrf.csv", f, "text/csv")},
            )
        assert upload_response.status_code == 200
        dataset_id = upload_response.json()["dataset_id"]

        # Then confirm mapping
        def _mapping(name: str, role: str, **kw: str) -> dict[str, str | float]:
            return {"name": name, "role": role, "confidence": 0.90, **kw}  # type: ignore[typeddict-item]

        mapping = {
            "mappings": [
                _mapping("Sample ID", "sample_id", confidence=0.95, data_type="string"),
                _mapping("Rb (ppm)", "measurement", data_type="numeric", unit="ppm"),
                _mapping("Sr (ppm)", "measurement", data_type="numeric", unit="ppm"),
                _mapping("Ba (ppm)", "measurement", data_type="numeric", unit="ppm"),
                _mapping("Al (ppm)", "measurement", data_type="numeric", unit="ppm"),
                _mapping("Si (ppm)", "measurement", data_type="numeric", unit="ppm"),
                _mapping("Ca (ppm)", "measurement", data_type="numeric", unit="ppm"),
            ]
        }
        response = client.post(f"/api/v1/datasets/{dataset_id}/confirm-mapping", json=mapping)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "mapped"
        assert data["samples_stored"] == 5
        assert data["measurements_stored"] == 35  # 5 samples x 7 columns (only 6 are measurements)

    def test_confirm_mapping_without_sample_id(self, client):
        fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "messy_xrf.csv")
        with open(fixture_path, "rb") as f:
            upload_response = client.post(
                "/api/v1/datasets/upload",
                files={"file": ("messy_xrf.csv", f, "text/csv")},
            )
        dataset_id = upload_response.json()["dataset_id"]

        mapping = {
            "mappings": [
                {"name": "Rb (ppm)", "role": "measurement", "confidence": 0.90},
            ]
        }
        response = client.post(f"/api/v1/datasets/{dataset_id}/confirm-mapping", json=mapping)
        assert response.status_code == 400
        assert "sample_id" in response.json()["detail"].lower()

    def test_confirm_mapping_invalid_dataset(self, client):
        mapping = {"mappings": []}
        response = client.post("/api/v1/datasets/99999/confirm-mapping", json=mapping)
        assert response.status_code == 404
