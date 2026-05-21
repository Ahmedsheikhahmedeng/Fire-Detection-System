import json
from datetime import date

from app.core.database import SessionLocal
from app.models.alert import Alert
from app.models.hotspot import Hotspot
from app.models.prediction import Prediction
from app.services.nasa_service import _build_v3_payload_from_nasa_row
from app.services.prediction_service import prediction_service


db = SessionLocal()

try:
    mock_date = date(2025, 7, 21)
    mock_time = "1245"

    # Benzersiz koordinat: duplicate korumasından bağımsız, gerçek NASA beklemeden
    # yeni-hotspot production akışını doğrulamak için kullanılır.
    hotspot = Hotspot(
        latitude=38.987654,
        longitude=23.987654,
        brightness=338.4,
        confidence="nominal",
        satellite="N",
        acq_date=mock_date,
        acq_time=mock_time,
        city=None,
    )
    db.add(hotspot)
    db.flush()

    mock_nasa_row = {
        "latitude": str(hotspot.latitude),
        "longitude": str(hotspot.longitude),
        "acq_date": mock_date.isoformat(),
        "acq_time": mock_time,
        "brightness": "338.4",
        "bright_ti4": "338.4",
        "bright_ti5": "300.1",
        "frp": "26.7",
        "scan": "0.42",
        "track": "0.39",
        "confidence": "nominal",
        "daynight": "D",
        "satellite": "N",
        "instrument": "VIIRS",
        "type": "0",
    }

    payload = _build_v3_payload_from_nasa_row(mock_nasa_row, hotspot)

    prediction = prediction_service.predict_hotspot_with_db_context(
        db=db,
        hotspot_payload=payload,
    )

    db.commit()

    print(json.dumps(prediction, indent=2, ensure_ascii=False, default=str))

    assert prediction["success"] is True
    assert prediction.get("saved_prediction_id") is not None
    assert "created_alert_id" in prediction
    assert "probabilities" in prediction
    assert "decision" in prediction

    saved_prediction = (
        db.query(Prediction)
        .filter(Prediction.id == prediction["saved_prediction_id"])
        .first()
    )

    assert saved_prediction is not None
    assert saved_prediction.hotspot_id == hotspot.id
    assert saved_prediction.model_version == "v3"

    created_alert_id = prediction.get("created_alert_id")
    if prediction["decision"]["decision_level"] >= 2:
        assert created_alert_id is not None
        created_alert = db.query(Alert).filter(Alert.id == created_alert_id).first()
        assert created_alert is not None
        assert created_alert.hotspot_id == hotspot.id

    print("\nMock NASA V3 integration test PASSED.")

finally:
    db.close()
