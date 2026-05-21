from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict

import numpy as np
import pandas as pd
import requests
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.hotspot import Hotspot
from app.models.weather import WeatherData

logger = logging.getLogger("fire_detection.weather")


def _is_placeholder_openweather_key(value: str | None) -> bool:
    if not value:
        return True

    return value.strip().lower() in {
        "",
        "dev_key",
        "your_openweather_api_key",
        "your_openweather_api_key_here",
        "replace_with_openweather_api_key",
    }


def _fetch_current_weather_open_meteo(latitude: float, longitude: float) -> Dict[str, Any]:
    """Fetch current weather without an API key for local/demo enrichment."""
    response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": ",".join(
                [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "wind_speed_10m",
                    "wind_direction_10m",
                    "pressure_msl",
                    "precipitation",
                ]
            ),
            "timezone": "UTC",
        },
        timeout=30,
    )
    response.raise_for_status()
    current = response.json().get("current") or {}

    return {
        "temperature": current.get("temperature_2m"),
        "humidity": current.get("relative_humidity_2m"),
        "pressure": current.get("pressure_msl"),
        "wind_speed": current.get("wind_speed_10m"),
        "wind_deg": current.get("wind_direction_10m"),
        "rain_1h": current.get("precipitation", 0) or 0,
    }


def _fetch_current_weather_openweather(latitude: float, longitude: float) -> Dict[str, Any]:
    url = (
        "https://api.openweathermap.org/data/2.5/weather"
        f"?lat={latitude}"
        f"&lon={longitude}"
        f"&appid={settings.OPENWEATHER_API_KEY}"
        "&units=metric"
    )
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()

    return {
        "temperature": data["main"]["temp"],
        "humidity": data["main"]["humidity"],
        "pressure": data["main"]["pressure"],
        "wind_speed": data["wind"]["speed"],
        "wind_deg": data.get("wind", {}).get("deg"),
        "rain_1h": data.get("rain", {}).get("1h", 0),
    }


def enrich_weather_for_hotspot(hotspot_id: int, db: Session):
    """
    Legacy/current weather snapshot helper.

    V3 ML feature üretimi geçmiş saatlik Open-Meteo verisini kullanır;
    bu fonksiyon sadece yardımcı anlık weather kaydı için tutulur.
    """
    hotspot = db.query(Hotspot).filter(Hotspot.id == hotspot_id).first()

    if not hotspot:
        return None

    try:
        if _is_placeholder_openweather_key(settings.OPENWEATHER_API_KEY):
            data = _fetch_current_weather_open_meteo(hotspot.latitude, hotspot.longitude)
        else:
            try:
                data = _fetch_current_weather_openweather(hotspot.latitude, hotspot.longitude)
            except requests.HTTPError as exc:
                status_code = exc.response.status_code if exc.response is not None else None
                if status_code not in {401, 403}:
                    raise

                logger.warning(
                    "OpenWeather key rejected; falling back to Open-Meteo | hotspot_id=%s status=%s",
                    hotspot_id,
                    status_code,
                )
                data = _fetch_current_weather_open_meteo(hotspot.latitude, hotspot.longitude)
    except Exception:
        logger.exception("Current weather enrichment failed | hotspot_id=%s", hotspot_id)
        raise

    weather = WeatherData(
        hotspot_id=hotspot.id,
        temperature=data["temperature"],
        humidity=data["humidity"],
        pressure=data["pressure"],
        wind_speed=data["wind_speed"],
        wind_deg=data.get("wind_deg"),
        rain_1h=data["rain_1h"],
    )

    db.add(weather)
    db.commit()
    db.refresh(weather)

    return weather


class WeatherService:
    """
    Open-Meteo üzerinden hotspot zamanından önceki 7 günlük hourly weather alır.
    Sonra V3 modelin beklediği 24h / 3d / 7d aggregate feature'ları üretir.
    """

    ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

    HOURLY_VARS = [
        "temperature_2m",
        "relative_humidity_2m",
        "wind_speed_10m",
        "wind_gusts_10m",
        "precipitation",
    ]

    def get_weather_features(
        self,
        latitude: float,
        longitude: float,
        acq_datetime: datetime,
    ) -> Dict[str, Any]:
        start_date = (acq_datetime - timedelta(days=8)).date().isoformat()
        end_date = acq_datetime.date().isoformat()

        hourly_df = self._fetch_hourly_weather(
            latitude=latitude,
            longitude=longitude,
            start_date=start_date,
            end_date=end_date,
        )

        if hourly_df.empty:
            logger.warning(
                "Open-Meteo hourly data empty; fallback weather features used | lat=%s lon=%s date=%s",
                latitude,
                longitude,
                acq_datetime.isoformat(),
            )
            return self._fallback_weather_features()

        hourly_df["time"] = pd.to_datetime(hourly_df["time"], errors="coerce")
        hourly_df = hourly_df.dropna(subset=["time"]).copy()

        hourly_df = hourly_df[
            (hourly_df["time"] <= acq_datetime)
            & (hourly_df["time"] >= acq_datetime - timedelta(days=7))
        ].copy()

        if hourly_df.empty:
            logger.warning(
                "Open-Meteo hourly data outside target window; fallback weather features used | lat=%s lon=%s date=%s",
                latitude,
                longitude,
                acq_datetime.isoformat(),
            )
            return self._fallback_weather_features()

        features = {}
        features.update(self._aggregate_window(hourly_df, acq_datetime, hours=24, suffix="24h"))
        features.update(self._aggregate_window(hourly_df, acq_datetime, hours=72, suffix="3d"))
        features.update(self._aggregate_window(hourly_df, acq_datetime, hours=168, suffix="7d"))

        if not self._has_usable_weather_aggregates(features):
            logger.warning(
                "Open-Meteo hourly data has no usable numeric weather values; fallback weather features used | lat=%s lon=%s date=%s",
                latitude,
                longitude,
                acq_datetime.isoformat(),
            )
            return self._fallback_weather_features()

        features = self._clean_weather_features(features)
        cleaned_missing_any = int(features.pop("weather_missing_any", 0) or 0)
        cleaned_missing_count = int(features.pop("weather_missing_count", 0) or 0)

        features.update(self._derive_weather_features(features))
        features.update(self._derive_fwi_proxy_features(features))

        features["weather_fetch_ok"] = 1
        features["weather_missing_any"] = cleaned_missing_any
        features["weather_missing_count"] = cleaned_missing_count
        features["weather_hours_24h"] = int(features.get("_weather_hours_24h", 0))
        features["weather_hours_3d"] = int(features.get("_weather_hours_3d", 0))
        features["weather_hours_7d"] = int(features.get("_weather_hours_7d", 0))
        features["weather_hour_count_7d"] = int(features.get("_weather_hours_7d", 0))

        for key in list(features.keys()):
            if key.startswith("_"):
                features.pop(key, None)

        return self._clean_weather_features(features)

    def _fetch_hourly_weather(
        self,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": ",".join(self.HOURLY_VARS),
            "timezone": "UTC",
        }

        try:
            response = requests.get(self.ARCHIVE_URL, params=params, timeout=30)
            response.raise_for_status()
        except Exception:
            logger.exception(
                "Open-Meteo archive fetch failed | lat=%s lon=%s start=%s end=%s",
                latitude,
                longitude,
                start_date,
                end_date,
            )
            raise

        data = response.json()
        hourly = data.get("hourly", {})

        if not hourly or "time" not in hourly:
            logger.warning(
                "Open-Meteo response missing hourly/time | lat=%s lon=%s start=%s end=%s",
                latitude,
                longitude,
                start_date,
                end_date,
            )
            return pd.DataFrame()

        return pd.DataFrame(hourly)

    def _aggregate_window(
        self,
        hourly_df: pd.DataFrame,
        acq_datetime: datetime,
        hours: int,
        suffix: str,
    ) -> Dict[str, Any]:
        start_time = acq_datetime - timedelta(hours=hours)

        window = hourly_df[
            (hourly_df["time"] >= start_time)
            & (hourly_df["time"] <= acq_datetime)
        ].copy()

        out = {
            f"_weather_hours_{suffix}": len(window),
        }

        if window.empty:
            out.update({
                f"temp_mean_{suffix}": np.nan,
                f"temp_max_{suffix}": np.nan,
                f"temp_min_{suffix}": np.nan,
                f"humidity_mean_{suffix}": np.nan,
                f"rh_mean_{suffix}": np.nan,
                f"rh_min_{suffix}": np.nan,
                f"wind_mean_{suffix}": np.nan,
                f"wind_max_{suffix}": np.nan,
                f"gust_max_{suffix}": np.nan,
                f"precip_sum_{suffix}": np.nan,
            })
            return out

        temp = pd.to_numeric(window.get("temperature_2m"), errors="coerce")
        rh = pd.to_numeric(window.get("relative_humidity_2m"), errors="coerce")
        wind = pd.to_numeric(window.get("wind_speed_10m"), errors="coerce")
        gust = pd.to_numeric(window.get("wind_gusts_10m"), errors="coerce")
        precip = pd.to_numeric(window.get("precipitation"), errors="coerce")

        out.update({
            f"temp_mean_{suffix}": float(temp.mean()),
            f"temp_max_{suffix}": float(temp.max()),
            f"temp_min_{suffix}": float(temp.min()),
            f"humidity_mean_{suffix}": float(rh.mean()),
            f"rh_mean_{suffix}": float(rh.mean()),
            f"rh_min_{suffix}": float(rh.min()),
            f"wind_mean_{suffix}": float(wind.mean()),
            f"wind_max_{suffix}": float(wind.max()),
            f"gust_max_{suffix}": float(gust.max()) if gust.notna().any() else float(wind.max()),
            f"precip_sum_{suffix}": float(precip.sum(min_count=1)),
        })

        return out

    def _compute_vpd_kpa(self, temp_c: float, rh_percent: float) -> float:
        if pd.isna(temp_c) or pd.isna(rh_percent):
            return 0.0

        rh_percent = max(0.0, min(100.0, float(rh_percent)))
        temp_c = float(temp_c)

        es = 0.6108 * np.exp((17.27 * temp_c) / (temp_c + 237.3))
        ea = es * (rh_percent / 100.0)

        return float(max(es - ea, 0.0))

    def _derive_weather_features(self, features: Dict[str, Any]) -> Dict[str, Any]:
        out = {}

        for suffix in ["24h", "3d", "7d"]:
            temp_mean = self._safe_number(features.get(f"temp_mean_{suffix}"), 0.0)
            temp_max = self._safe_number(features.get(f"temp_max_{suffix}"), temp_mean)
            rh_mean = self._safe_number(
                features.get(f"rh_mean_{suffix}", features.get(f"humidity_mean_{suffix}", 50)),
                50.0,
            )
            rh_min = self._safe_number(features.get(f"rh_min_{suffix}"), rh_mean)

            out[f"vpd_mean_{suffix}"] = self._compute_vpd_kpa(temp_mean, rh_mean)
            out[f"vpd_max_{suffix}"] = self._compute_vpd_kpa(temp_max, rh_min)
            out[f"dryness_{suffix}"] = max(0.0, 100.0 - rh_mean)

        precip_24h = self._safe_number(features.get("precip_sum_24h"), 0.0)
        precip_3d = self._safe_number(features.get("precip_sum_3d"), 0.0)
        precip_7d = self._safe_number(features.get("precip_sum_7d"), 0.0)

        out["no_rain_24h"] = int(precip_24h <= 0.1)
        out["no_rain_3d"] = int(precip_3d <= 0.5)
        out["no_rain_7d"] = int(precip_7d <= 1.0)

        if precip_7d <= 1:
            dry_days = 7
        elif precip_7d <= 5:
            dry_days = 5
        elif precip_7d <= 15:
            dry_days = 3
        else:
            dry_days = 1

        out["dry_days_count_7d"] = dry_days
        out["rainy_days_count_7d"] = 7 - dry_days

        out["heat_dry_index_24h"] = (
            self._safe_number(features.get("temp_max_24h"), 0.0)
            * max(0.0, 100.0 - self._safe_number(features.get("rh_min_24h"), 50.0))
            / 100.0
        )

        out["wind_dryness_index_24h"] = (
            self._safe_number(features.get("wind_max_24h"), 0.0)
            * self._safe_number(out.get("dryness_24h"), 0.0)
            / 100.0
        )

        out["gust_dryness_index_24h"] = (
            self._safe_number(
                features.get("gust_max_24h", features.get("wind_max_24h", 0)),
                0.0,
            )
            * self._safe_number(out.get("dryness_24h"), 0.0)
            / 100.0
        )

        return out

    def _derive_fwi_proxy_features(self, features: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(features)
        merged.update(self._derive_weather_features(features))

        temp_max_24h = self._safe_number(merged.get("temp_max_24h"), 0.0)
        dryness_24h = self._safe_number(merged.get("dryness_24h"), 0.0)
        wind_mean_24h = self._safe_number(merged.get("wind_mean_24h"), 0.0)
        precip_24h = self._safe_number(merged.get("precip_sum_24h"), 0.0)

        temp_mean_3d = self._safe_number(merged.get("temp_mean_3d"), 0.0)
        dryness_3d = self._safe_number(merged.get("dryness_3d"), 0.0)
        precip_3d = self._safe_number(merged.get("precip_sum_3d"), 0.0)

        temp_mean_7d = self._safe_number(merged.get("temp_mean_7d"), 0.0)
        dryness_7d = self._safe_number(merged.get("dryness_7d"), 0.0)
        precip_7d = self._safe_number(merged.get("precip_sum_7d"), 0.0)
        dry_days_7d = self._safe_number(merged.get("dry_days_count_7d"), 0.0)

        wind_max_24h = self._safe_number(merged.get("wind_max_24h"), 0.0)
        vpd_max_24h = self._safe_number(merged.get("vpd_max_24h"), 0.0)

        ffmc_proxy = (
            0.35 * temp_max_24h
            + 0.35 * dryness_24h
            + 0.20 * wind_mean_24h
            - 0.40 * precip_24h
        )

        dmc_proxy = (
            0.40 * temp_mean_3d
            + 0.35 * dryness_3d
            + 0.25 * dry_days_7d
            - 0.30 * precip_3d
        )

        dc_proxy = (
            0.35 * temp_mean_7d
            + 0.35 * dryness_7d
            + 0.30 * dry_days_7d
            - 0.20 * precip_7d
        )

        ffmc_proxy = max(0.0, ffmc_proxy)
        dmc_proxy = max(0.0, dmc_proxy)
        dc_proxy = max(0.0, dc_proxy)
        isi_proxy = max(0.0, ffmc_proxy * (1 + wind_max_24h / 50))
        bui_proxy = max(0.0, (dmc_proxy + dc_proxy) / 2)

        fwi_proxy = max(0.0, (
            0.35 * ffmc_proxy
            + 0.25 * isi_proxy
            + 0.25 * bui_proxy
            + 0.15 * vpd_max_24h
        ))

        return {
            "ffmc_proxy": float(ffmc_proxy),
            "dmc_proxy": float(dmc_proxy),
            "dc_proxy": float(dc_proxy),
            "isi_proxy": float(isi_proxy),
            "bui_proxy": float(bui_proxy),
            "fwi_proxy": float(fwi_proxy),
            "ffmc": float(ffmc_proxy),
            "dmc": float(dmc_proxy),
            "dc": float(dc_proxy),
            "isi": float(isi_proxy),
            "bui": float(bui_proxy),
            "fwi": float(fwi_proxy),
        }

    def _fallback_weather_features(self) -> Dict[str, Any]:
        fallback = self._neutral_weather_fwi_defaults()
        fallback.update({
            "weather_fetch_ok": 0,
            "weather_missing_any": 1,
            "weather_missing_count": len(fallback),
            "weather_hours_24h": 0,
            "weather_hours_3d": 0,
            "weather_hours_7d": 0,
            "weather_hour_count_7d": 0,
        })
        return fallback

    def _neutral_weather_fwi_defaults(self) -> Dict[str, Any]:
        features: Dict[str, Any] = {}
        for suffix in ["24h", "3d", "7d"]:
            features[f"temp_mean_{suffix}"] = 20.0
            features[f"temp_max_{suffix}"] = 20.0
            features[f"temp_min_{suffix}"] = 20.0
            features[f"humidity_mean_{suffix}"] = 50.0
            features[f"rh_mean_{suffix}"] = 50.0
            features[f"rh_min_{suffix}"] = 50.0
            features[f"wind_mean_{suffix}"] = 0.0
            features[f"wind_max_{suffix}"] = 0.0
            features[f"gust_max_{suffix}"] = 0.0
            features[f"precip_sum_{suffix}"] = 0.0
            features[f"vpd_mean_{suffix}"] = 0.0
            features[f"vpd_max_{suffix}"] = 0.0
            features[f"dryness_{suffix}"] = 50.0

        features.update({
            "no_rain_24h": 1,
            "no_rain_3d": 1,
            "no_rain_7d": 1,
            "dry_days_count_7d": 0,
            "rainy_days_count_7d": 0,
            "heat_dry_index_24h": 0.0,
            "wind_dryness_index_24h": 0.0,
            "gust_dryness_index_24h": 0.0,
            "ffmc_proxy": 0.0,
            "dmc_proxy": 0.0,
            "dc_proxy": 0.0,
            "isi_proxy": 0.0,
            "bui_proxy": 0.0,
            "fwi_proxy": 0.0,
            "ffmc": 0.0,
            "dmc": 0.0,
            "dc": 0.0,
            "isi": 0.0,
            "bui": 0.0,
            "fwi": 0.0,
        })
        return features

    def _clean_weather_features(self, features: Dict[str, Any]) -> Dict[str, Any]:
        fallback = self._neutral_weather_fwi_defaults()
        cleaned = {}
        cleaned_count = 0

        for key, value in features.items():
            if self._is_missing_number(value):
                cleaned[key] = fallback.get(key, 0.0)
                cleaned_count += 1
            else:
                cleaned[key] = value

        if cleaned_count:
            cleaned["weather_missing_any"] = 1
            cleaned["weather_missing_count"] = int(cleaned.get("weather_missing_count", 0) or 0) + cleaned_count
            logger.warning("NaN weather feature values cleaned | count=%s", cleaned_count)

        return cleaned

    def _has_usable_weather_aggregates(self, features: Dict[str, Any]) -> bool:
        prefixes = (
            "temp_mean_",
            "temp_max_",
            "temp_min_",
            "rh_mean_",
            "rh_min_",
            "wind_mean_",
            "wind_max_",
            "gust_max_",
            "precip_sum_",
        )
        for key, value in features.items():
            if key.startswith(prefixes) and not self._is_missing_number(value):
                return True
        return False

    def _safe_number(self, value: Any, default: float = 0.0) -> float:
        if self._is_missing_number(value):
            return default
        try:
            return float(value)
        except Exception:
            return default

    def _is_missing_number(self, value: Any) -> bool:
        try:
            return bool(pd.isna(value))
        except Exception:
            return value is None


weather_service = WeatherService()
