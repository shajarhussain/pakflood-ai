"""
Seed script — Pakistan districts table.

Usage (from backend/ directory):
    python scripts/seed_districts.py

Requires SUPABASE_URL and SUPABASE_KEY in backend/.env (same as the app).
Safe to run multiple times — uses upsert on district_id.
geom_json is left NULL; boundaries can be added later from a GeoJSON source.
"""

import sys
from pathlib import Path

# Allow imports from backend/app/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.supabase import get_supabase  # noqa: E402

# ── District data ─────────────────────────────────────────────────────────────
# (district_id, name, province, center_lat, center_lng)

DISTRICTS: list[tuple[str, str, str, float, float]] = [
    # ── Punjab (36 districts) ─────────────────────────────────────────────────
    ("PK-PB-AT", "Attock",           "Punjab", 33.77, 72.36),
    ("PK-PB-BN", "Bahawalnagar",     "Punjab", 29.99, 73.25),
    ("PK-PB-BW", "Bahawalpur",       "Punjab", 29.40, 71.68),
    ("PK-PB-CK", "Chakwal",          "Punjab", 32.93, 72.86),
    ("PK-PB-CH", "Chiniot",          "Punjab", 31.72, 72.98),
    ("PK-PB-DG", "Dera Ghazi Khan",  "Punjab", 30.05, 70.64),
    ("PK-PB-FS", "Faisalabad",       "Punjab", 31.42, 73.08),
    ("PK-PB-GW", "Gujranwala",       "Punjab", 32.16, 74.19),
    ("PK-PB-GT", "Gujrat",           "Punjab", 32.57, 74.08),
    ("PK-PB-HF", "Hafizabad",        "Punjab", 32.07, 73.69),
    ("PK-PB-JG", "Jhang",            "Punjab", 31.27, 72.32),
    ("PK-PB-JH", "Jhelum",           "Punjab", 32.94, 73.73),
    ("PK-PB-KS", "Kasur",            "Punjab", 31.12, 74.45),
    ("PK-PB-KW", "Khanewal",         "Punjab", 30.30, 71.93),
    ("PK-PB-KB", "Khushab",          "Punjab", 32.29, 72.35),
    ("PK-PB-LH", "Lahore",           "Punjab", 31.55, 74.34),
    ("PK-PB-LY", "Layyah",           "Punjab", 30.96, 70.94),
    ("PK-PB-LD", "Lodhran",          "Punjab", 29.53, 71.63),
    ("PK-PB-MB", "Mandi Bahauddin",  "Punjab", 32.58, 73.49),
    ("PK-PB-MW", "Mianwali",         "Punjab", 32.58, 71.54),
    ("PK-PB-MT", "Multan",           "Punjab", 30.20, 71.43),
    ("PK-PB-MZ", "Muzaffargarh",     "Punjab", 30.07, 71.19),
    ("PK-PB-NK", "Nankana Sahib",    "Punjab", 31.45, 73.71),
    ("PK-PB-NR", "Narowal",          "Punjab", 32.10, 74.87),
    ("PK-PB-OK", "Okara",            "Punjab", 30.81, 73.46),
    ("PK-PB-PP", "Pakpattan",        "Punjab", 30.34, 73.39),
    ("PK-PB-RY", "Rahim Yar Khan",   "Punjab", 28.42, 70.30),
    ("PK-PB-RJ", "Rajanpur",         "Punjab", 29.10, 70.33),
    ("PK-PB-RW", "Rawalpindi",       "Punjab", 33.60, 73.04),
    ("PK-PB-SW", "Sahiwal",          "Punjab", 30.67, 73.11),
    ("PK-PB-SG", "Sargodha",         "Punjab", 32.08, 72.67),
    ("PK-PB-SK", "Sheikhupura",      "Punjab", 31.71, 74.00),
    ("PK-PB-SI", "Sialkot",          "Punjab", 32.49, 74.53),
    ("PK-PB-TT", "Toba Tek Singh",   "Punjab", 30.97, 72.48),
    ("PK-PB-VH", "Vehari",           "Punjab", 30.04, 72.35),

    # ── Sindh (29 districts) ──────────────────────────────────────────────────
    ("PK-SD-BD", "Badin",                 "Sindh", 24.65, 68.84),
    ("PK-SD-DD", "Dadu",                  "Sindh", 26.73, 67.78),
    ("PK-SD-GK", "Ghotki",               "Sindh", 28.00, 69.32),
    ("PK-SD-HY", "Hyderabad",            "Sindh", 25.40, 68.37),
    ("PK-SD-JC", "Jacobabad",            "Sindh", 28.28, 68.45),
    ("PK-SD-JM", "Jamshoro",             "Sindh", 25.43, 68.28),
    ("PK-SD-KS", "Kambar Shahdadkot",    "Sindh", 27.59, 68.00),
    ("PK-SD-KC", "Karachi",              "Sindh", 24.86, 67.01),
    ("PK-SD-KM", "Kashmore",             "Sindh", 28.45, 69.57),
    ("PK-SD-KP", "Khairpur",             "Sindh", 27.53, 68.76),
    ("PK-SD-LK", "Larkana",              "Sindh", 27.56, 68.21),
    ("PK-SD-MT", "Matiari",              "Sindh", 25.60, 68.45),
    ("PK-SD-MK", "Mirpur Khas",          "Sindh", 25.53, 69.00),
    ("PK-SD-NF", "Naushahro Feroze",     "Sindh", 26.84, 68.12),
    ("PK-SD-SG", "Sanghar",              "Sindh", 26.04, 68.95),
    ("PK-SD-NB", "Shaheed Benazirabad",  "Sindh", 26.24, 68.41),
    ("PK-SD-SP", "Shikarpur",            "Sindh", 27.96, 68.64),
    ("PK-SD-SJ", "Sujawal",              "Sindh", 24.46, 68.09),
    ("PK-SD-SK", "Sukkur",               "Sindh", 27.70, 68.86),
    ("PK-SD-TA", "Tando Allahyar",       "Sindh", 25.47, 68.72),
    ("PK-SD-TM", "Tando Muhammad Khan",  "Sindh", 25.12, 68.54),
    ("PK-SD-TP", "Tharparkar",           "Sindh", 24.75, 69.74),
    ("PK-SD-TH", "Thatta",               "Sindh", 24.75, 67.92),
    ("PK-SD-UK", "Umerkot",              "Sindh", 25.36, 69.74),

    # ── Khyber Pakhtunkhwa (35 districts) ────────────────────────────────────
    ("PK-KP-AB", "Abbottabad",       "Khyber Pakhtunkhwa", 34.15, 73.21),
    ("PK-KP-BJ", "Bajaur",          "Khyber Pakhtunkhwa", 34.83, 71.51),
    ("PK-KP-BN", "Bannu",           "Khyber Pakhtunkhwa", 32.99, 70.60),
    ("PK-KP-BT", "Battagram",       "Khyber Pakhtunkhwa", 34.68, 73.02),
    ("PK-KP-BR", "Buner",           "Khyber Pakhtunkhwa", 34.51, 72.50),
    ("PK-KP-CS", "Charsadda",       "Khyber Pakhtunkhwa", 34.15, 71.74),
    ("PK-KP-CT", "Chitral",         "Khyber Pakhtunkhwa", 35.85, 71.79),
    ("PK-KP-DI", "Dera Ismail Khan","Khyber Pakhtunkhwa", 31.83, 70.91),
    ("PK-KP-HG", "Hangu",           "Khyber Pakhtunkhwa", 33.53, 71.06),
    ("PK-KP-HP", "Haripur",         "Khyber Pakhtunkhwa", 33.99, 72.94),
    ("PK-KP-KR", "Karak",           "Khyber Pakhtunkhwa", 33.12, 71.10),
    ("PK-KP-KH", "Kohat",           "Khyber Pakhtunkhwa", 33.59, 71.44),
    ("PK-KP-KN", "Kohistan",        "Khyber Pakhtunkhwa", 35.08, 73.48),
    ("PK-KP-KU", "Kurram",          "Khyber Pakhtunkhwa", 33.90, 70.00),
    ("PK-KP-LM", "Lakki Marwat",    "Khyber Pakhtunkhwa", 32.61, 70.91),
    ("PK-KP-LD", "Lower Dir",       "Khyber Pakhtunkhwa", 34.72, 71.88),
    ("PK-KP-ML", "Malakand",        "Khyber Pakhtunkhwa", 34.56, 71.93),
    ("PK-KP-MS", "Mansehra",        "Khyber Pakhtunkhwa", 34.33, 73.20),
    ("PK-KP-MD", "Mardan",          "Khyber Pakhtunkhwa", 34.20, 72.04),
    ("PK-KP-MH", "Mohmand",         "Khyber Pakhtunkhwa", 34.49, 71.27),
    ("PK-KP-NW", "North Waziristan","Khyber Pakhtunkhwa", 33.00, 70.06),
    ("PK-KP-NS", "Nowshera",        "Khyber Pakhtunkhwa", 34.01, 71.97),
    ("PK-KP-OR", "Orakzai",         "Khyber Pakhtunkhwa", 33.63, 70.95),
    ("PK-KP-PW", "Peshawar",        "Khyber Pakhtunkhwa", 34.01, 71.55),
    ("PK-KP-SH", "Shangla",         "Khyber Pakhtunkhwa", 34.78, 72.81),
    ("PK-KP-SW", "South Waziristan","Khyber Pakhtunkhwa", 32.38, 69.85),
    ("PK-KP-SB", "Swabi",           "Khyber Pakhtunkhwa", 34.12, 72.47),
    ("PK-KP-ST", "Swat",            "Khyber Pakhtunkhwa", 35.22, 72.43),
    ("PK-KP-TK", "Tank",            "Khyber Pakhtunkhwa", 32.22, 70.38),
    ("PK-KP-UD", "Upper Dir",       "Khyber Pakhtunkhwa", 35.21, 71.91),

    # ── Balochistan (33 districts) ────────────────────────────────────────────
    ("PK-BL-AW", "Awaran",          "Balochistan", 26.36, 65.24),
    ("PK-BL-BK", "Barkhan",         "Balochistan", 29.90, 69.53),
    ("PK-BL-CG", "Chagai",          "Balochistan", 28.98, 64.48),
    ("PK-BL-DB", "Dera Bugti",      "Balochistan", 28.90, 69.16),
    ("PK-BL-GW", "Gwadar",          "Balochistan", 25.12, 62.33),
    ("PK-BL-HN", "Harnai",          "Balochistan", 30.10, 67.93),
    ("PK-BL-JF", "Jaffarabad",      "Balochistan", 28.28, 68.15),
    ("PK-BL-JM", "Jhal Magsi",      "Balochistan", 28.28, 67.73),
    ("PK-BL-KC", "Kachhi",          "Balochistan", 29.50, 67.60),
    ("PK-BL-KL", "Kalat",           "Balochistan", 29.02, 66.59),
    ("PK-BL-KE", "Kech",            "Balochistan", 26.00, 63.05),
    ("PK-BL-KR", "Kharan",          "Balochistan", 28.58, 65.42),
    ("PK-BL-KZ", "Khuzdar",         "Balochistan", 27.81, 66.61),
    ("PK-BL-KA", "Killa Abdullah",  "Balochistan", 30.68, 66.59),
    ("PK-BL-KF", "Killa Saifullah", "Balochistan", 30.70, 68.44),
    ("PK-BL-KO", "Kohlu",           "Balochistan", 29.90, 69.25),
    ("PK-BL-LS", "Lasbela",         "Balochistan", 26.22, 66.70),
    ("PK-BL-LH", "Lehri",           "Balochistan", 29.50, 68.12),
    ("PK-BL-LR", "Loralai",         "Balochistan", 30.37, 68.60),
    ("PK-BL-MG", "Mastung",         "Balochistan", 29.80, 66.84),
    ("PK-BL-MK", "Musakhel",        "Balochistan", 30.58, 69.74),
    ("PK-BL-NR", "Nasirabad",       "Balochistan", 28.42, 68.37),
    ("PK-BL-NK", "Nushki",          "Balochistan", 29.55, 66.02),
    ("PK-BL-PJ", "Panjgur",         "Balochistan", 26.97, 64.10),
    ("PK-BL-PS", "Pishin",          "Balochistan", 30.58, 66.99),
    ("PK-BL-QT", "Quetta",          "Balochistan", 30.18, 67.00),
    ("PK-BL-SR", "Sherani",         "Balochistan", 30.96, 69.86),
    ("PK-BL-SB", "Sibi",            "Balochistan", 29.54, 67.88),
    ("PK-BL-SH", "Sohbatpur",       "Balochistan", 28.35, 68.07),
    ("PK-BL-WS", "Washuk",          "Balochistan", 27.20, 65.00),
    ("PK-BL-ZB", "Zhob",            "Balochistan", 31.34, 69.45),
    ("PK-BL-ZR", "Ziarat",          "Balochistan", 30.38, 67.73),

    # ── Gilgit-Baltistan (10 districts) ──────────────────────────────────────
    ("PK-GB-AS", "Astore",   "Gilgit-Baltistan", 35.37, 74.91),
    ("PK-GB-DM", "Diamer",   "Gilgit-Baltistan", 35.51, 74.17),
    ("PK-GB-GC", "Ghanche",  "Gilgit-Baltistan", 35.49, 76.72),
    ("PK-GB-GZ", "Ghizer",   "Gilgit-Baltistan", 36.27, 73.75),
    ("PK-GB-GL", "Gilgit",   "Gilgit-Baltistan", 35.92, 74.31),
    ("PK-GB-HN", "Hunza",    "Gilgit-Baltistan", 36.32, 74.65),
    ("PK-GB-HM", "Kharmang", "Gilgit-Baltistan", 35.24, 75.92),
    ("PK-GB-NG", "Nagar",    "Gilgit-Baltistan", 36.15, 74.49),
    ("PK-GB-SG", "Shigar",   "Gilgit-Baltistan", 35.50, 75.73),
    ("PK-GB-SK", "Skardu",   "Gilgit-Baltistan", 35.30, 75.63),

    # ── Azad Jammu & Kashmir (10 districts) ──────────────────────────────────
    ("PK-AK-BG", "Bagh",          "Azad Kashmir", 33.98, 73.78),
    ("PK-AK-BM", "Bhimber",       "Azad Kashmir", 32.97, 74.07),
    ("PK-AK-HV", "Haveli",        "Azad Kashmir", 33.63, 73.70),
    ("PK-AK-HT", "Hattian Bala",  "Azad Kashmir", 34.32, 73.84),
    ("PK-AK-KT", "Kotli",         "Azad Kashmir", 33.52, 73.90),
    ("PK-AK-MP", "Mirpur",        "Azad Kashmir", 33.14, 73.75),
    ("PK-AK-MZ", "Muzaffarabad",  "Azad Kashmir", 34.37, 73.47),
    ("PK-AK-NL", "Neelum",        "Azad Kashmir", 34.69, 74.02),
    ("PK-AK-PN", "Poonch",        "Azad Kashmir", 33.77, 74.09),
    ("PK-AK-SD", "Sudhnati",      "Azad Kashmir", 33.74, 73.71),

    # ── Islamabad Capital Territory ───────────────────────────────────────────
    ("PK-IS-IS", "Islamabad", "Islamabad Capital Territory", 33.72, 73.04),
]


def main() -> None:
    db = get_supabase()

    rows = [
        {
            "district_id": d[0],
            "name":        d[1],
            "province":    d[2],
            "center_lat":  d[3],
            "center_lng":  d[4],
            "geom_json":   None,
        }
        for d in DISTRICTS
    ]

    print(f"Seeding {len(rows)} districts...")

    # Upsert in chunks of 50 (safe for Supabase)
    chunk_size = 50
    inserted   = 0
    for start in range(0, len(rows), chunk_size):
        chunk = rows[start: start + chunk_size]
        db.table("districts").upsert(chunk, on_conflict="district_id").execute()
        inserted += len(chunk)
        print(f"  {inserted}/{len(rows)} done")

    print(f"Done — {len(rows)} districts upserted.")


if __name__ == "__main__":
    main()
