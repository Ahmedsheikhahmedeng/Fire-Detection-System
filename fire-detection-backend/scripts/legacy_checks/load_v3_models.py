from pathlib import Path
import joblib

MODEL_DIR = Path("app/ml/final_models_v3")

model_files = {
    "hgb_core": "v3_hgb_core_model.joblib",
    "xgboost": "v3_xgboost_full_model.joblib",
    "lightgbm": "v3_lightgbm_watch_model.joblib",
    "catboost": "v3_catboost_watch_model.joblib",
    "rf": "v3_rf_balanced_verifier_model.joblib",
    "extratrees": "v3_extratrees_strict_verifier_model.joblib",
}

loaded_models = {}

for name, file_name in model_files.items():
    path = MODEL_DIR / file_name
    print(f"Loading {name}: {path}")
    loaded_models[name] = joblib.load(path)
    print(f"Loaded {name}: {type(loaded_models[name])}")

print("\nAll V3 models loaded successfully.")
