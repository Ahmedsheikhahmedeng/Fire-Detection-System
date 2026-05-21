import argparse
import json
import sys
from pathlib import Path

import joblib
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.services.explainability_service import (
    compute_global_feature_importance,
    compute_local_explanation,
    compute_shap_explanation,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Eğitilmiş modeli SHAP ile açıkla.")
    parser.add_argument(
        "--model",
        default="app/ml/fire_model.joblib",
        help="Model artefakt yolu.",
    )
    parser.add_argument(
        "--dataset",
        default="dataset.csv",
        help="Açıklama için kullanılacak dataset.",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/explainability",
        help="Rapor ve görsellerin kaydedileceği klasör.",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=200,
        help="Global SHAP hesabında kullanılacak maksimum örnek sayısı.",
    )
    parser.add_argument(
        "--row-index",
        type=int,
        default=0,
        help="Yerel explanation üretilecek satır indeksi.",
    )
    return parser.parse_args()


def save_summary_plots(explanation, transformed_frame: pd.DataFrame, output_dir: Path):
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import shap
    except ImportError:
        print("⚠️ matplotlib veya shap plotting bağımlılığı bulunamadı, görsel üretilmedi.")
        return

    bar_path = output_dir / "shap_summary_bar.png"
    beeswarm_path = output_dir / "shap_summary_beeswarm.png"

    plt.figure()
    shap.summary_plot(
        explanation.values,
        transformed_frame,
        plot_type="bar",
        show=False,
    )
    plt.tight_layout()
    plt.savefig(bar_path, dpi=160, bbox_inches="tight")
    plt.close()

    plt.figure()
    shap.summary_plot(
        explanation.values,
        transformed_frame,
        show=False,
    )
    plt.tight_layout()
    plt.savefig(beeswarm_path, dpi=160, bbox_inches="tight")
    plt.close()


def main():
    args = parse_args()
    model_path = Path(args.model)
    dataset_path = Path(args.dataset)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    model_bundle = joblib.load(model_path)
    pipeline = model_bundle["model"]
    feature_columns = model_bundle["feature_columns"]

    df = pd.read_csv(dataset_path)
    X = df[feature_columns]

    sample_size = min(args.sample_size, len(X))
    sample = X.iloc[:sample_size].copy()
    explanation, transformed = compute_shap_explanation(pipeline, sample)
    global_importance = compute_global_feature_importance(explanation)

    local_row_index = max(0, min(args.row_index, len(X) - 1))
    local_feature_frame = X.iloc[[local_row_index]].copy()
    local_explanation = compute_local_explanation(pipeline, local_feature_frame, top_n=5)

    global_path = output_dir / "shap_global_importance.json"
    local_path = output_dir / "shap_local_explanation.json"
    metadata_path = output_dir / "shap_report_metadata.json"

    global_path.write_text(
        json.dumps(global_importance, indent=2),
        encoding="utf-8",
    )
    local_path.write_text(
        json.dumps(local_explanation, indent=2),
        encoding="utf-8",
    )
    metadata_path.write_text(
        json.dumps(
            {
                "model_name": model_bundle.get("model_name"),
                "feature_columns": feature_columns,
                "dataset_path": str(dataset_path),
                "sample_size": sample_size,
                "local_row_index": local_row_index,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    save_summary_plots(explanation, transformed, output_dir)

    print(f"✅ SHAP raporu üretildi: {output_dir}")
    print("Top global features:")
    for item in global_importance[:5]:
        print(f"- {item['name']}: {item['importance']}")

    if local_explanation:
        print("Top local features:")
        for item in local_explanation["top_features"]:
            print(
                f"- {item['name']}: impact={item['impact']} value={item['value']} direction={item['direction']}"
            )


if __name__ == "__main__":
    main()
