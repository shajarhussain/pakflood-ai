"""
Phase 5 — API endpoint tests for /explain-risk and /alerts/generate-draft.

All tests use TestClient + existing conftest mocks (no real DB, no live APIs).
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── GET /explain-risk/by-boundary/{id} ───────────────────────────────────────

class TestExplainRiskEndpoint:
    def test_returns_200_for_known_district(self):
        resp = client.get("/api/v1/explain-risk/by-boundary/PK-SD-SKR")
        assert resp.status_code == 200

    def test_returns_404_for_unknown_district(self):
        resp = client.get("/api/v1/explain-risk/by-boundary/PK-XX-FAKE")
        assert resp.status_code == 404

    def test_response_has_all_7_fields(self):
        resp = client.get("/api/v1/explain-risk/by-boundary/PK-SD-SKR")
        data = resp.json()
        required = {"risk_level", "main_causes", "historical_evidence",
                    "suggested_actions", "confidence", "data_sources", "disclaimer"}
        assert required.issubset(data.keys())

    def test_risk_level_is_valid(self):
        resp = client.get("/api/v1/explain-risk/by-boundary/PK-SD-SKR")
        assert resp.json()["risk_level"] in {"Low", "Moderate", "High", "Severe"}

    def test_confidence_in_range(self):
        resp = client.get("/api/v1/explain-risk/by-boundary/PK-SD-SKR")
        c = resp.json()["confidence"]
        assert 0.0 <= c <= 1.0

    def test_all_list_fields_are_lists(self):
        resp = client.get("/api/v1/explain-risk/by-boundary/PK-SD-SKR")
        data = resp.json()
        for field in ("main_causes", "historical_evidence", "suggested_actions", "data_sources"):
            assert isinstance(data[field], list), f"{field} is not a list"

    def test_main_causes_not_empty(self):
        resp = client.get("/api/v1/explain-risk/by-boundary/PK-SD-SKR")
        assert len(resp.json()["main_causes"]) >= 1

    def test_suggested_actions_not_empty(self):
        resp = client.get("/api/v1/explain-risk/by-boundary/PK-SD-SKR")
        assert len(resp.json()["suggested_actions"]) >= 1

    def test_disclaimer_present_and_non_empty(self):
        resp = client.get("/api/v1/explain-risk/by-boundary/PK-SD-SKR")
        disclaimer = resp.json()["disclaimer"]
        assert isinstance(disclaimer, str) and len(disclaimer) > 10

    def test_disclaimer_does_not_claim_official_warning(self):
        resp = client.get("/api/v1/explain-risk/by-boundary/PK-SD-SKR")
        disclaimer = resp.json()["disclaimer"].lower()
        assert "official warning from" not in disclaimer
        assert "official government warning" not in disclaimer

    def test_second_district_also_returns_200(self):
        resp = client.get("/api/v1/explain-risk/by-boundary/PK-SD-JCB")
        assert resp.status_code == 200

    def test_historical_evidence_present(self):
        resp = client.get("/api/v1/explain-risk/by-boundary/PK-SD-SKR")
        evidence = resp.json()["historical_evidence"]
        assert isinstance(evidence, list) and len(evidence) >= 1

    def test_data_sources_present(self):
        resp = client.get("/api/v1/explain-risk/by-boundary/PK-SD-SKR")
        sources = resp.json()["data_sources"]
        assert isinstance(sources, list) and len(sources) >= 1


# ── POST /alerts/generate-draft ───────────────────────────────────────────────

class TestAlertDraftEndpoint:
    def test_returns_200(self):
        resp = client.post("/api/v1/alerts/generate-draft", json={"boundary_id": "PK-SD-SKR"})
        assert resp.status_code == 200

    def test_returns_404_for_unknown_district(self):
        resp = client.post("/api/v1/alerts/generate-draft", json={"boundary_id": "PK-XX-FAKE"})
        assert resp.status_code == 404

    def test_response_schema(self):
        resp = client.post("/api/v1/alerts/generate-draft", json={"boundary_id": "PK-SD-SKR"})
        data = resp.json()
        required = {"headline", "severity", "area", "description",
                    "instruction", "sources", "confidence", "disclaimer",
                    "is_draft", "is_official"}
        assert required.issubset(data.keys())

    def test_is_draft_always_true(self):
        resp = client.post("/api/v1/alerts/generate-draft", json={"boundary_id": "PK-SD-SKR"})
        assert resp.json()["is_draft"] is True

    def test_is_official_always_false(self):
        resp = client.post("/api/v1/alerts/generate-draft", json={"boundary_id": "PK-SD-SKR"})
        assert resp.json()["is_official"] is False

    def test_headline_contains_draft_marker(self):
        resp = client.post("/api/v1/alerts/generate-draft", json={"boundary_id": "PK-SD-SKR"})
        headline = resp.json()["headline"]
        assert "[DRAFT]" in headline or "DRAFT" in headline.upper()

    def test_disclaimer_says_not_sent(self):
        resp = client.post("/api/v1/alerts/generate-draft", json={"boundary_id": "PK-SD-SKR"})
        disclaimer = resp.json()["disclaimer"].upper()
        assert "NOT SENT" in disclaimer or "DRAFT" in disclaimer

    def test_severity_is_valid_cap_level(self):
        valid = {"Minor", "Moderate", "Severe", "Extreme"}
        resp = client.post("/api/v1/alerts/generate-draft", json={"boundary_id": "PK-SD-SKR"})
        assert resp.json()["severity"] in valid

    def test_confidence_in_range(self):
        resp = client.post("/api/v1/alerts/generate-draft", json={"boundary_id": "PK-SD-SKR"})
        c = resp.json()["confidence"]
        assert 0.0 <= c <= 1.0

    def test_description_does_not_claim_official(self):
        resp = client.post("/api/v1/alerts/generate-draft", json={"boundary_id": "PK-SD-SKR"})
        desc = resp.json()["description"].lower()
        assert "official government warning" not in desc

    def test_area_contains_district_name(self):
        resp = client.post("/api/v1/alerts/generate-draft", json={"boundary_id": "PK-SD-SKR"})
        area = resp.json()["area"]
        assert "Sukkur" in area or "Sindh" in area
