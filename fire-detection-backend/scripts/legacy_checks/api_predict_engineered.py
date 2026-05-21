import json
from pathlib import Path

import requests

MODEL_DIR = Path("app/ml/final_models_v3")
EXAMPLE_INPUT = MODEL_DIR / "example_input_v3.json"

API_URL = "http://127.0.0.1:8000/api/ml/predict-engineered"

with open(EXAMPLE_INPUT, "r", encoding="utf-8") as f:
    payload = json.load(f)

if "features" in payload:
    features = payload["features"]
else:
    features = payload

request_body = {
    "features": features,
}

response = requests.post(API_URL, json=request_body, timeout=60)

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

print("\nAPI predict-engineered test PASSED.")
