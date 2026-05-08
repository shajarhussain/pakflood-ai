from app.hazards.flood.rules import classify_risk


def test_risk_level_thresholds() -> None:
    assert classify_risk(0.10) == "Low"
    assert classify_risk(0.45) == "Moderate"
    assert classify_risk(0.70) == "High"
    assert classify_risk(0.90) == "Severe"


def test_boundary_values() -> None:
    assert classify_risk(0.0) == "Low"
    assert classify_risk(0.30) == "Moderate"
    assert classify_risk(0.55) == "High"
    assert classify_risk(0.75) == "Severe"
