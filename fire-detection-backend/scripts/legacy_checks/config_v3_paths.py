from pathlib import Path
from app.core.config import settings

model_dir = Path(settings.V3_MODEL_DIR)

print("MODEL_PACKAGE_VERSION: v3")
print("ENABLE_ML_PREDICTION:", settings.ENABLE_ML_PREDICTION)
print("V3_MODEL_DIR:", model_dir.resolve())
print("Exists:", model_dir.exists())

required_files = [
    settings.V3_HGB_CORE_MODEL,
    settings.V3_XGBOOST_MODEL,
    settings.V3_LIGHTGBM_MODEL,
    settings.V3_CATBOOST_MODEL,
    settings.V3_RF_MODEL,
    settings.V3_EXTRATREES_MODEL,
    settings.V3_HGB_FEATURES,
    settings.V3_FULL_FEATURES,
    settings.V3_THRESHOLD_CONFIG,
    settings.V3_METADATA,
]

missing = []

for file_name in required_files:
    path = model_dir / file_name
    if path.exists():
        print("OK  -", path)
    else:
        print("MISS -", path)
        missing.append(str(path))

if missing:
    raise FileNotFoundError(missing)

print("\nV3 config path check PASSED.")
