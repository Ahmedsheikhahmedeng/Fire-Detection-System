import logging
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("fire_detection.explainability")

_EXPLAINER_CACHE = {}


def _extract_estimator(pipeline):
    if hasattr(pipeline, "named_steps") and "model" in pipeline.named_steps:
        return pipeline.named_steps["model"]
    return pipeline


def transform_feature_frame(pipeline, feature_frame: pd.DataFrame) -> pd.DataFrame:
    transformed = feature_frame.copy()
    if hasattr(pipeline, "named_steps") and "imputer" in pipeline.named_steps:
        values = pipeline.named_steps["imputer"].transform(feature_frame)
        transformed = pd.DataFrame(
            values,
            columns=feature_frame.columns,
            index=feature_frame.index,
        )
    return transformed


def _get_cached_tree_explainer(pipeline):
    try:
        import shap
    except ImportError as exc:
        raise RuntimeError("SHAP kütüphanesi yüklü değil.") from exc

    estimator = _extract_estimator(pipeline)
    cache_key = id(estimator)
    cached = _EXPLAINER_CACHE.get(cache_key)
    if cached is not None:
        return shap, cached

    explainer = shap.TreeExplainer(estimator)
    _EXPLAINER_CACHE[cache_key] = explainer
    return shap, explainer


def _normalize_explanation(shap_module, shap_output, transformed_frame: pd.DataFrame):
    values = shap_output.values if hasattr(shap_output, "values") else shap_output
    base_values = getattr(shap_output, "base_values", None)

    if isinstance(values, list):
        values = values[1] if len(values) > 1 else values[0]
    values = np.asarray(values)

    if values.ndim == 3:
        values = values[:, :, -1]
    elif values.ndim == 1:
        values = values.reshape(1, -1)

    if base_values is None:
        base_values = np.zeros(values.shape[0], dtype=float)
    else:
        base_values = np.asarray(base_values)
        if base_values.ndim == 2:
            base_values = base_values[:, -1]
        elif base_values.ndim == 1 and base_values.shape[0] != values.shape[0]:
            if base_values.shape[0] > 1:
                base_values = np.repeat(float(base_values[-1]), values.shape[0])
        elif base_values.ndim == 0:
            base_values = np.repeat(float(base_values), values.shape[0])

    return shap_module.Explanation(
        values=values,
        base_values=base_values,
        data=transformed_frame.values,
        feature_names=list(transformed_frame.columns),
    )


def compute_shap_explanation(pipeline, feature_frame: pd.DataFrame):
    shap_module, explainer = _get_cached_tree_explainer(pipeline)
    transformed_frame = transform_feature_frame(pipeline, feature_frame)
    shap_output = explainer(transformed_frame)
    explanation = _normalize_explanation(shap_module, shap_output, transformed_frame)
    return explanation, transformed_frame


def summarize_top_features(
    explanation,
    raw_feature_frame: pd.DataFrame,
    top_n: int = 3,
) -> list[dict]:
    row_values = explanation.values[0]
    feature_names = list(raw_feature_frame.columns)
    row_data = raw_feature_frame.iloc[0]
    top_indices = np.argsort(np.abs(row_values))[::-1][:top_n]

    top_features = []
    for idx in top_indices:
        raw_value = row_data.iloc[idx]
        top_features.append(
            {
                "name": feature_names[idx],
                "impact": round(float(row_values[idx]), 4),
                "abs_impact": round(float(abs(row_values[idx])), 4),
                "value": None if pd.isna(raw_value) else round(float(raw_value), 4),
                "direction": "increase" if row_values[idx] >= 0 else "decrease",
            }
        )
    return top_features


def compute_local_explanation(
    pipeline,
    feature_frame: pd.DataFrame,
    top_n: int = 3,
) -> Optional[dict]:
    try:
        explanation, _ = compute_shap_explanation(pipeline, feature_frame)
    except Exception as exc:
        logger.warning("Yerel SHAP explanation üretilemedi: %s", exc)
        return None

    base_value = explanation.base_values
    if isinstance(base_value, np.ndarray):
        base_value = float(base_value[0])

    return {
        "method": "shap",
        "base_value": round(float(base_value), 4),
        "top_features": summarize_top_features(explanation, feature_frame, top_n=top_n),
    }


def compute_global_feature_importance(explanation) -> list[dict]:
    mean_abs = np.abs(explanation.values).mean(axis=0)
    feature_names = list(explanation.feature_names)
    ranked_indices = np.argsort(mean_abs)[::-1]

    return [
        {
            "name": feature_names[idx],
            "importance": round(float(mean_abs[idx]), 6),
        }
        for idx in ranked_indices
    ]
