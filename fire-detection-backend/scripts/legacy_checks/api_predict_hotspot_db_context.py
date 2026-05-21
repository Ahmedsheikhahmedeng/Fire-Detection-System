import json

import requests

API_URL = "http://127.0.0.1:8000/api/ml/predict-hotspot-db-context"

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
}

response = requests.post(API_URL, json=payload, timeout=90)

print("Status code:", response.status_code)

data = response.json()
print(json.dumps(data, indent=2, ensure_ascii=False))

assert response.status_code == 200
assert data["success"] is True
assert "probabilities" in data
assert "decision" in data
assert "context_status" in data
assert "created_alert_id" in data
assert "websocket_broadcast_queued" in data

print("\nAPI predict-hotspot-db-context test PASSED.")
