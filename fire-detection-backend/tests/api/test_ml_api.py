def test_ml_status_endpoint_returns_v3_status(client):
    response = client.get("/api/ml/status")

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert data["model_version"] == "v3"
    assert data["is_loaded"] is True

    assert "available_models" in data
    assert isinstance(data["available_models"], list)

    expected_models = {
        "hgb_core",
        "xgboost",
        "lightgbm",
        "catboost",
        "rf",
        "extratrees",
    }

    assert expected_models.issubset(set(data["available_models"]))

    assert "hgb_core_feature_count" in data
    assert "full_feature_count" in data
    assert data["hgb_core_feature_count"] > 0
    assert data["full_feature_count"] > 0

    assert "threshold_config" in data
    assert isinstance(data["threshold_config"], dict)


def test_validate_engineered_empty_input_returns_missing_features(client, api_key_headers):
    response = client.post(
        "/api/ml/validate-engineered",
        json={"features": {}},
        headers=api_key_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert "validation" in data

    validation = data["validation"]

    assert validation["is_valid"] is False
    assert validation["required_feature_count"] > 0
    assert validation["received_feature_count"] == 0
    assert len(validation["missing_features"]) > 0
