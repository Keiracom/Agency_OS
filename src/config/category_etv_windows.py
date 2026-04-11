"""
Canonical ETV window configuration for all DataForSEO categories.

Generated from calibration run — Directive #328.1 (2026-04-12).
All discovery calls must use get_etv_window() rather than hardcoding
numeric defaults. See src/pipeline/discovery.py for usage pattern.

Measurement methodology:
  - 20 DFS Labs domain-metrics pages per category (100 domains/page)
  - Junk floor applied: offset_start = top-N blocked/parked domains
  - SMB band = p20 organic_count to p95 organic_count (keyword range)
  - ETV window = (p20_etv * 0.8, p95_etv * 5.5) — captures 80 % of SMBs
  - median_etv_per_keyword used for cross-category normalisation
"""

from typing import TypedDict


class ETVWindow(TypedDict):
    category_name: str
    etv_min: float
    etv_max: float
    keyword_count_min: int
    keyword_count_max: int
    offset_start: int
    offset_end: int
    median_etv_per_keyword: float
    sample_size: int
    measured_date: str
    measurement_directive: str
    junk_floor_offset: int


CATEGORY_ETV_WINDOWS: dict[int, ETVWindow] = {
    # ── Health ────────────────────────────────────────────────────────────────
    10514: {
        "category_name": "Dentists & Dental Services",
        "etv_min": 812.7,
        "etv_max": 39684.3,
        "keyword_count_min": 110,
        "keyword_count_max": 1275,
        "offset_start": 19,
        "offset_end": 1999,
        "median_etv_per_keyword": 6.21,
        "sample_size": 1449,
        "measured_date": "2026-04-12",
        "measurement_directive": "#328.1",
        "junk_floor_offset": 1999,
    },
    10520: {
        "category_name": "Hospitals & Health Clinics",
        "etv_min": 886.1,
        "etv_max": 72617.7,
        "keyword_count_min": 120,
        "keyword_count_max": 1820,
        "offset_start": 61,
        "offset_end": 1998,
        "median_etv_per_keyword": 8.46,
        "sample_size": 1323,
        "measured_date": "2026-04-12",
        "measurement_directive": "#328.1",
        "junk_floor_offset": 1999,
    },
    11979: {
        "category_name": "Veterinary",
        "etv_min": 379.1,
        "etv_max": 68771.5,
        "keyword_count_min": 93,
        "keyword_count_max": 1868,
        "offset_start": 15,
        "offset_end": 1999,
        "median_etv_per_keyword": 5.05,
        "sample_size": 1457,
        "measured_date": "2026-04-12",
        "measurement_directive": "#328.1",
        "junk_floor_offset": 1999,
    },
    # ── Legal & Finance ───────────────────────────────────────────────────────
    10163: {
        "category_name": "Legal",
        "etv_min": 1127.6,
        "etv_max": 153117.7,
        "keyword_count_min": 336,
        "keyword_count_max": 4588,
        "offset_start": 41,
        "offset_end": 1998,
        "median_etv_per_keyword": 3.25,
        "sample_size": 1208,
        "measured_date": "2026-04-12",
        "measurement_directive": "#328.1",
        "junk_floor_offset": 1999,
    },
    13686: {
        "category_name": "Attorneys & Law Firms",
        "etv_min": 425.6,
        "etv_max": 67159.0,
        "keyword_count_min": 174,
        "keyword_count_max": 2836,
        "offset_start": 26,
        "offset_end": 1698,
        "median_etv_per_keyword": 2.68,
        "sample_size": 1144,
        "measured_date": "2026-04-12",
        "measurement_directive": "#328.1",
        "junk_floor_offset": 1699,
    },
    11093: {
        "category_name": "Accounting & Auditing",
        "etv_min": 365.1,
        "etv_max": 176701.2,
        "keyword_count_min": 162,
        "keyword_count_max": 3854,
        "offset_start": 19,
        "offset_end": 1999,
        "median_etv_per_keyword": 2.35,
        "sample_size": 1425,
        "measured_date": "2026-04-12",
        "measurement_directive": "#328.1",
        "junk_floor_offset": 1999,
    },
    12391: {
        "category_name": "Bookkeeping",
        "etv_min": 964.2,
        "etv_max": 130487.3,
        "keyword_count_min": 328,
        "keyword_count_max": 5550,
        "offset_start": 3,
        "offset_end": 299,
        "median_etv_per_keyword": 2.75,
        "sample_size": 217,
        "measured_date": "2026-04-12",
        "measurement_directive": "#328.1",
        "junk_floor_offset": 299,
    },
    10531: {
        "category_name": "Real Estate Investments",
        "etv_min": 140.0,
        "etv_max": 13454.4,
        "keyword_count_min": 74,
        "keyword_count_max": 1767,
        "offset_start": 10,
        "offset_end": 499,
        "median_etv_per_keyword": 2.08,
        "sample_size": 372,
        "measured_date": "2026-04-12",
        "measurement_directive": "#328.1",
        "junk_floor_offset": 499,
    },
    # ── Construction & Trades ─────────────────────────────────────────────────
    10282: {
        "category_name": "Building Construction & Maintenance",
        "etv_min": 6578.1,
        "etv_max": 641325.5,
        "keyword_count_min": 1033,
        "keyword_count_max": 15048,
        "offset_start": 12,
        "offset_end": 1999,
        "median_etv_per_keyword": 6.83,
        "sample_size": 1478,
        "measured_date": "2026-04-12",
        "measurement_directive": "#328.1",
        "junk_floor_offset": 1999,
    },
    13462: {
        "category_name": "Plumbing",
        "etv_min": 825.8,
        "etv_max": 175250.5,
        "keyword_count_min": 217,
        "keyword_count_max": 3755,
        "offset_start": 13,
        "offset_end": 1998,
        "median_etv_per_keyword": 4.1,
        "sample_size": 1460,
        "measured_date": "2026-04-12",
        "measurement_directive": "#328.1",
        "junk_floor_offset": 1999,
    },
    11138: {
        "category_name": "Building Painting Services",
        "etv_min": 116.2,
        "etv_max": 26608.6,
        "keyword_count_min": 53,
        "keyword_count_max": 1524,
        "offset_start": 16,
        "offset_end": 1097,
        "median_etv_per_keyword": 2.23,
        "sample_size": 812,
        "measured_date": "2026-04-12",
        "measurement_directive": "#328.1",
        "junk_floor_offset": 1099,
    },
    11295: {
        "category_name": "Electrical Wiring",
        "etv_min": 157.8,
        "etv_max": 19777.1,
        "keyword_count_min": 53,
        "keyword_count_max": 1530,
        "offset_start": 25,
        "offset_end": 1098,
        "median_etv_per_keyword": 2.58,
        "sample_size": 808,
        "measured_date": "2026-04-12",
        "measurement_directive": "#328.1",
        "junk_floor_offset": 1099,
    },
    # ── HVAC ──────────────────────────────────────────────────────────────────
    10418: {
        "category_name": "Home Heating & Cooling",
        "etv_min": 32.1,
        "etv_max": 19483.6,
        "keyword_count_min": 36,
        "keyword_count_max": 1457,
        "offset_start": 19,
        "offset_end": 998,
        "median_etv_per_keyword": 1.42,
        "sample_size": 743,
        "measured_date": "2026-04-12",
        "measurement_directive": "#328.1",
        "junk_floor_offset": 999,
    },
    11147: {
        "category_name": "HVAC Service & Repair",
        "etv_min": 58.8,
        "etv_max": 25433.2,
        "keyword_count_min": 55,
        "keyword_count_max": 1386,
        "offset_start": 10,
        "offset_end": 1197,
        "median_etv_per_keyword": 2.79,
        "sample_size": 898,
        "measured_date": "2026-04-12",
        "measurement_directive": "#328.1",
        "junk_floor_offset": 1199,
    },
    11284: {
        "category_name": "HVAC & Climate Control",
        "etv_min": 304.7,
        "etv_max": 65746.5,
        "keyword_count_min": 120,
        "keyword_count_max": 2227,
        "offset_start": 23,
        "offset_end": 1999,
        "median_etv_per_keyword": 3.23,
        "sample_size": 1490,
        "measured_date": "2026-04-12",
        "measurement_directive": "#328.1",
        "junk_floor_offset": 1999,
    },
    # ── Automotive ────────────────────────────────────────────────────────────
    10193: {
        "category_name": "Vehicle Repair & Maintenance",
        "etv_min": 863.9,
        "etv_max": 102580.3,
        "keyword_count_min": 170,
        "keyword_count_max": 2643,
        "offset_start": 22,
        "offset_end": 1998,
        "median_etv_per_keyword": 4.64,
        "sample_size": 1493,
        "measured_date": "2026-04-12",
        "measurement_directive": "#328.1",
        "junk_floor_offset": 1999,
    },
    # ── Fitness & Beauty ──────────────────────────────────────────────────────
    10123: {
        "category_name": "Fitness",
        "etv_min": 1170.6,
        "etv_max": 262497.8,
        "keyword_count_min": 218,
        "keyword_count_max": 6237,
        "offset_start": 15,
        "offset_end": 1999,
        "median_etv_per_keyword": 5.5,
        "sample_size": 1434,
        "measured_date": "2026-04-12",
        "measurement_directive": "#328.1",
        "junk_floor_offset": 1999,
    },
    12049: {
        "category_name": "Fitness Instruction Training",
        "etv_min": 3.5,
        "etv_max": 10638.3,
        "keyword_count_min": 8,
        "keyword_count_max": 373,
        "offset_start": 6,
        "offset_end": 397,
        "median_etv_per_keyword": 0.88,
        "sample_size": 263,
        "measured_date": "2026-04-12",
        "measurement_directive": "#328.1",
        "junk_floor_offset": 399,
    },
    10333: {
        "category_name": "Hair Salons & Styling Services",
        "etv_min": 1644.6,
        "etv_max": 187962.5,
        "keyword_count_min": 171,
        "keyword_count_max": 4454,
        "offset_start": 18,
        "offset_end": 1399,
        "median_etv_per_keyword": 7.83,
        "sample_size": 1043,
        "measured_date": "2026-04-12",
        "measurement_directive": "#328.1",
        "junk_floor_offset": 1399,
    },
    # ── Food & Hospitality ────────────────────────────────────────────────────
    10020: {
        "category_name": "Dining & Nightlife",
        "etv_min": 7604.7,
        "etv_max": 1503903.5,
        "keyword_count_min": 320,
        "keyword_count_max": 18810,
        "offset_start": 14,
        "offset_end": 1199,
        "median_etv_per_keyword": 21.58,
        "sample_size": 897,
        "measured_date": "2026-04-12",
        "measurement_directive": "#328.1",
        "junk_floor_offset": 1199,
    },
    12975: {
        "category_name": "Restaurant Reviews, Guides & Listings",
        "etv_min": 764.7,
        "etv_max": 144862.7,
        "keyword_count_min": 96,
        "keyword_count_max": 2145,
        "offset_start": 20,
        "offset_end": 1297,
        "median_etv_per_keyword": 17.36,
        "sample_size": 973,
        "measured_date": "2026-04-12",
        "measurement_directive": "#328.1",
        "junk_floor_offset": 1299,
    },
}


def get_etv_window(category_code: int) -> tuple[float, float]:
    """Return (etv_min, etv_max) for a category. Raises KeyError if not calibrated."""
    if category_code not in CATEGORY_ETV_WINDOWS:
        raise KeyError(
            f"Category {category_code} not in calibrated ETV windows. "
            f"Run #328.1 calibration or add manually. "
            f"Available: {sorted(CATEGORY_ETV_WINDOWS.keys())}"
        )
    w = CATEGORY_ETV_WINDOWS[category_code]
    return (w["etv_min"], w["etv_max"])
