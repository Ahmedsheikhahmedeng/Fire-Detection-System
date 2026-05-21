from __future__ import annotations

import logging
from datetime import datetime, timedelta
from math import asin, cos, radians, sin, sqrt
from typing import Any, Dict, List

logger = logging.getLogger("fire_detection.spatial_context")


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    İki koordinat arasındaki mesafeyi km olarak hesaplar.
    """
    r = 6371.0

    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
    )

    c = 2 * asin(sqrt(a))
    return r * c


class SpatialContextService:
    """
    Current hotspot için geçmiş hotspot'lardan spatial context üretir.

    İlk versiyon:
    - history_hotspots listesi alır
    - DB bağımsız çalışır
    - Sonraki aşamada nasa_service / database ile bağlanır
    """

    def compute_nearby_context(
        self,
        current_hotspot: Dict[str, Any],
        history_hotspots: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, float]:
        if history_hotspots is None:
            history_hotspots = []

        if current_hotspot.get("latitude") is None or current_hotspot.get("longitude") is None:
            raise ValueError("latitude and longitude are required for spatial context.")

        current_lat = float(current_hotspot["latitude"])
        current_lon = float(current_hotspot["longitude"])
        current_time = self._parse_datetime(current_hotspot)
        current_hotspot_id = self._normalize_id(
            current_hotspot.get("hotspot_id") or current_hotspot.get("id")
        )

        context = {}

        windows = [
            (2, 24),
            (5, 48),
            (10, 72),
        ]

        for radius_km, window_hours in windows:
            matched_frps = []

            window_start = current_time - timedelta(hours=window_hours)

            for h in history_hotspots:
                try:
                    h_time = self._parse_datetime(h)
                    if not (window_start <= h_time <= current_time):
                        continue

                    history_hotspot_id = self._normalize_id(h.get("hotspot_id") or h.get("id"))
                    if current_hotspot_id is not None and history_hotspot_id == current_hotspot_id:
                        continue

                    h_lat = float(h["latitude"])
                    h_lon = float(h["longitude"])

                    distance = haversine_km(current_lat, current_lon, h_lat, h_lon)

                    if distance <= radius_km:
                        frp = float(h.get("frp") or 0.0)
                        matched_frps.append(frp)

                except Exception as e:
                    logger.debug("History hotspot skipped while computing spatial context: %s", e)
                    continue

            prefix = f"{radius_km}km_{window_hours}h"

            context[f"nearby_count_{prefix}"] = float(len(matched_frps))
            context[f"nearby_max_frp_{prefix}"] = float(max(matched_frps)) if matched_frps else 0.0
            context[f"nearby_mean_frp_{prefix}"] = (
                float(sum(matched_frps) / len(matched_frps)) if matched_frps else 0.0
            )

        return context

    def _parse_datetime(self, hotspot: Dict[str, Any]) -> datetime:
        if hotspot.get("hotspot_datetime"):
            value = hotspot["hotspot_datetime"]
            if isinstance(value, datetime):
                return value.replace(tzinfo=None)

            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)

        acq_date = hotspot.get("acq_date")
        acq_time = hotspot.get("acq_time")
        if acq_date is None or acq_time is None:
            raise ValueError("hotspot_datetime or acq_date/acq_time is required.")

        acq_time = str(acq_time).replace(".0", "").zfill(4)

        return datetime.strptime(f"{acq_date} {acq_time}", "%Y-%m-%d %H%M")

    def _normalize_id(self, value: Any) -> str | None:
        if value is None:
            return None
        return str(value)


spatial_context_service = SpatialContextService()
