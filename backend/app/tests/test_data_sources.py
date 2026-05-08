from fastapi.testclient import TestClient


def test_get_data_sources_returns_list(client: TestClient):
    resp = client.get("/api/v1/data-sources")
    assert resp.status_code == 200
    sources = resp.json()
    assert isinstance(sources, list)
    assert len(sources) >= 1


def test_data_source_schema(client: TestClient):
    resp = client.get("/api/v1/data-sources")
    src = resp.json()[0]
    assert "id" in src
    assert "name" in src
    assert "status" in src
    assert "features_created" in src
    assert "circuit_state" in src   # Phase 3 addition


def test_imerg_source_present(client: TestClient):
    resp = client.get("/api/v1/data-sources")
    ids = [s["id"] for s in resp.json()]
    assert "imerg" in ids


def test_reliefweb_source_present(client: TestClient):
    resp = client.get("/api/v1/data-sources")
    ids = [s["id"] for s in resp.json()]
    assert "reliefweb" in ids


def test_features_created_is_list(client: TestClient):
    resp = client.get("/api/v1/data-sources")
    for src in resp.json():
        assert isinstance(src["features_created"], list)


def test_status_values_are_valid(client: TestClient):
    resp = client.get("/api/v1/data-sources")
    valid_statuses = {"fresh", "stale", "error", "disabled"}
    for src in resp.json():
        assert src["status"] in valid_statuses


def test_reliefweb_is_fresh(client: TestClient):
    resp = client.get("/api/v1/data-sources")
    rw = next((s for s in resp.json() if s["id"] == "reliefweb"), None)
    assert rw is not None
    assert rw["status"] == "fresh"


def test_stub_adapters_are_stale(client: TestClient):
    resp = client.get("/api/v1/data-sources")
    stubs = [s for s in resp.json() if s["id"] in {"imerg", "chirps", "glofas", "ffd"}]
    for src in stubs:
        assert src["status"] == "stale"
