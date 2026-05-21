import argparse
import re
from pathlib import Path

import pandas as pd

from app.services.temporal_features import (
    MODEL_FEATURE_COLUMNS,
    build_advanced_features,
    build_temporal_feature_history,
)

HIGH_CONFIDENCE_LABELS = {"h", "high"}
LOW_CONFIDENCE_LABELS = {"l", "low", "n", "nominal"}


def parse_args():
    parser = argparse.ArgumentParser(description="Temporal feature'lı eğitim dataseti üret.")
    parser.add_argument(
        "--output",
        default="dataset.csv",
        help="Üretilecek CSV yolu.",
    )
    parser.add_argument(
        "--label-threshold",
        type=float,
        default=80.0,
        help="Numerik confidence için pozitif sınıf eşiği.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Weather kayıtlarını stream ederken kullanılacak batch boyutu.",
    )
    parser.add_argument(
        "--label-mode",
        choices=["strict_high", "nominal_or_high"],
        default="strict_high",
        help="NASA confidence değerini binary label'a çevirme stratejisi.",
    )
    return parser.parse_args()


def confidence_to_label(confidence, threshold: float, label_mode: str):
    if confidence is None:
        return None

    text = str(confidence).strip().lower()
    if not text or text in {"none", "null", "nan"}:
        return None

    if label_mode == "nominal_or_high":
        if text in HIGH_CONFIDENCE_LABELS | {"n", "nominal"}:
            return 1
        if text in {"l", "low"}:
            return 0
    elif text in HIGH_CONFIDENCE_LABELS:
        return 1
    elif text in LOW_CONFIDENCE_LABELS:
        return 0

    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if match is None:
        return None

    return 1 if float(match.group()) >= threshold else 0


def main():
    args = parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    from app.core.database import SessionLocal
    from app.models.hotspot import Hotspot
    from app.models.weather import WeatherData

    db = SessionLocal()
    rows = []
    skipped_unlabeled = 0

    try:
        confidence_by_hotspot = {
            hotspot_id: confidence
            for hotspot_id, confidence in db.query(Hotspot.id, Hotspot.confidence).all()
        }

        weather_query = (
            db.query(WeatherData)
            .filter(WeatherData.hotspot_id.isnot(None), WeatherData.created_at.isnot(None))
            .order_by(WeatherData.hotspot_id.asc(), WeatherData.created_at.asc(), WeatherData.id.asc())
        )

        for weather, temporal in build_temporal_feature_history(
            weather_query.yield_per(args.batch_size)
        ):
            label = confidence_to_label(
                confidence_by_hotspot.get(weather.hotspot_id),
                threshold=args.label_threshold,
                label_mode=args.label_mode,
            )
            if label is None:
                skipped_unlabeled += 1
                continue

            advanced = build_advanced_features(
                temp=weather.temperature if weather.temperature is not None else 20.0,
                humidity=weather.humidity if weather.humidity is not None else 50.0,
                wind_speed=weather.wind_speed if weather.wind_speed is not None else 0.0,
                rain=weather.rain_1h if weather.rain_1h is not None else 0.0,
                temporal_features=temporal,
            )
            row = {
                "hotspot_id": weather.hotspot_id,
                "weather_id": weather.id,
                "observed_at": weather.created_at.isoformat() if weather.created_at else None,
                "confidence_raw": confidence_by_hotspot.get(weather.hotspot_id),
                "temperature": weather.temperature,
                "humidity": weather.humidity,
                "wind_speed": weather.wind_speed,
                "precipitation": weather.rain_1h,
                "temp_avg_24h": temporal["temp_avg_24h"],
                "rain_sum_3d": temporal["rain_sum_3d"],
                "humidity_trend": temporal["humidity_trend"],
                "heat_index": advanced["heat_index"],
                "drought_index": advanced["drought_index"],
                "wind_effect": advanced["wind_effect"],
                "fwi": advanced["fwi"],
                "fire": label,
            }

            rows.append(row)

        dataset = pd.DataFrame(rows)
        if dataset.empty:
            raise RuntimeError("Dataset boş üretildi. Hotspot/weather verisi veya label parse mantığı kontrol edilmeli.")

        missing_features = [column for column in MODEL_FEATURE_COLUMNS if column not in dataset.columns]
        if missing_features:
            raise RuntimeError(f"Eksik feature kolonları: {missing_features}")

        dataset.to_csv(output_path, index=False)

        label_counts = dataset["fire"].value_counts().to_dict()
        print(
            "✅ Dataset üretildi | "
            f"path={output_path} rows={len(dataset)} "
            f"positive={label_counts.get(1, 0)} negative={label_counts.get(0, 0)} "
            f"skipped_unlabeled={skipped_unlabeled} "
            f"label_mode={args.label_mode}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
