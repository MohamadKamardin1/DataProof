def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "DataProof API"


def test_health_endpoint_returns_valid_structure(client):
    response = client.get("/health")
    assert response.status_code in [200, 503]

    data = response.json()
    assert "status" in data
    assert data["status"] in ["healthy", "degraded", "unhealthy"]
    assert "version" in data
    assert "timestamp" in data
    assert "checks" in data
    assert isinstance(data["checks"], dict)
    assert "database" in data["checks"]
    assert "redis" in data["checks"]
    assert "minio" in data["checks"]
