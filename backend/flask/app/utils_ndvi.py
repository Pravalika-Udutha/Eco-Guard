"""
Date validation and seasonal NDVI loss thresholds (Telangana forest monitoring).

Rules:
- Only period1_start / period1_end are user input; span may be at most MAX_PERIOD_DAYS (3) inclusive.
- Period 2 for NDVI comparison is derived automatically as the next contiguous window of the same length.
- Monsoon (June-September): loss threshold NDVI drop = -0.15 (relaxed).
- Other months: NDVI drop threshold = -0.25 (stricter).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from app.config import Config


def parse_iso_date(s: str) -> date:
    """Parse YYYY-MM-DD."""
    return datetime.strptime(s.strip()[:10], "%Y-%m-%d").date()


def period_length_days(start: date, end: date) -> int:
    """Inclusive span in days: same day => 1."""
    return (end - start).days + 1


def validate_period_one(
    p1_start: str,
    p1_end: str,
    max_days: int | None = None,
) -> tuple[date, date]:
    """
    Validate the user's single window (period 1). Raises ValueError on failure.
    Inclusive length must be <= max_days (default MAX_PERIOD_DAYS).
    """
    max_d = max_days if max_days is not None else Config.MAX_PERIOD_DAYS
    a1, b1 = parse_iso_date(p1_start), parse_iso_date(p1_end)
    if b1 < a1:
        raise ValueError("period1_end must be on or after period1_start")
    if period_length_days(a1, b1) > max_d:
        raise ValueError(
            f"Period 1 (start to end) must be at most {max_d} days inclusive"
        )
    return a1, b1


def derive_period2_following(p1_start: date, p1_end: date) -> tuple[date, date]:
    """
    Second comparison window: same inclusive length as period 1, starting the day after p1_end.
    Example: P1 = Jan 1-3 (3 days) -> P2 = Jan 4-6.
    """
    n = period_length_days(p1_start, p1_end)
    p2_start = p1_end + timedelta(days=1)
    p2_end = p2_start + timedelta(days=n - 1)
    return p2_start, p2_end


def is_monsoon_period(d1: date, d2: date, d3: date, d4: date) -> bool:
    """
    Use monsoon threshold if the mid-month of the comparison falls in Jun-Sep.
    We take the latest start date among the two windows as reference month.
    """
    ref = max(d1, d2)
    return ref.month in Config.MONSOON_MONTHS


def ndvi_drop_threshold_for_dates(d1: date, d2: date, d3: date, d4: date) -> float:
    """Negative float: e.g. -0.25 or -0.15."""
    if is_monsoon_period(d1, d2, d3, d4):
        return Config.NDVI_DROP_THRESHOLD_MONSOON
    return Config.NDVI_DROP_THRESHOLD_NORMAL


def classify_status(loss_pct: float) -> str:
    """Map forest loss % to Normal | Moderate Change | Critical Loss."""
    if loss_pct < Config.STATUS_MODERATE_MIN_PCT:
        return "Normal"
    if loss_pct < Config.STATUS_CRITICAL_MIN_PCT:
        return "Moderate Change"
    return "Critical Loss"


def geojson_empty_feature_collection() -> dict[str, Any]:
    return {"type": "FeatureCollection", "features": []}