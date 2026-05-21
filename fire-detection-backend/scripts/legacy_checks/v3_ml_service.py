import json
from pathlib import Path

from app.services.ml_service import v3_fire_model_service

MODEL_DIR = Path("app/ml/final_models_v3")
EXAMPLE_INPUT = MODEL_DIR / "example_input_v3.json"

with open(EXAMPLE_INPUT, "r", encoding="utf-8") as f:
    payload = json.load(f)

if "features" in payload:
    features = payload["features"]
else:
    features = payload

v3_fire_model_service.load()

validation = v3_fire_model_service.validate_engineered_features(features)

print("Validation:")
print(json.dumps(validation, indent=2, ensure_ascii=False))

if not validation["is_valid"]:
    raise ValueError("Example input is missing required features.")

prediction = v3_fire_model_service.predict_engineered(features)

print("\nPrediction:")
print(json.dumps(prediction, indent=2, ensure_ascii=False))

assert prediction["success"] is True
assert "probabilities" in prediction
assert "decision" in prediction

print("\nV3 ml_service test PASSED.")
