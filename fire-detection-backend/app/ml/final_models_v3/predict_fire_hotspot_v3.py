#!/usr/bin/env python3
import argparse
import warnings
from pathlib import Path

import joblib
import pandas as pd

from app.core.json_loader import load_json_file

warnings.filterwarnings("ignore", message="X does not have valid feature names")

MODEL_DIR = Path(__file__).resolve().parent

MODEL_FILES = {
    "hgb_core": "v3_hgb_core_model.joblib",
    "xgboost": "v3_xgboost_full_model.joblib",
    "lightgbm": "v3_lightgbm_watch_model.joblib",
    "catboost": "v3_catboost_watch_model.joblib",
    "rf": "v3_rf_balanced_verifier_model.joblib",
    "extratrees": "v3_extratrees_strict_verifier_model.joblib",
}


def load_json(path):
    return load_json_file(path)


def load_package():
    models = {name: joblib.load(MODEL_DIR / filename) for name, filename in MODEL_FILES.items()}
    hgb_features = load_json(MODEL_DIR / "hgb_core_feature_columns.json")
    full_features = load_json(MODEL_DIR / "full_feature_columns.json")
    thresholds = load_json(MODEL_DIR / "threshold_config_v3.json")
    return models, hgb_features, full_features, thresholds


def read_input(path):
    path = Path(path)
    if path.suffix.lower() == ".json":
        data = load_json(path)
        if isinstance(data, list):
            return pd.DataFrame(data)
        return pd.DataFrame([data])
    return pd.read_csv(path, low_memory=False)


def check_features(df, features, name):
    missing = [c for c in features if c not in df.columns]
    if missing:
        raise ValueError(f"{name} missing required features: {missing}")
    if df[features].isna().any().any():
        bad = df[features].columns[df[features].isna().any()].tolist()
        raise ValueError(f"{name} has missing values in features: {bad}")


def assign_level(row, t):
    if row["lightgbm_probability"] < t["lightgbm_watch_threshold"]:
        return 0
    if row["extratrees_probability"] >= t["extratrees_strict_threshold"] and row["rf_probability"] >= t["rf_balanced_threshold"]:
        return 4
    if row["extratrees_probability"] >= t["extratrees_strict_threshold"]:
        return 3
    if row["rf_probability"] >= t["rf_balanced_threshold"]:
        return 2
    return 1


def level_name(level):
    return {
        0: "low_risk_no_fire",
        1: "watch_early_warning",
        2: "high_confidence_balanced_fire",
        3: "strict_fire_alert",
        4: "very_strict_fire_alert",
    }[int(level)]


def predict(df):
    models, hgb_features, full_features, thresholds = load_package()
    df = df.copy()
    check_features(df, hgb_features, "hgb_core")
    check_features(df, full_features, "full_models")

    out = df.copy()
    out["hgb_core_probability"] = models["hgb_core"].predict_proba(out[hgb_features])[:, 1]
    out["xgboost_probability"] = models["xgboost"].predict_proba(out[full_features])[:, 1]
    out["lightgbm_probability"] = models["lightgbm"].predict_proba(out[full_features])[:, 1]
    out["catboost_probability"] = models["catboost"].predict_proba(out[full_features])[:, 1]
    out["ensemble_probability"] = out[[
        "hgb_core_probability", "xgboost_probability", "lightgbm_probability", "catboost_probability"
    ]].mean(axis=1)
    out["rf_probability"] = models["rf"].predict_proba(out[full_features])[:, 1]
    out["extratrees_probability"] = models["extratrees"].predict_proba(out[full_features])[:, 1]

    out["watch_lightgbm"] = out["lightgbm_probability"] >= thresholds["lightgbm_watch_threshold"]
    out["watch_catboost"] = out["catboost_probability"] >= thresholds["catboost_watch_threshold"]
    out["watch_ensemble"] = out["ensemble_probability"] >= thresholds["ensemble_watch_threshold"]
    out["rf_balanced_gate"] = out["rf_probability"] >= thresholds["rf_balanced_threshold"]
    out["extratrees_strict_gate"] = out["extratrees_probability"] >= thresholds["extratrees_strict_threshold"]
    out["decision_level"] = out.apply(assign_level, axis=1, t=thresholds)
    out["decision_name"] = out["decision_level"].apply(level_name)
    return out


def main():
    parser = argparse.ArgumentParser(description="Predict V3 fire hotspot decision levels.")
    parser.add_argument("input", help="Input JSON or CSV with completed V3 features")
    parser.add_argument("--output", "-o", help="Output JSON or CSV path", default=None)
    args = parser.parse_args()

    df = read_input(args.input)
    pred = predict(df)

    preferred = [
        "hotspot_id", "decision_level", "decision_name", "lightgbm_probability",
        "ensemble_probability", "catboost_probability", "rf_probability", "extratrees_probability",
        "watch_lightgbm", "watch_catboost", "watch_ensemble", "rf_balanced_gate", "extratrees_strict_gate",
    ]
    cols = [c for c in preferred if c in pred.columns] + [c for c in pred.columns if c not in preferred]
    pred = pred[cols]

    if args.output:
        out_path = Path(args.output)
        if out_path.suffix.lower() == ".json":
            out_path.write_text(pred.to_json(orient="records", indent=2, force_ascii=False), encoding="utf-8")
        else:
            pred.to_csv(out_path, index=False)
    else:
        print(pred.to_json(orient="records", indent=2, force_ascii=False))


if __name__ == "__main__":
    main()
