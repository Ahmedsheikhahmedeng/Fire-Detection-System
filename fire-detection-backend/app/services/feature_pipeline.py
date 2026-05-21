from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import json
import logging
import math
from threading import Lock

import pandas as pd

from app.core.config import settings
from app.core.json_loader import load_json_file
from app.services.spatial_context_service import spatial_context_service
from app.services.weather_service import weather_service

logger = logging.getLogger("fire_detection.features")


class V3FeaturePipeline:
    """
    Raw FIRMS hotspot -> V3 model engineered feature dictionary.

    Builds FIRMS, temporal, location, spatial context, weather aggregate,
    and FWI proxy features from raw NASA hotspot input.
    """

    def __init__(self) -> None:
        self.model_dir = Path(settings.V3_MODEL_DIR)
        self.hgb_features: List[str] = []
        self.full_features: List[str] = []
        self.required_features: List[str] = []
        self.default_features: Dict[str, Any] = {}
        self.is_loaded = False
        self._load_lock = Lock()
        self._metadata_lock = Lock()
        self._defaulted_features_by_output: Dict[int, List[str]] = {}

    def load(self) -> None:
        if self.is_loaded:
            return

        with self._load_lock:
            if self.is_loaded:
                return

            self.hgb_features = self._load_json(settings.V3_HGB_FEATURES)
            self.full_features = self._load_json(settings.V3_FULL_FEATURES)
            self.required_features = sorted(set(self.hgb_features + self.full_features))

            example_path = self.model_dir / "example_input_v3.json"
            if not example_path.exists():
                raise FileNotFoundError(f"example_input_v3.json not found: {example_path}")

            with open(example_path, "r", encoding="utf-8") as f:
                example_payload = json.load(f)

            if "features" in example_payload:
                self.default_features = example_payload["features"]
            else:
                self.default_features = example_payload

            self.is_loaded = True

            logger.info(
                "V3 feature pipeline loaded | required features: %s",
                len(self.required_features),
            )

    def _load_json(self, file_name: str) -> Any:
        path = self.model_dir / file_name

        if not path.exists():
            raise FileNotFoundError(f"Feature file not found: {path}")

        return load_json_file(path)

    def build_features_from_raw_hotspot(self, hotspot: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_loaded:
            self.load()

        features: Dict[str, Any] = {}

        acq_datetime = self._parse_datetime(
            acq_date=hotspot.get("acq_date"),
            acq_time=hotspot.get("acq_time"),
            hotspot_datetime=hotspot.get("hotspot_datetime"),
        )

        self._add_raw_firms_features(features, hotspot)
        self._add_temporal_features(features, acq_datetime)
        self._add_location_features(features, hotspot)
        self._add_firms_derived_features(features)
        history_hotspots = hotspot.get("history_hotspots", [])
        self._add_spatial_context_features(features, hotspot, history_hotspots)
        self._add_weather_fwi_features(features, hotspot, acq_datetime)
        defaulted_features = self._finalize_required_features(features)
        self._remember_defaulted_features(features, defaulted_features)

        return features

    def _parse_datetime(
        self,
        acq_date: Any = None,
        acq_time: Any = None,
        hotspot_datetime: Any = None,
    ) -> datetime:
        if hotspot_datetime:
            dt = pd.to_datetime(hotspot_datetime, errors="coerce")
            if pd.isna(dt):
                raise ValueError(f"Invalid hotspot_datetime: {hotspot_datetime}")
            return dt.to_pydatetime().replace(tzinfo=None)

        if acq_date is None or acq_time is None:
            raise ValueError("Either hotspot_datetime or acq_date + acq_time is required.")

        acq_time_str = str(acq_time).replace(".0", "").zfill(4)

        dt = pd.to_datetime(
            f"{acq_date} {acq_time_str}",
            format="%Y-%m-%d %H%M",
            errors="coerce",
        )

        if pd.isna(dt):
            raise ValueError(f"Invalid acq_date/acq_time: {acq_date} {acq_time}")

        return dt.to_pydatetime().replace(tzinfo=None)

    def _to_float(self, value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    def _add_raw_firms_features(self, features: Dict[str, Any], hotspot: Dict[str, Any]) -> None:
        brightness = hotspot.get("brightness")
        bright_ti4 = hotspot.get("bright_ti4")
        if bright_ti4 is None:
            bright_ti4 = brightness

        if brightness is None:
            brightness = bright_ti4

        bright_ti5 = hotspot.get("bright_ti5")
        if bright_ti5 is None:
            bright_ti5 = bright_ti4

        raw_map = {
            "latitude": hotspot.get("latitude"),
            "longitude": hotspot.get("longitude"),
            "frp": hotspot.get("frp", 0.0),
            "brightness": brightness,
            "bright_ti4": bright_ti4,
            "bright_ti5": bright_ti5,
            "scan": hotspot.get("scan", 1.0),
            "track": hotspot.get("track", 1.0),
            "confidence": hotspot.get("confidence"),
            "daynight": hotspot.get("daynight"),
            "satellite": hotspot.get("satellite"),
            "instrument": hotspot.get("instrument", "VIIRS"),
            "firms_source": hotspot.get("firms_source", "VIIRS_SNPP_NRT"),
            "type": hotspot.get("type", 0),
            "version": hotspot.get("version", 2),
        }

        for key, value in raw_map.items():
            if key in self.required_features:
                features[key] = value

        # Keep normalized core FIRMS values visible for validation/tests even when a
        # model feature list does not require every raw source field.
        features.setdefault("brightness", brightness)

        for key in ["confidence", "daynight", "satellite", "instrument", "firms_source"]:
            if key in features and features[key] is None:
                features[key] = "unknown"

    def _add_temporal_features(self, features: Dict[str, Any], dt: datetime) -> None:
        month = dt.month
        hour = dt.hour
        weekday = dt.weekday()
        day_of_year = dt.timetuple().tm_yday

        temporal_values = {
            "year": dt.year,
            "month": month,
            "day": dt.day,
            "day_of_year": day_of_year,
            "hour": hour,
            "weekday": weekday,
            "is_weekend": int(weekday in [5, 6]),
            "is_fire_season": int(month in [6, 7, 8, 9, 10]),
            "is_peak_fire_season": int(month in [7, 8, 9]),
            "month_sin": math.sin(2 * math.pi * month / 12),
            "month_cos": math.cos(2 * math.pi * month / 12),
            "hour_sin": math.sin(2 * math.pi * hour / 24),
            "hour_cos": math.cos(2 * math.pi * hour / 24),
            "season": self._season_from_month(month),
            "is_day": int(6 <= hour <= 18),
        }

        for key, value in temporal_values.items():
            if key in self.required_features:
                features[key] = value

    def _season_from_month(self, month: int) -> str:
        if month in [12, 1, 2]:
            return "winter"
        if month in [3, 4, 5]:
            return "spring"
        if month in [6, 7, 8]:
            return "summer"
        return "autumn"

    def _add_location_features(self, features: Dict[str, Any], hotspot: Dict[str, Any]) -> None:
        lat = self._to_float(hotspot.get("latitude"))
        lon = self._to_float(hotspot.get("longitude"))

        location_values = {
            "latitude": lat,
            "longitude": lon,
            "lat_grid": round(lat, 1),
            "lon_grid": round(lon, 1),
            "inside_greece_polygon": hotspot.get("inside_greece_polygon", 0),
        }

        for key, value in location_values.items():
            if key in self.required_features:
                features[key] = value

    def _add_firms_derived_features(self, features: Dict[str, Any]) -> None:
        frp = self._to_float(features.get("frp"))
        brightness = self._to_float(features.get("brightness"))
        bright_ti4 = self._to_float(features.get("bright_ti4"))
        bright_ti5 = self._to_float(features.get("bright_ti5"))
        scan = self._to_float(features.get("scan"), default=1.0)
        track = self._to_float(features.get("track"), default=1.0)

        pixel_area_proxy = scan * track if scan and track else 0.0

        derived = {
            "log_frp": math.log1p(max(frp, 0.0)),
            "brightness_diff_ti4": brightness - bright_ti4,
            "ti4_ti5_diff": bright_ti4 - bright_ti5,
            "pixel_area_proxy": pixel_area_proxy,
            "frp_per_pixel_area": frp / pixel_area_proxy if pixel_area_proxy else 0.0,
        }

        confidence = features.get("confidence")
        if confidence is not None:
            derived["confidence_clean"] = str(confidence).strip().lower()

        for key, value in derived.items():
            if key in self.required_features:
                features[key] = value

    def _add_spatial_context_features(
        self,
        features: Dict[str, Any],
        hotspot: Dict[str, Any],
        history_hotspots: List[Dict[str, Any]] | None = None,
    ) -> None:
        """
        Geçmiş hotspot listesinden nearby context feature'ları üretir.
        Eğer history_hotspots boşsa değerler 0 kalır.
        """
        context = spatial_context_service.compute_nearby_context(
            current_hotspot=hotspot,
            history_hotspots=history_hotspots or [],
        )

        for key, value in context.items():
            if key in self.required_features:
                features[key] = value

    def _add_weather_fwi_features(
        self,
        features: Dict[str, Any],
        hotspot: Dict[str, Any],
        acq_datetime: datetime,
    ) -> None:
        """
        Open-Meteo weather service ile gerçek weather/FWI proxy feature üretir.
        API başarısız olursa fallback değerler kullanılır.
        """
        lat = self._to_float(hotspot.get("latitude"))
        lon = self._to_float(hotspot.get("longitude"))

        try:
            weather_features = weather_service.get_weather_features(
                latitude=lat,
                longitude=lon,
                acq_datetime=acq_datetime,
            )
            source = "open_meteo_weather_service"
        except Exception as e:
            logger.warning("Weather fetch failed; neutral fallback will be used: %s", e)
            weather_features = {}
            source = "weather_fallback"

        for key, value in weather_features.items():
            if key in self.required_features:
                features[key] = value

        if "weather_feature_source" in self.required_features:
            features["weather_feature_source"] = source

        if not weather_features:
            self._add_weather_fwi_fallback_flags(features)

    def _add_weather_fwi_fallback_flags(self, features: Dict[str, Any]) -> None:
        fallback_values = self._neutral_weather_fwi_defaults()

        fallback_values.update({
            "weather_fetch_ok": 0,
            "weather_missing_any": 1,
            "weather_missing_count": len(self._weather_fwi_feature_names()),
            "weather_hour_count_7d": 0,
            "weather_hours_24h": 0,
            "weather_hours_3d": 0,
            "weather_hours_7d": 0,
        })

        for key, value in fallback_values.items():
            if key in self.required_features:
                features[key] = value

        nearby_features = [
            "nearby_count_2km_24h",
            "nearby_max_frp_2km_24h",
            "nearby_mean_frp_2km_24h",
            "nearby_count_5km_48h",
            "nearby_max_frp_5km_48h",
            "nearby_mean_frp_5km_48h",
            "nearby_count_10km_72h",
            "nearby_max_frp_10km_72h",
            "nearby_mean_frp_10km_72h",
        ]

        for key in nearby_features:
            if key in self.required_features and key not in features:
                features[key] = 0

    def _weather_fwi_feature_names(self) -> List[str]:
        tokens = (
            "temp_",
            "rh_",
            "wind_",
            "gust_",
            "precip_",
            "rain",
            "dry",
            "fwi",
            "ffmc",
            "dmc",
            "dc_",
            "isi",
            "bui",
            "weather_",
        )
        return [
            key
            for key in self.required_features
            if any(token in key.lower() for token in tokens)
        ]

    def _neutral_weather_fwi_defaults(self) -> Dict[str, Any]:
        values = {}
        for key in self._weather_fwi_feature_names():
            name = key.lower()

            if name.startswith("temp_"):
                values[key] = 20.0
            elif name.startswith("rh_"):
                values[key] = 50.0
            elif name.startswith("no_rain_"):
                values[key] = 1
            else:
                values[key] = 0

        return values

    def _finalize_required_features(self, features: Dict[str, Any]) -> List[str]:
        defaulted_features = []
        for key in self.required_features:
            if key not in features:
                features[key] = self.default_features.get(key, 0)
                defaulted_features.append(key)
                continue

            if features[key] is None:
                features[key] = self.default_features.get(key, 0)
                defaulted_features.append(key)

        return defaulted_features

    def _remember_defaulted_features(
        self,
        features: Dict[str, Any],
        defaulted_features: List[str],
    ) -> None:
        with self._metadata_lock:
            self._defaulted_features_by_output[id(features)] = list(defaulted_features)

            # Keep this tiny cache bounded; build/validate are normally called back-to-back.
            if len(self._defaulted_features_by_output) > 256:
                for key in list(self._defaulted_features_by_output.keys())[:128]:
                    self._defaulted_features_by_output.pop(key, None)

    def validate_output(self, features: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_loaded:
            self.load()

        missing = [c for c in self.required_features if c not in features]
        with self._metadata_lock:
            defaulted_features = self._defaulted_features_by_output.get(id(features), [])

        return {
            "required_feature_count": len(self.required_features),
            "output_feature_count": len(features),
            "received_feature_count": len(features),
            "missing_features": missing,
            "defaulted_feature_count": len(defaulted_features),
            "defaulted_features": defaulted_features[:50],
            "is_valid": len(missing) == 0,
        }


v3_feature_pipeline = V3FeaturePipeline()
