RISK_THRESHOLDS = {
    "Low": (0.0, 0.30),
    "Moderate": (0.30, 0.55),
    "High": (0.55, 0.75),
    "Severe": (0.75, 1.01),
}

DISCLAIMER = (
    "PakFlood AI is an educational decision-support prototype. "
    "Always consult official PMD, FFD, NDMA, and PDMA sources for real emergency decisions."
)


def classify_risk(score: float) -> str:
    for level, (low, high) in RISK_THRESHOLDS.items():
        if low <= score < high:
            return level
    return "Unknown"
