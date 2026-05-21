from pathlib import Path
import json

MODEL_DIR = Path("app/ml/final_models_v3")

required_files = [
    "v3_hgb_core_model.joblib",
    "v3_xgboost_full_model.joblib",
    "v3_lightgbm_watch_model.joblib",
    "v3_catboost_watch_model.joblib",
    "v3_rf_balanced_verifier_model.joblib",
    "v3_extratrees_strict_verifier_model.joblib",
    "hgb_core_feature_columns.json",
    "full_feature_columns.json",
    "threshold_config_v3.json",
    "example_input_v3.json",
    "example_prediction_v3.json",
    "model_package_metadata_v3.json",
    "FINAL_PROJECT_REPORT_V3.md",
]

print("Checking V3 model package...")
print("Model dir:", MODEL_DIR.resolve())

missing = []

for file_name in required_files:
    path = MODEL_DIR / file_name
    if path.exists():
        print(f"OK  - {file_name}")
    else:
        print(f"MISS - {file_name}")
        missing.append(file_name)

if missing:
    raise FileNotFoundError(f"Missing files: {missing}")

with open(MODEL_DIR / "threshold_config_v3.json", "r", encoding="utf-8") as f:
    threshold_config = json.load(f)

with open(MODEL_DIR / "hgb_core_feature_columns.json", "r", encoding="utf-8") as f:
    hgb_features = json.load(f)

with open(MODEL_DIR / "full_feature_columns.json", "r", encoding="utf-8") as f:
    full_features = json.load(f)

print("\nThreshold config:")
print(json.dumps(threshold_config, indent=2, ensure_ascii=False))

print("\nFeature counts:")
print("HGB core features:", len(hgb_features))
print("Full features:", len(full_features))

assert len(hgb_features) > 0, "HGB feature list is empty"
assert len(full_features) > 0, "Full feature list is empty"

print("\nV3 model package check PASSED.")
