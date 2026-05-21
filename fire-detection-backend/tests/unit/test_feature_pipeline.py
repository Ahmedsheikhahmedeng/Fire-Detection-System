import pytest

import app.services.feature_pipeline as feature_pipeline_module
from app.services.feature_pipeline import v3_feature_pipeline


def fake_success_weather_features(*args, **kwargs):
    """
    Gercek Open-Meteo cagrisi yapmadan basarili weather/FWI feature set doner.
    """
    return {
        "weather_fetch_ok": 1,
        "weather_missing_any": 0,
        "weather_missing_count": 0,

        "weather_hours_24h": 24,
        "weather_hours_3d": 72,
        "weather_hours_7d": 168,
        "weather_hour_count_7d": 168,

        "temp_mean_24h": 30.0,
        "temp_max_24h": 36.0,
        "temp_min_24h": 24.0,
        "humidity_mean_24h": 35.0,
        "rh_mean_24h": 35.0,
        "rh_min_24h": 20.0,
        "wind_mean_24h": 12.0,
        "wind_max_24h": 20.0,
        "gust_max_24h": 28.0,
        "precip_sum_24h": 0.0,

        "temp_mean_3d": 29.0,
        "temp_max_3d": 37.0,
        "temp_min_3d": 22.0,
        "humidity_mean_3d": 38.0,
        "rh_mean_3d": 38.0,
        "rh_min_3d": 22.0,
        "wind_mean_3d": 10.0,
        "wind_max_3d": 18.0,
        "gust_max_3d": 25.0,
        "precip_sum_3d": 0.0,

        "temp_mean_7d": 28.0,
        "temp_max_7d": 38.0,
        "temp_min_7d": 20.0,
        "humidity_mean_7d": 40.0,
        "rh_mean_7d": 40.0,
        "rh_min_7d": 25.0,
        "wind_mean_7d": 9.0,
        "wind_max_7d": 17.0,
        "gust_max_7d": 24.0,
        "precip_sum_7d": 0.0,

        "vpd_mean_24h": 2.0,
        "vpd_max_24h": 3.5,
        "dryness_24h": 65.0,
        "vpd_mean_3d": 1.8,
        "vpd_max_3d": 3.2,
        "dryness_3d": 62.0,
        "vpd_mean_7d": 1.6,
        "vpd_max_7d": 3.0,
        "dryness_7d": 60.0,

        "no_rain_24h": 1,
        "no_rain_3d": 1,
        "no_rain_7d": 1,
        "dry_days_count_7d": 7,
        "rainy_days_count_7d": 0,

        "heat_dry_index_24h": 28.0,
        "wind_dryness_index_24h": 7.8,
        "gust_dryness_index_24h": 18.2,

        "ffmc_proxy": 85.0,
        "dmc_proxy": 40.0,
        "dc_proxy": 120.0,
        "isi_proxy": 8.0,
        "bui_proxy": 60.0,
        "fwi_proxy": 15.0,
    }


def fake_failed_weather_features(*args, **kwargs):
    """
    Weather servisi basarisiz olmus gibi davranir.
    Pipeline'in kendi fallback guvenligi test edilir.
    """
    raise RuntimeError("fake weather service failure")


def test_feature_pipeline_builds_valid_required_features(monkeypatch, sample_raw_hotspot):
    monkeypatch.setattr(
        feature_pipeline_module.weather_service,
        "get_weather_features",
        fake_success_weather_features,
    )

    features = v3_feature_pipeline.build_features_from_raw_hotspot(sample_raw_hotspot)
    validation = v3_feature_pipeline.validate_output(features)

    assert validation["is_valid"] is True
    assert validation["required_feature_count"] == 101
    assert validation["received_feature_count"] >= 101
    assert len(validation["missing_features"]) == 0


def test_feature_pipeline_output_has_expected_core_fields(monkeypatch, sample_raw_hotspot):
    monkeypatch.setattr(
        feature_pipeline_module.weather_service,
        "get_weather_features",
        fake_success_weather_features,
    )

    features = v3_feature_pipeline.build_features_from_raw_hotspot(sample_raw_hotspot)

    expected_keys = [
        "latitude",
        "longitude",
        "frp",
        "brightness",
        "bright_ti4",
        "bright_ti5",
        "scan",
        "track",
        "month",
        "hour",
        "day_of_year",
        "is_fire_season",
        "is_peak_fire_season",
        "lat_grid",
        "lon_grid",
        "log_frp",
        "ti4_ti5_diff",
        "pixel_area_proxy",
        "frp_per_pixel_area",
        "weather_fetch_ok",
    ]

    for key in expected_keys:
        assert key in features


def test_feature_pipeline_bright_ti5_none_makes_diff_zero(monkeypatch, sample_raw_hotspot):
    monkeypatch.setattr(
        feature_pipeline_module.weather_service,
        "get_weather_features",
        fake_success_weather_features,
    )

    sample_raw_hotspot["bright_ti5"] = None
    sample_raw_hotspot["bright_ti4"] = 330
    sample_raw_hotspot["brightness"] = 330

    features = v3_feature_pipeline.build_features_from_raw_hotspot(sample_raw_hotspot)

    assert features["bright_ti5"] == 330
    assert features["ti4_ti5_diff"] == 0.0


def test_feature_pipeline_weather_success_features_are_used(monkeypatch, sample_raw_hotspot):
    monkeypatch.setattr(
        feature_pipeline_module.weather_service,
        "get_weather_features",
        fake_success_weather_features,
    )

    features = v3_feature_pipeline.build_features_from_raw_hotspot(sample_raw_hotspot)

    assert features["weather_fetch_ok"] == 1
    assert features["temp_mean_24h"] == 30.0
    assert features["rh_mean_24h"] == 35.0
    assert features["wind_mean_24h"] == 12.0
    assert features["precip_sum_24h"] == 0.0
    assert features["fwi_proxy"] == 15.0


def test_feature_pipeline_weather_failure_uses_neutral_fallback(monkeypatch, sample_raw_hotspot):
    monkeypatch.setattr(
        feature_pipeline_module.weather_service,
        "get_weather_features",
        fake_failed_weather_features,
    )

    features = v3_feature_pipeline.build_features_from_raw_hotspot(sample_raw_hotspot)
    validation = v3_feature_pipeline.validate_output(features)

    assert validation["is_valid"] is True

    assert features["weather_fetch_ok"] == 0
    assert features["weather_missing_any"] == 1

    assert features["temp_mean_24h"] == 20.0
    assert features["rh_mean_24h"] == 50.0
    assert features["wind_mean_24h"] == 0.0
    assert features["precip_sum_24h"] == 0.0
    assert features["fwi_proxy"] == 0.0


def test_feature_pipeline_spatial_context_features(monkeypatch, sample_raw_hotspot):
    monkeypatch.setattr(
        feature_pipeline_module.weather_service,
        "get_weather_features",
        fake_success_weather_features,
    )

    sample_raw_hotspot["history_hotspots"] = [
        {
            "hotspot_id": "999",
            "latitude": 38.401,
            "longitude": 27.101,
            "acq_date": "2025-08-01",
            "acq_time": "1200",
            "frp": 80,
        }
    ]

    features = v3_feature_pipeline.build_features_from_raw_hotspot(sample_raw_hotspot)

    assert "nearby_count_2km_24h" in features
    assert features["nearby_count_2km_24h"] == 1.0
    assert features["nearby_max_frp_2km_24h"] == 80.0


def test_feature_pipeline_validate_output_reports_defaulted_features(monkeypatch, sample_raw_hotspot):
    monkeypatch.setattr(
        feature_pipeline_module.weather_service,
        "get_weather_features",
        fake_success_weather_features,
    )

    features = v3_feature_pipeline.build_features_from_raw_hotspot(sample_raw_hotspot)
    validation = v3_feature_pipeline.validate_output(features)

    assert "defaulted_feature_count" in validation
    assert "defaulted_features" in validation
    assert isinstance(validation["defaulted_features"], list)
    assert validation["defaulted_feature_count"] >= 0


def test_feature_pipeline_invalid_missing_time_raises_error(monkeypatch, sample_raw_hotspot):
    monkeypatch.setattr(
        feature_pipeline_module.weather_service,
        "get_weather_features",
        fake_success_weather_features,
    )

    sample_raw_hotspot.pop("acq_date", None)
    sample_raw_hotspot.pop("acq_time", None)
    sample_raw_hotspot.pop("hotspot_datetime", None)

    with pytest.raises(Exception):
        v3_feature_pipeline.build_features_from_raw_hotspot(sample_raw_hotspot)


def test_feature_pipeline_invalid_missing_coordinates_still_validates_with_defaults(monkeypatch, sample_raw_hotspot):
    """
    Bu test pipeline'in eksik koordinatta nasil davrandigini kontrol eder.
    Eger production'da eksik koordinata hata verdirmek istiyorsan bu testi degistirebiliriz.
    """
    monkeypatch.setattr(
        feature_pipeline_module.weather_service,
        "get_weather_features",
        fake_success_weather_features,
    )

    sample_raw_hotspot["latitude"] = None
    sample_raw_hotspot["longitude"] = None

    with pytest.raises(Exception):
        v3_feature_pipeline.build_features_from_raw_hotspot(sample_raw_hotspot)
