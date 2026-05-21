import csv
import httpx
import time
import logging
from datetime import datetime
from io import StringIO
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.hotspot import Hotspot
from app.services.cluster_service import cluster_service
from app.services.prediction_service import prediction_service

logger = logging.getLogger("fire_detection.nasa")

NASA_FIRMS_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
FIRMS_SOURCES = [
    "VIIRS_SNPP_NRT",
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA21_NRT",
]

# Ülke kodlarına karşılık gelen koordinat kutuları (west, south, east, north)
COUNTRY_BOUNDS = {
    "TUR": "26,36,45,42",
    "USA": "-125,24,-66,50",
    "AUS": "112,-44,154,-10",
    "BRA": "-74,-34,-35,5",
    "GRC": "19,34,30,42",
    "CYP": "32,34,35,36",
}


def _safe_float(value, default=None):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _safe_str(value, default=""):
    if value is None:
        return default
    return str(value)


def _build_v3_payload_from_nasa_row(row, hotspot):
    """
    NASA CSV row + DB hotspot objesinden V3 model için zengin payload üretir.

    DB'de saklanmayan frp / scan / track / bright_ti5 / daynight gibi alanları
    doğrudan NASA row'dan alır.
    """

    acq_date = getattr(hotspot, "acq_date", None)
    if hasattr(acq_date, "isoformat"):
        acq_date_str = acq_date.isoformat()
    else:
        acq_date_str = str(acq_date)

    acq_time = getattr(hotspot, "acq_time", None)

    bright_ti4 = _safe_float(row.get("bright_ti4"), default=getattr(hotspot, "brightness", None))
    bright_ti5 = _safe_float(row.get("bright_ti5"), default=None)

    return {
        "id": getattr(hotspot, "id", None),
        "hotspot_id": getattr(hotspot, "id", None),
        "latitude": float(getattr(hotspot, "latitude")),
        "longitude": float(getattr(hotspot, "longitude")),
        "acq_date": acq_date_str,
        "acq_time": str(acq_time).replace(".0", "").zfill(4),
        "brightness": _safe_float(row.get("brightness"), default=bright_ti4),
        "bright_ti4": bright_ti4,
        "bright_ti5": bright_ti5,
        "frp": _safe_float(row.get("frp"), default=0.0),
        "scan": _safe_float(row.get("scan"), default=1.0),
        "track": _safe_float(row.get("track"), default=1.0),
        "confidence": _safe_str(row.get("confidence"), default=getattr(hotspot, "confidence", "")),
        "daynight": _safe_str(row.get("daynight"), default="unknown"),
        "satellite": _safe_str(row.get("satellite"), default=getattr(hotspot, "satellite", "")),
        "instrument": _safe_str(row.get("instrument"), default="VIIRS"),
        "firms_source": _safe_str(row.get("source"), default=getattr(hotspot, "firms_source", "")),
        "type": _safe_float(row.get("type"), default=0),
    }


def _build_firms_url(source: str, bounds: str, days: int) -> str:
    return f"{NASA_FIRMS_URL}/{settings.NASA_API_KEY}/{source}/{bounds}/{days}"


def fetch_hotspots_from_nasa(db: Session, country: str = "TUR", days: int = 5):
    """
    NASA FIRMS API'den yangın noktalarını çeker ve DB'ye yazar.
    
    ÖNEMLİ: Şehir tespiti (geocoding) bu aşamada YAPILMAZ.
    Noktalar hemen DB'ye kaydedilir, şehir isimleri arka planda
    resolve_missing_cities() ile doldurulur.
    Bu sayede 500 nokta bile saniyeler içinde haritaya düşer.
    """
    from app.services.nasa_fetch_run_service import safe_save_nasa_fetch_run

    started_at = datetime.utcnow()
    bounds = COUNTRY_BOUNDS.get(country.upper(), COUNTRY_BOUNDS["TUR"])
    rows = []
    source_errors = []
    received_by_source = {source: 0 for source in FIRMS_SOURCES}
    inserted_by_source = {source: 0 for source in FIRMS_SOURCES}
    duplicates_by_source = {source: 0 for source in FIRMS_SOURCES}
    row_errors_by_source = {source: 0 for source in FIRMS_SOURCES}
    predictions_by_source = {source: 0 for source in FIRMS_SOURCES}

    with httpx.Client() as client:
        for source in FIRMS_SOURCES:
            url = _build_firms_url(source, bounds, days)
            logger.info("[FIRMS] Fetching source: %s", source)

            try:
                response = client.get(url, timeout=30.0)
                response.raise_for_status()

                csv_text = response.text.strip()
                source_rows = list(csv.DictReader(StringIO(csv_text))) if csv_text else []
                for row in source_rows:
                    row["source"] = source

                rows.extend(source_rows)
                received_by_source[source] = len(source_rows)
                logger.info("[FIRMS] Source %s returned %s rows", source, len(source_rows))
            except Exception as e:
                source_errors.append({
                    "source": source,
                    "error": str(e),
                })
                logger.warning("[FIRMS] Source %s failed: %s", source, e)

    created_hotspot_payloads = []
    inserted_count = 0
    duplicate_count = 0
    row_errors = []
    prediction_count = 0
    alert_count = 0
    prediction_errors = []
    weather_timeout_count = 0
    weather_fallback_count = 0
    weather_error_count = 0

    for row_number, row in enumerate(rows, start=2):
        try:
            acq_date_str = row.get("acq_date", "")
            acq_time_str = _safe_str(row.get("acq_time"), default="").replace(".0", "").zfill(4)
            parsed_date = None
            if acq_date_str:
                parsed_date = datetime.strptime(acq_date_str, "%Y-%m-%d").date()

            lat = float(row.get("latitude", 0))
            lon = float(row.get("longitude", 0))
            source = _safe_str(row.get("source"), default="VIIRS_SNPP_NRT")
            satellite = _safe_str(row.get("satellite"), default="")
            instrument = _safe_str(row.get("instrument"), default="VIIRS")

            # Duplicate (Çift Kayıt) Koruması:
            # Aynı koordinat + tarih + saat + uydu + enstrüman + kaynak aynı FIRMS gözlemi kabul edilir.
            existing = db.query(Hotspot).filter(
                Hotspot.latitude == lat,
                Hotspot.longitude == lon,
                Hotspot.acq_date == parsed_date,
                Hotspot.acq_time == acq_time_str,
                Hotspot.satellite == satellite,
                Hotspot.instrument == instrument,
                Hotspot.firms_source == source,
            ).first()

            if existing:
                duplicate_count += 1
                duplicates_by_source[source] = duplicates_by_source.get(source, 0) + 1
                continue

            with db.begin_nested():
                # Şehir = None → arka planda doldurulacak
                hotspot = Hotspot(
                    latitude=lat,
                    longitude=lon,
                    brightness=_safe_float(row.get("bright_ti4"), default=0.0),
                    bright_ti5=_safe_float(row.get("bright_ti5"), default=None),
                    frp=_safe_float(row.get("frp"), default=0.0),
                    scan=_safe_float(row.get("scan"), default=1.0),
                    track=_safe_float(row.get("track"), default=1.0),
                    confidence=row.get("confidence", ""),
                    daynight=_safe_str(row.get("daynight"), default="unknown"),
                    satellite=satellite,
                    instrument=instrument,
                    firms_source=source,
                    type=_safe_float(row.get("type"), default=0),
                    version=_safe_float(row.get("version"), default=2),
                    acq_date=parsed_date,
                    acq_time=acq_time_str,
                    city=None  # ← Geocoding SONRA yapılacak
                )
                db.add(hotspot)
                db.flush()
                cluster_service.assign_hotspot_to_cluster(db, hotspot)

            v3_payload = _build_v3_payload_from_nasa_row(row, hotspot)
            created_hotspot_payloads.append(v3_payload)
            inserted_count += 1
            inserted_by_source[source] = inserted_by_source.get(source, 0) + 1

        except Exception as e:
            source = _safe_str(row.get("source"), default="unknown")
            row_errors_by_source[source] = row_errors_by_source.get(source, 0) + 1
            row_errors.append({
                "row_number": row_number,
                "error": str(e),
                "latitude": row.get("latitude"),
                "longitude": row.get("longitude"),
                "acq_date": row.get("acq_date"),
                "acq_time": row.get("acq_time"),
                "source": row.get("source"),
            })
            logger.warning("NASA row işlenemedi | row=%s | error=%s", row_number, e)

    db.commit()

    prediction_limit = settings.V3_MAX_PREDICTIONS_PER_NASA_FETCH
    prediction_limit_applied = False
    prediction_limit_note = None

    if settings.ENABLE_V3_PREDICTION_ON_NASA_FETCH:
        max_predictions = prediction_limit
        prediction_limit_applied = len(created_hotspot_payloads) > max_predictions
        if prediction_limit_applied:
            prediction_limit_note = (
                f"Prediction processing limited to {max_predictions} records per fetch cycle"
            )
            logger.info(
                "%s | inserted_count=%s",
                prediction_limit_note,
                len(created_hotspot_payloads),
            )

        for payload in created_hotspot_payloads[:max_predictions]:
            try:
                result = prediction_service.predict_hotspot_with_db_context(
                    db=db,
                    hotspot_payload=payload,
                )

                if result.get("success"):
                    prediction_count += 1
                    source = payload.get("firms_source") or "unknown"
                    predictions_by_source[source] = predictions_by_source.get(source, 0) + 1
                    weather_status = result.get("feature_status", {}).get("weather", {})
                    if weather_status and not weather_status.get("weather_fetch_ok"):
                        weather_fallback_count += 1

                if result.get("created_alert_id") is not None:
                    alert_count += 1

            except Exception as e:
                error_text = str(e)
                if "timeout" in error_text.lower() or "timed out" in error_text.lower():
                    weather_timeout_count += 1
                weather_error_count += 1
                prediction_errors.append({
                    "hotspot_id": payload.get("id"),
                    "error": error_text,
                })

    result = {
        "inserted_count": inserted_count,
        "received_count": len(rows),
        "duplicate_count": duplicate_count,
        "row_error_count": len(row_errors),
        "row_errors": row_errors[:10],
        "source_error_count": len(source_errors),
        "source_errors": source_errors[:10],
        "received_by_source": received_by_source,
        "inserted_by_source": inserted_by_source,
        "duplicates_by_source": duplicates_by_source,
        "row_errors_by_source": row_errors_by_source,
        "predictions_by_source": predictions_by_source,
        "prediction_limit_per_fetch": prediction_limit,
        "prediction_limit_applied": prediction_limit_applied,
        "prediction_limit_note": prediction_limit_note,
        "v3_prediction_count": prediction_count,
        "v3_alert_count": alert_count,
        "v3_prediction_errors": prediction_errors[:10],
        "weather_timeout_count": weather_timeout_count,
        "weather_fallback_count": weather_fallback_count,
        "weather_error_count": weather_error_count,
    }

    logger.info(
        "NASA fetch tamamlandı | received_count=%s | inserted_count=%s | duplicate_count=%s | row_error_count=%s | source_error_count=%s | v3_prediction_count=%s | v3_alert_count=%s | prediction_errors=%s",
        len(rows),
        inserted_count,
        duplicate_count,
        len(row_errors),
        len(source_errors),
        prediction_count,
        alert_count,
        len(prediction_errors),
    )
    _log_firms_summary(result)
    safe_save_nasa_fetch_run(
        db,
        result=result,
        started_at=started_at,
        finished_at=datetime.utcnow(),
    )
    return result


def _log_firms_summary(result: dict) -> None:
    summary_lines = ["[FIRMS SUMMARY]"]
    received_by_source = result.get("received_by_source", {})
    inserted_by_source = result.get("inserted_by_source", {})
    duplicates_by_source = result.get("duplicates_by_source", {})
    predictions_by_source = result.get("predictions_by_source", {})
    row_errors_by_source = result.get("row_errors_by_source", {})

    for source in FIRMS_SOURCES:
        summary_lines.extend([
            f"Source: {source}",
            f"Received: {received_by_source.get(source, 0)}",
            f"Inserted: {inserted_by_source.get(source, 0)}",
            f"Duplicate: {duplicates_by_source.get(source, 0)}",
            f"Predictions: {predictions_by_source.get(source, 0)}",
            f"Errors: {row_errors_by_source.get(source, 0)}",
            "",
        ])

    summary_lines.extend([
        f"Total received: {result.get('received_count', 0)}",
        f"Total inserted: {result.get('inserted_count', 0)}",
        f"Total duplicate: {result.get('duplicate_count', 0)}",
        f"Total predictions: {result.get('v3_prediction_count', 0)}",
        f"Source errors: {result.get('source_error_count', 0)}",
    ])
    if result.get("prediction_limit_note"):
        summary_lines.append(result["prediction_limit_note"])

    logger.info("\n".join(summary_lines))


def resolve_missing_cities(db: Session, batch_size: int = 50):
    """
    Şehir bilgisi eksik (NULL) olan hotspot'ların
    şehir isimlerini Nominatim ile arka planda doldurur.
    
    - Nominatim rate limit'e takılmamak için istekler arası 1.1 sn bekler
    - batch_size ile tek seferde en fazla N nokta işlenir
    - Her döngüde çağrılır, kalan noktalar bir sonraki döngüde işlenir
    
    Bu fonksiyon BLOKLAYICI DEĞİL — yangın noktaları zaten haritada.
    Sadece city=None olan kayıtları dener; "Bilinmiyor" tekrar seçilmez.
    """
    import ssl
    import certifi
    from geopy.geocoders import Nominatim

    # Şehri eksik olan noktaları bul
    missing = (
        db.query(Hotspot)
        .filter(Hotspot.city == None)
        .order_by(Hotspot.id.desc())  # En yeni noktalar önce
        .limit(batch_size)
        .all()
    )

    if not missing:
        return 0

    ssl_context = ssl.create_default_context(cafile=certifi.where())
    geolocator = Nominatim(user_agent="fire-system-v1", ssl_context=ssl_context)
    processed = 0
    resolved = 0
    unknown = 0
    errors = 0

    for hotspot in missing:
        processed += 1
        try:
            location = geolocator.reverse(
                (hotspot.latitude, hotspot.longitude),
                language="tr",
                exactly_one=True,
                timeout=5
            )
            if location and location.raw.get("address"):
                address = location.raw["address"]
                city_name = (
                    address.get("city")
                    or address.get("town")
                    or address.get("village")
                    or address.get("municipality")
                    or address.get("county")
                    or address.get("district")
                    or address.get("state_district")
                    or address.get("province")
                    or address.get("state")
                    or "Bilinmiyor"
                )
                hotspot.city = city_name
                if city_name == "Bilinmiyor":
                    unknown += 1
                else:
                    resolved += 1
            else:
                hotspot.city = "Bilinmiyor"
                unknown += 1
        except Exception as e:
            hotspot.city = "Bilinmiyor"
            errors += 1
            logger.warning(
                "Geocoding hatası | hotspot_id=%s | lat=%s | lon=%s | error=%s",
                hotspot.id,
                hotspot.latitude,
                hotspot.longitude,
                e,
            )

        # Nominatim rate limit: max 1 istek/saniye (ücretsiz kullanım)
        time.sleep(1.1)

    db.commit()
    logger.info(
        "City resolve tamamlandı | processed=%s | resolved=%s | unknown=%s | errors=%s",
        processed,
        resolved,
        unknown,
        errors,
    )
    return resolved
