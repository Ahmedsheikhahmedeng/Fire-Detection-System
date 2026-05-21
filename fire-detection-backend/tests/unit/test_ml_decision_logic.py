import copy

import pytest

from app.services.ml_service import v3_fire_model_service


@pytest.fixture
def fake_threshold_config(monkeypatch):
    """
    Gercek model dosyalarini yuklemeden V3 decision logic test edilir.
    Sadece threshold_config fake olarak verilir.
    """
    original_config = copy.deepcopy(v3_fire_model_service.threshold_config)

    test_config = {
        "version": "v3-test",

        "lightgbm_watch_threshold": 0.40,
        "catboost_watch_threshold": 0.40,
        "xgboost_watch_threshold": 0.40,
        "hgb_core_watch_threshold": 0.40,
        "ensemble_watch_threshold": 0.50,

        "rf_balanced_threshold": 0.60,
        "rf_recall90_threshold": 0.70,

        "extratrees_strict_threshold": 0.85,
        "extratrees_recall90_threshold": 0.70,

        "decision_system": {
            "level_0": "low_risk_no_fire",
            "level_1": "watch_early_warning",
            "level_2": "medium_risk_fire",
            "level_3": "high_risk_fire",
            "level_4": "critical_fire_alert",
        },
    }

    monkeypatch.setattr(v3_fire_model_service, "threshold_config", test_config)

    yield test_config

    monkeypatch.setattr(v3_fire_model_service, "threshold_config", original_config)


def make_decision(
    ensemble_prob=0.0,
    lightgbm_prob=0.0,
    catboost_prob=0.0,
    xgboost_prob=0.0,
    hgb_prob=0.0,
    rf_prob=0.0,
    extratrees_prob=0.0,
):
    return v3_fire_model_service._make_decision(
        ensemble_prob=ensemble_prob,
        lightgbm_prob=lightgbm_prob,
        catboost_prob=catboost_prob,
        xgboost_prob=xgboost_prob,
        hgb_prob=hgb_prob,
        rf_prob=rf_prob,
        extratrees_prob=extratrees_prob,
    )


def test_no_watch_signal_returns_level_0(fake_threshold_config):
    decision = make_decision(
        ensemble_prob=0.10,
        lightgbm_prob=0.10,
        catboost_prob=0.10,
        xgboost_prob=0.10,
        hgb_prob=0.10,
        rf_prob=0.10,
        extratrees_prob=0.10,
    )

    assert decision["watch_early_warning"] is False
    assert decision["decision_level"] == 0
    assert decision["decision_name"] == "low_risk_no_fire"


def test_lightgbm_watch_triggers_level_1_without_gates(fake_threshold_config):
    decision = make_decision(
        lightgbm_prob=0.41,
        rf_prob=0.10,
        extratrees_prob=0.10,
    )

    assert decision["lightgbm_watch"] is True
    assert decision["watch_early_warning"] is True
    assert decision["decision_level"] == 1
    assert decision["decision_name"] == "watch_early_warning"


def test_catboost_watch_triggers_level_1_without_gates(fake_threshold_config):
    decision = make_decision(
        catboost_prob=0.41,
        rf_prob=0.10,
        extratrees_prob=0.10,
    )

    assert decision["catboost_watch"] is True
    assert decision["watch_early_warning"] is True
    assert decision["decision_level"] == 1
    assert decision["decision_name"] == "watch_early_warning"


def test_xgboost_watch_triggers_early_warning(fake_threshold_config):
    decision = make_decision(
        xgboost_prob=0.41,
        rf_prob=0.10,
        extratrees_prob=0.10,
    )

    assert decision["xgboost_watch"] is True
    assert decision["watch_early_warning"] is True
    assert decision["decision_level"] == 1


def test_hgb_core_watch_triggers_early_warning(fake_threshold_config):
    decision = make_decision(
        hgb_prob=0.41,
        rf_prob=0.10,
        extratrees_prob=0.10,
    )

    assert decision["hgb_core_watch"] is True
    assert decision["watch_early_warning"] is True
    assert decision["decision_level"] == 1


def test_ensemble_watch_triggers_early_warning(fake_threshold_config):
    decision = make_decision(
        ensemble_prob=0.51,
        rf_prob=0.10,
        extratrees_prob=0.10,
    )

    assert decision["ensemble_watch"] is True
    assert decision["watch_early_warning"] is True
    assert decision["decision_level"] == 1


def test_rf_balanced_gate_creates_level_2_when_watch_exists(fake_threshold_config):
    decision = make_decision(
        ensemble_prob=0.51,
        rf_prob=0.61,
        extratrees_prob=0.10,
    )

    assert decision["watch_early_warning"] is True
    assert decision["rf_balanced_gate"] is True
    assert decision["decision_level"] == 2
    assert decision["decision_name"] == "medium_risk_fire"


def test_rf_recall90_gate_creates_level_3_when_watch_exists(fake_threshold_config):
    decision = make_decision(
        ensemble_prob=0.51,
        rf_prob=0.71,
        extratrees_prob=0.10,
    )

    assert decision["watch_early_warning"] is True
    assert decision["rf_recall90_gate"] is True
    assert decision["decision_level"] == 3
    assert decision["decision_name"] == "high_risk_fire"


def test_extratrees_recall90_gate_creates_level_3_when_watch_exists(fake_threshold_config):
    decision = make_decision(
        ensemble_prob=0.51,
        rf_prob=0.10,
        extratrees_prob=0.71,
    )

    assert decision["watch_early_warning"] is True
    assert decision["extratrees_recall90_gate"] is True
    assert decision["decision_level"] == 3
    assert decision["decision_name"] == "high_risk_fire"


def test_extratrees_strict_and_rf_balanced_create_level_4(fake_threshold_config):
    decision = make_decision(
        ensemble_prob=0.51,
        rf_prob=0.61,
        extratrees_prob=0.86,
    )

    assert decision["watch_early_warning"] is True
    assert decision["rf_balanced_gate"] is True
    assert decision["extratrees_strict_gate"] is True
    assert decision["decision_level"] == 4
    assert decision["decision_name"] == "critical_fire_alert"


def test_gates_without_watch_do_not_create_alert_level(fake_threshold_config):
    """
    V3 mantiginda once watch_early_warning gerekir.
    Watch yoksa RF/ExtraTrees yuksek olsa bile decision_level 0 kalir.
    """
    decision = make_decision(
        ensemble_prob=0.10,
        lightgbm_prob=0.10,
        catboost_prob=0.10,
        xgboost_prob=0.10,
        hgb_prob=0.10,
        rf_prob=0.95,
        extratrees_prob=0.95,
    )

    assert decision["watch_early_warning"] is False
    assert decision["rf_balanced_gate"] is True
    assert decision["extratrees_strict_gate"] is True
    assert decision["decision_level"] == 0
    assert decision["decision_name"] == "low_risk_no_fire"


def test_decision_response_contains_expected_boolean_fields(fake_threshold_config):
    decision = make_decision(
        ensemble_prob=0.51,
        lightgbm_prob=0.41,
        catboost_prob=0.41,
        xgboost_prob=0.41,
        hgb_prob=0.41,
        rf_prob=0.61,
        extratrees_prob=0.86,
    )

    expected_keys = [
        "watch_early_warning",
        "lightgbm_watch",
        "catboost_watch",
        "xgboost_watch",
        "hgb_core_watch",
        "ensemble_watch",
        "rf_balanced_gate",
        "rf_recall90_gate",
        "extratrees_strict_gate",
        "extratrees_recall90_gate",
        "decision_level",
        "decision_name",
    ]

    for key in expected_keys:
        assert key in decision
