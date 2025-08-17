"""
TMAP Traffic Integration
"""
import requests
from typing import Dict, Any, List
from django.conf import settings


def get_traffic_info(center_lat: float, center_lon: float, zoom_level: int = 15) -> Dict[str, Any]:
    """
    Fetch traffic information around a coordinate from TMAP Open API.
    Returns raw JSON or empty dict on failure.
    """
    if not getattr(settings, "TMAP_APP_KEY", None):
        # Gracefully return empty data if key not configured
        return {}

    url = "https://apis.openapi.sk.com/tmap/traffic"
    headers = {
        "Accept": "application/json",
        "appKey": settings.TMAP_APP_KEY,
    }
    params = {
        "version": 1,
        "centerLat": center_lat,
        "centerLon": center_lon,
        "reqCoordType": "WGS84GEO",
        "resCoordType": "WGS84GEO",
        "trafficType": "AUTO",
        "zoomLevel": zoom_level,
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=8)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {}


def summarize_traffic(traffic_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a compact summary from TMAP traffic response suitable for LLM prompts and UI.
    """
    if not traffic_data:
        return {
            "total_roads": 0,
            "counts": {"0": 0, "1": 0, "2": 0, "3": 0, "4": 0},
            "critical_roads": [],
        }

    counts = {"0": 0, "1": 0, "2": 0, "3": 0, "4": 0}
    critical: List[str] = []
    total = 0

    for feature in traffic_data.get("features", []):
        if feature.get("geometry", {}).get("type") != "LineString":
            continue
        props = feature.get("properties", {})
        road_name = props.get("name") or "알 수 없음"
        congestion = str(props.get("congestion", "0"))
        description = props.get("description") or ""
        total += 1
        if congestion in counts:
            counts[congestion] += 1
        # 3: 정체, 4: 매우정체 기준으로 주요 혼잡로 수집
        try:
            if int(congestion) >= 3 and description:
                critical.append(f"{road_name}: {description}")
        except Exception:
            pass

    return {
        "total_roads": total,
        "counts": counts,
        "critical_roads": critical[:10],
    }


