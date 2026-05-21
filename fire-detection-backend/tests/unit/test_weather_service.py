import math
from datetime import datetime, timedelta

import pandas as pd

from app.services.weather_service import weather_service


def test_weather_empty_dataframe_returns_full_fallback(monkeypatch):
    def fake_fetch(*args, **kwargs):
        return pd.DataFrame()

    monkeypatch.setattr(weather_service, "_fetch_hourly_weather", fake_fetch)

    result = weather_service.get_weather_features(
        latitude=38.4,
        longitude=27.1,
        acq_datetime=datetime(2025, 8, 1, 12, 30),
    )

    assert result["weather_fetch_ok"] == 0
    assert result["weather_missing_any"] == 1
    assert result["weather_hours_24h"] == 0
    assert result["weather_hours_3d"] == 0
    assert result["weather_hours_7d"] == 0

    assert result["temp_mean_24h"] == 20.0
    assert result["rh_mean_24h"] == 50.0
    assert result["wind_mean_24h"] == 0.0
    assert result["precip_sum_24h"] == 0.0
    assert result["fwi_proxy"] == 0.0


def test_weather_all_nan_dataframe_falls_back(monkeypatch):
    df = pd.DataFrame({
        "time": [
            "2025-08-01T10:00",
            "2025-08-01T11:00",
            "2025-08-01T12:00",
        ],
        "temperature_2m": [None, None, None],
        "relative_humidity_2m": [None, None, None],
        "wind_speed_10m": [None, None, None],
        "wind_gusts_10m": [None, None, None],
        "precipitation": [None, None, None],
    })

    def fake_fetch(*args, **kwargs):
        return df

    monkeypatch.setattr(weather_service, "_fetch_hourly_weather", fake_fetch)

    result = weather_service.get_weather_features(
        latitude=38.4,
        longitude=27.1,
        acq_datetime=datetime(2025, 8, 1, 12, 30),
    )

    assert result["weather_fetch_ok"] == 0
    assert result["weather_missing_any"] == 1
    assert result["temp_mean_24h"] == 20.0
    assert result["rh_mean_24h"] == 50.0
    assert result["fwi_proxy"] == 0.0


def test_weather_partial_nan_values_are_cleaned(monkeypatch):
    df = pd.DataFrame({
        "time": [
            "2025-08-01T09:00",
            "2025-08-01T10:00",
            "2025-08-01T11:00",
            "2025-08-01T12:00",
        ],
        "temperature_2m": [30.0, None, 32.0, 33.0],
        "relative_humidity_2m": [35.0, None, 40.0, 45.0],
        "wind_speed_10m": [10.0, None, 12.0, 14.0],
        "wind_gusts_10m": [20.0, None, 22.0, 24.0],
        "precipitation": [0.0, None, 0.0, 0.0],
    })

    def fake_fetch(*args, **kwargs):
        return df

    monkeypatch.setattr(weather_service, "_fetch_hourly_weather", fake_fetch)

    result = weather_service.get_weather_features(
        latitude=38.4,
        longitude=27.1,
        acq_datetime=datetime(2025, 8, 1, 12, 30),
    )

    assert result["weather_fetch_ok"] == 1

    for key, value in result.items():
        if isinstance(value, float):
            assert not math.isnan(value), f"{key} is NaN"


def test_successful_weather_generates_24h_3d_7d_features(monkeypatch):
    base_time = datetime(2025, 8, 1, 12, 0)

    times = []
    temps = []
    rhs = []
    winds = []
    gusts = []
    precips = []

    for i in range(168):
        t = base_time - timedelta(hours=i)
        times.append(t.isoformat())
        temps.append(30.0)
        rhs.append(35.0)
        winds.append(12.0)
        gusts.append(20.0)
        precips.append(0.0)

    df = pd.DataFrame({
        "time": times,
        "temperature_2m": temps,
        "relative_humidity_2m": rhs,
        "wind_speed_10m": winds,
        "wind_gusts_10m": gusts,
        "precipitation": precips,
    })

    def fake_fetch(*args, **kwargs):
        return df

    monkeypatch.setattr(weather_service, "_fetch_hourly_weather", fake_fetch)

    result = weather_service.get_weather_features(
        latitude=38.4,
        longitude=27.1,
        acq_datetime=datetime(2025, 8, 1, 12, 30),
    )

    assert result["weather_fetch_ok"] == 1

    assert "temp_mean_24h" in result
    assert "temp_mean_3d" in result
    assert "temp_mean_7d" in result

    assert "rh_mean_24h" in result
    assert "rh_mean_3d" in result
    assert "rh_mean_7d" in result

    assert "wind_mean_24h" in result
    assert "wind_mean_3d" in result
    assert "wind_mean_7d" in result

    assert "precip_sum_24h" in result
    assert "precip_sum_3d" in result
    assert "precip_sum_7d" in result

    assert result["weather_hours_24h"] > 0
    assert result["weather_hours_3d"] > 0
    assert result["weather_hours_7d"] > 0


def test_fwi_proxy_values_are_not_negative():
    features = {
        "temp_max_24h": 5.0,
        "temp_mean_3d": 5.0,
        "temp_mean_7d": 5.0,
        "rh_mean_24h": 95.0,
        "rh_mean_3d": 95.0,
        "rh_mean_7d": 95.0,
        "wind_mean_24h": 1.0,
        "wind_max_24h": 1.0,
        "precip_sum_24h": 100.0,
        "precip_sum_3d": 200.0,
        "precip_sum_7d": 300.0,
        "dryness_24h": 5.0,
        "dryness_3d": 5.0,
        "dryness_7d": 5.0,
    }

    result = weather_service._derive_fwi_proxy_features(features)

    assert result["ffmc_proxy"] >= 0.0
    assert result["dmc_proxy"] >= 0.0
    assert result["dc_proxy"] >= 0.0
    assert result["isi_proxy"] >= 0.0
    assert result["bui_proxy"] >= 0.0
    assert result["fwi_proxy"] >= 0.0


def test_vpd_calculation_returns_non_negative_value():
    value = weather_service._compute_vpd_kpa(
        temp_c=35.0,
        rh_percent=25.0,
    )

    assert value >= 0.0


def test_vpd_with_nan_returns_zero():
    value = weather_service._compute_vpd_kpa(
        temp_c=float("nan"),
        rh_percent=50.0,
    )

    assert value == 0.0
