import json

from app.core.database import SessionLocal
from app.services.nasa_service import fetch_hotspots_from_nasa

db = SessionLocal()

try:
    result = fetch_hotspots_from_nasa(
        db=db,
        country="TUR",
        days=1,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))

    if isinstance(result, dict):
        assert "inserted_count" in result
        assert "v3_prediction_count" in result
        assert "v3_alert_count" in result

    print("\nNASA fetch V3 integration test PASSED.")

finally:
    db.close()
