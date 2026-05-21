from collections import deque
from datetime import datetime, timedelta
from typing import Iterable, Optional

import numpy as np
from sqlalchemy.orm import Session

from app.core.time_utils import utc_now_naive
from app.models.weather import WeatherData

TEMPORAL_FEATURE_NAMES = {"temp_avg_24h", "rain_sum_3d", "humidity_trend"}
ADVANCED_FEATURE_NAMES = {"heat_index", "drought_index", "wind_effect", "fwi"}
MODEL_FEATURE_COLUMNS = [
    "temperature",
    "humidity",
    "wind_speed",
    "precipitation",
    "temp_avg_24h",
    "rain_sum_3d",
    "humidity_trend",
    "heat_index",
    "drought_index",
    "wind_effect",
    "fwi",
]


def value_or_default(value: Optional[float], default: float) -> float:
    return default if value is None else float(value)


def recent_weather_history(
    hotspot_id: int,
    reference_time: datetime,
    db: Session,
    lookback_hours: int = 72,
) -> list[WeatherData]:
    cutoff = reference_time - timedelta(hours=lookback_hours)
    return (
        db.query(WeatherData)
        .filter(
            WeatherData.hotspot_id == hotspot_id,
            WeatherData.created_at >= cutoff,
            WeatherData.created_at <= reference_time,
        )
        .order_by(WeatherData.created_at.asc(), WeatherData.id.asc())
        .all()
    )


def calculate_humidity_trend(history_24h: Iterable[WeatherData]) -> float:
    humidity_points = [
        row
        for row in history_24h
        if row.created_at is not None and row.humidity is not None
    ]
    if len(humidity_points) < 2:
        return 0.0

    start_time = humidity_points[0].created_at
    hours = np.array(
        [
            (row.created_at - start_time).total_seconds() / 3600
            for row in humidity_points
        ],
        dtype=float,
    )
    humidity_values = np.array(
        [float(row.humidity) for row in humidity_points],
        dtype=float,
    )

    if np.allclose(hours, hours[0]):
        return 0.0

    return float(np.polyfit(hours, humidity_values, 1)[0])


def extract_temporal_features(
    weather: WeatherData,
    weather_history: list[WeatherData],
) -> dict:
    reference_time = weather.created_at or utc_now_naive()
    cutoff_24h = reference_time - timedelta(hours=24)

    history_24h = [
        row
        for row in weather_history
        if row.created_at is not None and row.created_at >= cutoff_24h
    ]

    current_temp = value_or_default(weather.temperature, 20.0)
    current_rain = value_or_default(weather.rain_1h, 0.0)

    temp_values_24h = [
        float(row.temperature)
        for row in history_24h
        if row.temperature is not None
    ]
    rain_values_72h = [
        float(row.rain_1h)
        for row in weather_history
        if row.rain_1h is not None
    ]

    coverage_24h = min(1.0, len(history_24h) / 24) if history_24h else 0.0
    coverage_72h = min(1.0, len(weather_history) / 72) if weather_history else 0.0

    temp_avg_24h = (
        sum(temp_values_24h) / len(temp_values_24h)
        if temp_values_24h
        else current_temp
    )
    rain_sum_3d = sum(rain_values_72h) if rain_values_72h else current_rain
    humidity_trend = calculate_humidity_trend(history_24h)

    return {
        "temp_avg_24h": round(float(temp_avg_24h), 4),
        "rain_sum_3d": round(float(rain_sum_3d), 4),
        "humidity_trend": round(float(humidity_trend), 4),
        "coverage_24h": round(float(coverage_24h), 4),
        "coverage_72h": round(float(coverage_72h), 4),
    }


def build_advanced_features(
    temp: float,
    humidity: float,
    wind_speed: float,
    rain: float,
    temporal_features: dict,
) -> dict:
    rain_sum = float(temporal_features["rain_sum_3d"])
    dryness = max(0.0, min(1.0, 1 - (humidity / 100)))

    heat_index = temp + 0.1 * humidity

    drought_index = dryness
    if rain_sum <= 0.01 and rain <= 0.01:
        drought_index += 0.5

    wind_effect = wind_speed * dryness

    fwi = (
        temp * 0.3
        + wind_speed * 0.3
        + dryness * 0.4
    )

    return {
        "heat_index": round(float(heat_index), 4),
        "drought_index": round(float(drought_index), 4),
        "wind_effect": round(float(wind_effect), 4),
        "fwi": round(float(fwi), 4),
    }


def get_temporal_features(
    hotspot_id: int,
    db: Session,
    weather: Optional[WeatherData] = None,
    reference_time: Optional[datetime] = None,
) -> Optional[dict]:
    target_weather = weather
    if target_weather is None:
        query = db.query(WeatherData).filter(WeatherData.hotspot_id == hotspot_id)
        if reference_time is not None:
            query = query.filter(WeatherData.created_at <= reference_time)
        target_weather = (
            query.order_by(WeatherData.created_at.desc(), WeatherData.id.desc()).first()
        )

    if target_weather is None:
        return None

    target_time = target_weather.created_at or reference_time or utc_now_naive()
    weather_history = recent_weather_history(hotspot_id, target_time, db)
    return extract_temporal_features(target_weather, weather_history)


def build_temporal_feature_history(
    weather_rows: Iterable[WeatherData],
) -> Iterable[tuple[WeatherData, dict]]:
    history = deque()
    current_hotspot_id = None

    for weather in weather_rows:
        if weather.hotspot_id != current_hotspot_id:
            history.clear()
            current_hotspot_id = weather.hotspot_id

        reference_time = weather.created_at or utc_now_naive()
        cutoff_72h = reference_time - timedelta(hours=72)
        history.append(weather)

        while history and history[0].created_at is not None and history[0].created_at < cutoff_72h:
            history.popleft()

        yield weather, extract_temporal_features(weather, list(history))
