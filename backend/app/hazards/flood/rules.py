DISCLAIMER = (
    "PakFlood AI is an educational decision-support prototype. "
    "Always consult official PMD, FFD, NDMA, and PDMA sources for real emergency decisions."
)

RISK_THRESHOLDS = {
    "Low":      (0.00, 0.30),
    "Moderate": (0.30, 0.55),
    "High":     (0.55, 0.75),
    "Severe":   (0.75, 1.01),
}


def classify_risk(probability: float) -> str:
    for level, (lo, hi) in RISK_THRESHOLDS.items():
        if lo <= probability < hi:
            return level
    return "Unknown"
