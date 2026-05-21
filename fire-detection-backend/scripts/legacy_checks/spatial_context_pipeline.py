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
        },
        {
            "hotspot_id": "hist_002",
            "latitude": 38.13,
            "longitude": 23.46,
            "acq_date": "2025-07-20",
            "acq_time": "1035",
            "frp": 15.0,
        },
        {
            "hotspot_id": "hist_003",
            "latitude": 38.20,
            "longitude": 23.55,
            "acq_date": "2025-07-19",
            "acq_time": "1235",
            "frp": 8.0,
        },
    ],
}

features = v3_feature_pipeline.build_features_from_raw_hotspot(payload)

nearby_keys = [
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

result = {k: features.get(k) for k in nearby_keys}

print(json.dumps(result, indent=2, ensure_ascii=False))

assert features["nearby_count_2km_24h"] >= 1
assert features["nearby_count_5km_48h"] >= 1
assert features["nearby_count_10km_72h"] >= 1

print("\nSpatial context pipeline test PASSED.")
