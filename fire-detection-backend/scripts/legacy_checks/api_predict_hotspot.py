import json

import requests

API_URL = "http://127.0.0.1:8000/api/ml/predict-hotspot"

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

response = requests.post(API_URL, json=payload, timeout=60)

print("Status code:", response.status_code)

try:
    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))
except Exception:
    print(response.text)
    raise

assert response.status_code == 200
assert data["success"] is True
assert "probabilities" in data
assert "decision" in data
assert "feature_status" in data

print("\nAPI predict-hotspot test PASSED.")
