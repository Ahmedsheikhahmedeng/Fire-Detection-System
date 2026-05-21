from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.models.hotspot import Hotspot
from app.models.weather import WeatherData
from app.models.prediction import Prediction
from app.models.alert import Alert
from app.models.fire_cluster import FireCluster
from app.services.scheduler import get_scheduler_status
from app.services.scheduler_state import normalize_scheduler_state, read_scheduler_state
from app.core.config import settings
from app.core.time_utils import utc_now_naive
from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/map", tags=["Map"])

MAP_VISIBLE_HOURS = 24
MAP_QUERY_DAYS = 2
RISK_LEVELS = ["CRITICAL", "HIGH", "MEDIUM", "WATCH", "LOW", "UNKNOWN"]





def calculate_hours_ago(hotspot):
    if getattr(hotspot, "acq_date", None) is None:
        return 9999.0

    if getattr(hotspot, "acq_time", None) is None:
        # Eski kayıtlar için (acq_time olmayan), gece yarısını baz alarak tahmini saat hesapla
        acq_datetime = datetime.combine(hotspot.acq_date, datetime.min.time())
        hours = (utc_now_naive() - acq_datetime).total_seconds() / 3600
        return max(0.1, round(hours, 1))

    try:
        # acq_time format is typically '0840' for 08:40 AM or similar string representation.
        acq_time_str = str(hotspot.acq_time).strip().zfill(4)
        hour = int(acq_time_str[:2])
        minute = int(acq_time_str[2:])
    except Exception:
        acq_datetime = datetime.combine(hotspot.acq_date, datetime.min.time())
        hours = (utc_now_naive() - acq_datetime).total_seconds() / 3600
        return max(0.1, round(hours, 1))

    acq_datetime = datetime.combine(
        hotspot.acq_date,
        datetime.min.time()
    ).replace(hour=hour, minute=minute)

    # NASA returns time in UTC; DB date/time fields are stored as timezone-naive UTC.
    hours = (utc_now_naive() - acq_datetime).total_seconds() / 3600
    return max(0.1, round(hours, 1))


def hotspot_observation_iso(hotspot):
    if not hotspot or getattr(hotspot, "acq_date", None) is None:
        return None

    try:
        acq_time_str = str(getattr(hotspot, "acq_time", "") or "0000").replace(".0", "").zfill(4)
        hour = int(acq_time_str[:2])
        minute = int(acq_time_str[2:])
        observed_at = datetime.combine(hotspot.acq_date, datetime.min.time()).replace(
            hour=hour,
            minute=minute,
        )
    except Exception:
        observed_at = datetime.combine(hotspot.acq_date, datetime.min.time())

    return observed_at.replace(tzinfo=timezone.utc).isoformat()


def degree_to_direction(deg):
    if deg is None:
        return None

    directions = ["K", "KD", "D", "GD", "G", "GB", "B", "KB"]
    index = round(deg / 45) % 8
    return directions[index]


def round_optional(value, digits=1):
    if value is None:
        return None

    try:
        return round(float(value), digits)
    except Exception:
        return None


def risk_sort_value(risk_level):
    order = {
        "CRITICAL": 5,
        "HIGH": 4,
        "MEDIUM": 3,
        "WATCH": 2,
        "LOW": 1,
        "UNKNOWN": 0,
    }
    return order.get(str(risk_level or "UNKNOWN").upper(), 0)


# Şehir bilgisi NASA ingest aşamasında boş bırakılır.
# resolve_missing_cities() çalıştıktan sonra DB'den okunur.
# Boşsa frontend için "Çözülüyor..." gösterilir.


@router.get("/hotspots")
def get_map_hotspots(
    min_lat: Optional[float] = Query(None),
    max_lat: Optional[float] = Query(None),
    min_lon: Optional[float] = Query(None),
    max_lon: Optional[float] = Query(None),
    db: Session = Depends(get_db)
):
    # ── 1. Hotspot'ları çek ──
    query = db.query(Hotspot)
    if None not in [min_lat, max_lat, min_lon, max_lon]:
        query = query.filter(
            Hotspot.latitude >= min_lat,
            Hotspot.latitude <= max_lat,
            Hotspot.longitude >= min_lon,
            Hotspot.longitude <= max_lon
        )
    min_visible_date = utc_now_naive().date() - timedelta(days=MAP_QUERY_DAYS)
    query = (
        query
        .filter(Hotspot.acq_date >= min_visible_date)
        .order_by(Hotspot.id.desc())
        .limit(1000)
    )
    hotspots = query.all()

    # Haritada sadece son 24 saatlik hotspot'ları göster
    valid_hotspots = []
    for h in hotspots:
        hours = calculate_hours_ago(h)
        if hours <= MAP_VISIBLE_HOURS:
            valid_hotspots.append((h, hours))

    if not valid_hotspots:
        return []

    hotspot_ids = [h.id for h, _ in valid_hotspots]

    # ── 2. TOPLU sorgular (3 sorgu — N+1 yerine) ──
    # Weather: her hotspot için en son kayıt
    from sqlalchemy import func
    weather_sub = (
        db.query(
            WeatherData.hotspot_id,
            func.max(WeatherData.id).label("max_id")
        )
        .filter(WeatherData.hotspot_id.in_(hotspot_ids))
        .group_by(WeatherData.hotspot_id)
        .subquery()
    )
    weather_rows = (
        db.query(WeatherData)
        .join(weather_sub, WeatherData.id == weather_sub.c.max_id)
        .all()
    )
    weather_map = {w.hotspot_id: w for w in weather_rows}

    # Prediction: her hotspot için en son tahmin
    pred_sub = (
        db.query(
            Prediction.hotspot_id,
            func.max(Prediction.id).label("max_id")
        )
        .filter(Prediction.hotspot_id.in_(hotspot_ids))
        .group_by(Prediction.hotspot_id)
        .subquery()
    )
    pred_rows = (
        db.query(Prediction)
        .join(pred_sub, Prediction.id == pred_sub.c.max_id)
        .all()
    )
    pred_map = {p.hotspot_id: p for p in pred_rows}

    # Alert: aktif alarmlar
    alert_rows = (
        db.query(Alert)
        .filter(Alert.hotspot_id.in_(hotspot_ids), Alert.status == "ACTIVE")
        .all()
    )
    alert_map = {a.hotspot_id: a for a in alert_rows}

    cluster_ids = {h.cluster_id for h, _ in valid_hotspots if getattr(h, "cluster_id", None)}
    cluster_map = {}
    if cluster_ids:
        cluster_rows = db.query(FireCluster).filter(FireCluster.id.in_(cluster_ids)).all()
        cluster_map = {cluster.id: cluster for cluster in cluster_rows}

    # ── 3. Sonuç oluştur (sadece Python hesaplaması, DB sorgusu yok) ──
    result = []
    for hotspot, hours_ago in valid_hotspots:
        weather = weather_map.get(hotspot.id)
        prediction = pred_map.get(hotspot.id)
        active_alert = alert_map.get(hotspot.id)
        cluster = cluster_map.get(getattr(hotspot, "cluster_id", None))
        has_alert = active_alert is not None

        if prediction:
            ml_prob = prediction.fire_probability
            final_risk_percent = round(ml_prob * 100, 1) if ml_prob is not None else None
            final_risk_level = prediction.risk_level or "UNKNOWN"
            decision_level = getattr(prediction, "decision_level", None)
            decision_name = getattr(prediction, "decision_name", None)
            final_alert = has_alert or int(decision_level or 0) >= 2
            ml_source = "model"
        else:
            ml_prob = None
            final_risk_percent = None
            final_risk_level = "UNKNOWN"
            decision_level = None
            decision_name = None
            final_alert = False
            ml_source = "pending"

        temp = round_optional(weather.temperature, 1) if weather else None
        humidity = round_optional(weather.humidity, 1) if weather else None
        wind_speed = round_optional(weather.wind_speed, 1) if weather else None
        wind_deg = getattr(weather, 'wind_deg', None) if weather else None



        spread_direction = degree_to_direction(wind_deg)
        city = getattr(hotspot, "city", None) or "Çözülüyor..."

        if final_alert and final_risk_level == "CRITICAL" and final_risk_percent is not None:
            alert_message = f"KRİTİK: {city} bölgesinde %{final_risk_percent} yangın ihtimali tespit edildi!"
        elif final_alert and final_risk_level == "HIGH" and final_risk_percent is not None:
            alert_message = f"YÜKSEK RİSK: {city} bölgesinde yangın riski %{final_risk_percent}"
        elif final_alert and final_risk_level == "MEDIUM" and final_risk_percent is not None:
            alert_message = f"ORTA RİSK: {city} bölgesinde yangın riski %{final_risk_percent}"
        else:
            alert_message = None

        result.append({
            "id": hotspot.id,
            "cluster_id": getattr(hotspot, "cluster_id", None),
            "cluster_status": getattr(cluster, "status", None),
            "latitude": hotspot.latitude,
            "longitude": hotspot.longitude,
            "brightness": hotspot.brightness,
            "city": city,
            "temperature": temp,
            "humidity": humidity,
            "wind_speed": wind_speed,
            "spread_direction": spread_direction,
            "risk_level": final_risk_level,
            "fire_probability": ml_prob,
            "risk_percent": final_risk_percent,
            "decision_level": decision_level,
            "decision_name": decision_name,
            "observed_at": hotspot_observation_iso(hotspot),
            "hours_ago": hours_ago,
            "alert": final_alert,
            "has_active_alert": has_alert,
            "alert_id": active_alert.id if active_alert else None,
            "alert_message": alert_message,
            "ml_source": ml_source,
        })

    return result


@router.get("/status")
def get_map_status(db: Session = Depends(get_db)):
    """Scheduler durumunu DB tabanlı son veri zamanlarıyla birlikte döndürür."""
    status = normalize_scheduler_state(
        {**get_scheduler_status(), **read_scheduler_state(db)},
        bool(settings.ENABLE_SCHEDULER),
    )

    latest_hotspot = (
        db.query(Hotspot)
        .filter(Hotspot.acq_date.isnot(None))
        .order_by(Hotspot.acq_date.desc(), Hotspot.acq_time.desc(), Hotspot.id.desc())
        .first()
    )
    latest_prediction = (
        db.query(Prediction)
        .filter(Prediction.created_at.isnot(None))
        .order_by(Prediction.created_at.desc(), Prediction.id.desc())
        .first()
    )

    last_nasa_observation_at = hotspot_observation_iso(latest_hotspot)
    last_prediction_at = (
        latest_prediction.created_at.isoformat()
        if latest_prediction and latest_prediction.created_at
        else None
    )

    return {
        **status,
        "last_nasa_observation_at": last_nasa_observation_at,
        "last_prediction_at": last_prediction_at,
        "last_nasa_display_at": status.get("last_nasa_fetch") or last_nasa_observation_at,
        "last_ml_display_at": status.get("last_ml_scan") or last_prediction_at,
    }


@router.get("/stats")
def get_map_stats(db: Session = Depends(get_db)):
    """Dashboard istatistikleri — risk dağılımı, şehir bazlı, trend verisi."""
    from sqlalchemy import func
    from collections import Counter

    # Son tahminler (her hotspot için en son)
    pred_sub = (
        db.query(
            Prediction.hotspot_id,
            func.max(Prediction.id).label("max_id")
        )
        .group_by(Prediction.hotspot_id)
        .subquery()
    )
    predictions = (
        db.query(Prediction)
        .join(pred_sub, Prediction.id == pred_sub.c.max_id)
        .all()
    )

    pred_map = {p.hotspot_id: p for p in predictions}
    high_fire_hotspot_count = sum(
        1
        for prediction in predictions
        if int(getattr(prediction, "decision_level", 0) or 0) in {3, 4}
    )

    # Hotspot'lar + şehir eşlemesi
    total_hotspots = db.query(Hotspot).count()
    recent_date = utc_now_naive().date() - timedelta(days=7)
    hotspots = (
        db.query(Hotspot)
        .filter(Hotspot.acq_date >= recent_date)
        .order_by(Hotspot.id.desc())
        .limit(1000)
        .all()
    )

    # Risk dağılımı: prediction olmayan recent hotspot'lar UNKNOWN sayılır.
    risk_counts = Counter()
    for h in hotspots:
        pred = pred_map.get(h.id)
        level = pred.risk_level if pred else "UNKNOWN"
        risk_counts[level or "UNKNOWN"] += 1

    city_risk = {}
    for h in hotspots:
        city = getattr(h, "city", None) or "Çözülüyor..."
        pred = pred_map.get(h.id)
        if city not in city_risk:
            city_risk[city] = {level: 0 for level in RISK_LEVELS}
            city_risk[city]["total"] = 0
        city_risk[city]["total"] += 1
        if pred:
            level = pred.risk_level or "UNKNOWN"
            city_risk[city][level] = city_risk[city].get(level, 0) + 1
        else:
            city_risk[city]["UNKNOWN"] = city_risk[city].get("UNKNOWN", 0) + 1

    # Şehir bazlı sıralama (en riskli üstte)
    city_stats = sorted(
        [{"city": k, **v} for k, v in city_risk.items()],
        key=lambda x: (x.get("CRITICAL", 0), x.get("HIGH", 0), x.get("MEDIUM", 0), x.get("WATCH", 0)),
        reverse=True
    )

    # Günlük hotspot trend (son 7 gün)
    seven_days_ago = utc_now_naive().date() - timedelta(days=7)
    daily_counts = (
        db.query(Hotspot.acq_date, func.count(Hotspot.id))
        .filter(Hotspot.acq_date >= seven_days_ago)
        .group_by(Hotspot.acq_date)
        .order_by(Hotspot.acq_date)
        .all()
    )
    trend = [
        {"date": str(d), "count": c}
        for d, c in daily_counts if d
    ]

    # Hava verisi ortalamaları
    weather_rows = db.query(WeatherData).limit(500).all()
    temps = [w.temperature for w in weather_rows if w.temperature is not None]
    humids = [w.humidity for w in weather_rows if w.humidity is not None]
    winds = [w.wind_speed for w in weather_rows if w.wind_speed is not None]

    # Alert sayısı
    active_alerts = db.query(Alert).filter(Alert.status == "ACTIVE").count()
    total_alerts = db.query(Alert).count()

    return {
        "total_hotspots": total_hotspots,
        "high_fire_hotspot_count": high_fire_hotspot_count,
        "sampled_hotspots": len(hotspots),
        "risk_distribution": {level: risk_counts.get(level, 0) for level in RISK_LEVELS},
        "city_stats": city_stats[:10],
        "trend": trend,
        "weather_summary": {
            "avg_temp": round(sum(temps) / len(temps), 1) if temps else 0,
            "avg_humidity": round(sum(humids) / len(humids), 1) if humids else 0,
            "avg_wind": round(sum(winds) / len(winds), 1) if winds else 0,
            "min_temp": round(min(temps), 1) if temps else 0,
            "max_temp": round(max(temps), 1) if temps else 0,
        },
        "alerts": {
            "active": active_alerts,
            "total": total_alerts,
        },
    }
