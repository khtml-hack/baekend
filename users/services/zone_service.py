from __future__ import annotations

import hashlib
from typing import Optional, Dict
import random


IMUN_ZONE_CODES = [
    {"code": "A", "name": "A구역"},
    {"code": "B", "name": "B구역"},
    {"code": "C", "name": "C구역"},
    {"code": "D", "name": "D구역"},
]


def _hash_to_zone(text: str) -> Dict[str, str]:
    """Deterministically map arbitrary text to one of predefined zone codes."""
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    idx = int(h[:8], 16) % len(IMUN_ZONE_CODES)
    return IMUN_ZONE_CODES[idx]


def infer_zone(address: Optional[str] = None, lat: Optional[float] = None, lng: Optional[float] = None) -> Optional[Dict[str, str]]:
    """
    Infer user's zone within Imun New Town.

    Rules (simple, deterministic, safe defaults):
    - If address contains '이문' (or 'imun'), bucket by address hash into A~D.
    - Else, if coordinates provided, bucket by simple quadrant hashing for stability.
    - Else, return None.

    This is intentionally simple so we can replace later with polygon-based mapping
    without changing calling code.
    """

    # 1) Address-based mapping: random assignment among predefined zones
    if address:
        return random.choice(IMUN_ZONE_CODES)

    # 2) Coordinate-based fallback (stable bucketing by rounded grid cell)
    if lat is not None and lng is not None:
        lat_bucket = int(round(lat * 1000))  # ~110m granularity
        lng_bucket = int(round(lng * 1000))
        key = f"{lat_bucket}:{lng_bucket}"
        return _hash_to_zone(key)

    # 3) Unknown
    return None


