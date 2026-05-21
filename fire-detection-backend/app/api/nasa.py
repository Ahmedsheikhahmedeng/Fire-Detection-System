from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.security import verify_api_key
from app.core.database import SessionLocal
from app.services.nasa_service import fetch_hotspots_from_nasa

router = APIRouter(prefix="/nasa", tags=["NASA"])

SUPPORTED_COUNTRIES = {"turkey", "greece", "cyprus"}
COUNTRY_ALIASES = {
    "turkiye": "turkey",
    "türkiye": "turkey",
    "tr": "turkey",
    "tur": "turkey",
    "gr": "greece",
    "grc": "greece",
    "cy": "cyprus",
    "cyp": "cyprus",
}
COUNTRY_SERVICE_CODES = {
    "turkey": "TUR",
    "greece": "GRC",
    "cyprus": "CYP",
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def normalize_country(country: str) -> str:
    value = country.strip().lower()
    value = COUNTRY_ALIASES.get(value, value)

    if value not in SUPPORTED_COUNTRIES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported country. Supported values: turkey, greece, cyprus",
        )

    return value


@router.post("/fetch-hotspots")
def fetch_hotspots(
    country: str = Query(
        default="turkey",
        description="Country to fetch NASA FIRMS data for. Supported values: turkey, greece, cyprus.",
    ),
    days: int = Query(
        default=5,
        ge=1,
        le=10,
        description="Number of past days to fetch from NASA FIRMS. Allowed range: 1-10.",
    ),
    _: bool = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """
    NASA'dan yeni hotspot çeker.
    V3 prediction + alert akışı fetch sırasında çalışır.
    """
    normalized_country = normalize_country(country)
    service_country = COUNTRY_SERVICE_CODES[normalized_country]

    result = fetch_hotspots_from_nasa(
        db=db,
        country=service_country,
        days=days,
    )
    inserted = result.get("inserted_count", 0) if isinstance(result, dict) else result

    return {
        "status": "success",
        "country": normalized_country,
        "days": days,
        "inserted": inserted,
        "result": result,
        "message": f"{inserted} yeni hotspot eklendi. V3 prediction NASA fetch sırasında çalıştı."
    }
