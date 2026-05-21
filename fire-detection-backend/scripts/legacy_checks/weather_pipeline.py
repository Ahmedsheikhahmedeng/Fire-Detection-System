import json

from app.services.feature_pipeline import v3_feature_pipeline

payload = {
    "latitude": 38.12,
    "longitude": 23.45,
    "acq_date": "2025-07-20",
    "acq_time": "1235",
    "frp": 18.2,
    "brightness": 330.5,
    "bright_ti4": 335.1,
    "bright_ti5": 298.4,
    "scan": 0.41,
    "track": 0.39,
    "confidence": "nominal",
    "daynight": "D",
    "satellite": "N",
    "instrument": "VIIRS",
    "history_hotspots": [
        {
            "hotspot_id": "hist_001",
            "latitude": 38.121,
            "longitude": 23.451,
            "acq_date": "2025-07-20",
            "acq_time": "1135",
            "frp": 22.0,
        }
    ],
}

features = v3_feature_pipeline.build_features_from_raw_hotspot(payload)

keys = [
    "weather_fetch_ok",
    "weather_missing_any",
    "weather_hours_24h",
    "weather_hours_3d",
    "weather_hours_7d",
    "temp_mean_24h",
    "temp_max_24h",
    "humidity_mean_24h",
    "rh_mean_24h",
    "rh_min_24h",
    "wind_mean_24h",
    "wind_max_24h",
    "gust_max_24h",
    "precip_sum_24h",
    "vpd_mean_24h",
    "vpd_max_24h",
    "dryness_24h",
    "ffmc_proxy",
    "dmc_proxy",
    "dc_proxy",
    "isi_proxy",
    "bui_proxy",
    "fwi_proxy",
    "fwi",
]

result = {k: features.get(k) for k in keys if k in features}

print(json.dumps(result, indent=2, ensure_ascii=False))

assert features.get("weather_fetch_ok") == 1
assert features.get("weather_hours_24h", 0) > 0
assert features.get("weather_hours_7d", 0) > 0
assert "fwi_proxy" in features

print("\nWeather pipeline test PASSED.")
