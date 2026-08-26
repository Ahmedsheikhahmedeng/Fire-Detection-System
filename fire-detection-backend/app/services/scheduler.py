"""
Arka Plan Zamanlayıcı — NASA + Weather + ML döngüsü
====================================================
- Her 6 saatte: NASA → Weather → ML tam döngü
- Her 1 saatte: Weather + ML refresh (mevcut noktalar)
- Tüm ağır iş burada yapılır, API endpoint'leri sadece DB okur.
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from app.core.time_utils import utc_now, utc_now_naive
from app.core.database import SessionLocal
from app.models.hotspot import Hotspot
from app.models.weather import WeatherData
from app.models.prediction import Prediction
from app.services.nasa_service import fetch_hotspots_from_nasa, resolve_missing_cities
from app.services.prediction_service import prediction_service
from app.services.scheduler_state import write_scheduler_state
from app.services.cluster_status_service import update_cluster_statuses
from app.websocket.manager import manager

logger = logging.getLogger("fire_detection.scheduler")

# ── Zamanlama sabitleri (saniye) ──
WEATHER_ML_INTERVAL = 3600    # 1 saat
CITY_RESOLVE_BATCH_SIZE = 100
WEATHER_ML_MAX_SECONDS = 90

# ── Durum takibi (GET /map/status için) ──
scheduler_status = {
    "last_nasa_fetch": None,
    "last_weather_refresh": None,
    "last_ml_scan": None,
    "nasa_hotspots_inserted": 0,
    "v3_prediction_count": 0,
    "v3_alert_count": 0,
    "ml_processed": 0,
    "ml_high_risk": 0,
    "is_running": False,
    "current_task": None,
    "last_error": None,
    "last_nasa_error": None,
    "last_refresh_error": None,
    "last_city_resolve_error": None,
    "last_city_resolve_at": None,
    "last_city_resolved_count": 0,
    "last_cluster_status_update": None,
    "cluster_status_counts": None,
    "last_cluster_status_error": None,
    "last_cycle_error": None,
    "last_cycle_started_at": None,
    "last_cycle_finished_at": None,
    "last_cycle_type": None,
}

_scheduler_task = None
_scheduler_cycle_lock = asyncio.Lock()
_scheduler_lock = _scheduler_cycle_lock


def _get_scheduler_lock():
    global _scheduler_lock, _scheduler_cycle_lock
    if _scheduler_lock is None:
        _scheduler_lock = _scheduler_cycle_lock
    return _scheduler_lock


def _set_scheduler_error(scope: str, error: Exception) -> None:
    message = f"{type(error).__name__}: {error}"
    scheduler_status["last_error"] = message
    scheduler_status[f"last_{scope}_error"] = message


def _clear_scheduler_error(scope: str) -> None:
    scheduler_status[f"last_{scope}_error"] = None


def _fetch_nasa_data_sync():
    db = SessionLocal()
    try:
        return fetch_hotspots_from_nasa(db)
    finally:
        db.close()


def _write_scheduler_state_sync(values: dict) -> None:
    db = SessionLocal()
    try:
        write_scheduler_state(db, values)
    finally:
        db.close()


def _update_cluster_statuses_sync():
    db = SessionLocal()
    try:
        return update_cluster_statuses(db)
    finally:
        db.close()


def _safe_float(value, default=None):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _hotspot_datetime(hotspot: Hotspot):
    if hotspot.acq_date is None or hotspot.acq_time is None:
        return None

    try:
        acq_time_str = str(hotspot.acq_time).replace(".0", "").zfill(4)
        return datetime.strptime(f"{hotspot.acq_date} {acq_time_str}", "%Y-%m-%d %H%M")
    except Exception:
        return None


def _build_v3_payload_from_hotspot_row(hotspot: Hotspot) -> dict:
    bright_ti4 = _safe_float(getattr(hotspot, "brightness", None), default=0.0)
    bright_ti5 = _safe_float(getattr(hotspot, "bright_ti5", None), default=bright_ti4)

    return {
        "id": hotspot.id,
        "hotspot_id": hotspot.id,
        "latitude": float(hotspot.latitude),
        "longitude": float(hotspot.longitude),
        "acq_date": hotspot.acq_date.isoformat() if hotspot.acq_date else None,
        "acq_time": str(hotspot.acq_time).replace(".0", "").zfill(4),
        "brightness": bright_ti4,
        "bright_ti4": bright_ti4,
        "bright_ti5": bright_ti5,
        "frp": _safe_float(getattr(hotspot, "frp", None), default=0.0),
        "scan": _safe_float(getattr(hotspot, "scan", None), default=1.0),
        "track": _safe_float(getattr(hotspot, "track", None), default=1.0),
        "confidence": getattr(hotspot, "confidence", None) or "unknown",
        "daynight": getattr(hotspot, "daynight", None) or "unknown",
        "satellite": getattr(hotspot, "satellite", None) or "unknown",
        "instrument": getattr(hotspot, "instrument", None) or "VIIRS",
        "firms_source": getattr(hotspot, "firms_source", None) or "VIIRS_SNPP_NRT",
        "type": _safe_float(getattr(hotspot, "type", None), default=0),
        "version": _safe_float(getattr(hotspot, "version", None), default=2),
    }


async def _fetch_nasa_data():
    """NASA FIRMS'den yeni hotspot verisini çek."""
    scheduler_status["current_task"] = "NASA veri çekiliyor"
    logger.info("🛰️ NASA FIRMS veri çekme başladı...")
    try:
        result = await asyncio.to_thread(_fetch_nasa_data_sync)
        if isinstance(result, dict):
            inserted = result.get("inserted_count", 0)
            scheduler_status["v3_prediction_count"] = result.get("v3_prediction_count", 0)
            scheduler_status["v3_alert_count"] = result.get("v3_alert_count", 0)
        else:
            inserted = result
            result = {"inserted_count": inserted}

        scheduler_status["nasa_hotspots_inserted"] = inserted
        scheduler_status["last_nasa_fetch"] = utc_now().isoformat()
        status_report = {}
        try:
            status_report = await asyncio.to_thread(_update_cluster_statuses_sync)
            scheduler_status["last_cluster_status_update"] = utc_now().isoformat()
            scheduler_status["cluster_status_counts"] = {
                "active": status_report.get("active", 0),
                "monitoring": status_report.get("monitoring", 0),
                "resolved": status_report.get("resolved", 0),
            }
            _clear_scheduler_error("cluster_status")
        except Exception as status_error:
            _set_scheduler_error("cluster_status", status_error)
            logger.exception("Cluster status update hatası")
        await asyncio.to_thread(
            _write_scheduler_state_sync,
            {
                "last_nasa_fetch": scheduler_status["last_nasa_fetch"],
                "nasa_hotspots_inserted": inserted,
                "v3_prediction_count": scheduler_status["v3_prediction_count"],
                "v3_alert_count": scheduler_status["v3_alert_count"],
                "last_cluster_status_update": scheduler_status["last_cluster_status_update"],
                "cluster_status_counts": scheduler_status["cluster_status_counts"],
            },
        )
        logger.info(
            "🛰️ NASA: inserted_count=%s | v3_prediction_count=%s | v3_alert_count=%s",
            inserted,
            scheduler_status["v3_prediction_count"],
            scheduler_status["v3_alert_count"],
        )
        logger.info(
            "🔥 Cluster status update: active=%s | monitoring=%s | resolved=%s | changed=%s",
            status_report.get("active", 0),
            status_report.get("monitoring", 0),
            status_report.get("resolved", 0),
            status_report.get("changed_clusters", 0),
        )
        _clear_scheduler_error("nasa")
        return result
    except Exception as e:
        _set_scheduler_error("nasa", e)
        logger.exception("NASA veri çekme hatası")
        return 0


def _refresh_weather_and_ml_sync():
    db = SessionLocal()
    processed = 0
    high_risk = 0
    total = 0
    started_at = time.monotonic()
    stopped_by_deadline = False

    try:
        cutoff = utc_now_naive() - timedelta(hours=24)
        candidates = (
            db.query(Hotspot)
            .filter(Hotspot.acq_date >= cutoff.date())
            .order_by(Hotspot.id.desc())
            .limit(200)
            .all()
        )

        for hotspot in candidates:
            if time.monotonic() - started_at > WEATHER_ML_MAX_SECONDS:
                stopped_by_deadline = True
                logger.warning(
                    "V3 refresh time limit reached; remaining hotspots will be processed in next cycle | processed=%s total_seen=%s limit_seconds=%s",
                    processed,
                    total,
                    WEATHER_ML_MAX_SECONDS,
                )
                break

            hotspot_dt = _hotspot_datetime(hotspot)
            if hotspot_dt is None or hotspot_dt < cutoff:
                continue

            total += 1
            existing_prediction = (
                db.query(Prediction)
                .filter(Prediction.hotspot_id == hotspot.id)
                .order_by(Prediction.id.desc())
                .first()
            )
            existing_weather = (
                db.query(WeatherData)
                .filter(WeatherData.hotspot_id == hotspot.id)
                .order_by(WeatherData.id.desc())
                .first()
            )
            if existing_prediction and existing_weather:
                continue

            try:
                result = prediction_service.predict_hotspot_with_db_context(
                    db=db,
                    hotspot_payload=_build_v3_payload_from_hotspot_row(hotspot),
                )
                if result.get("success"):
                    processed += 1
                    decision_level = int(
                        result.get("decision", {}).get("decision_level", 0) or 0
                    )
                    if decision_level >= 2:
                        high_risk += 1
            except Exception:
                logger.exception("V3 refresh hotspot %s hatası", hotspot.id)
                continue

        return {
            "processed": processed,
            "high_risk": high_risk,
            "total": total,
            "skipped": False,
            "mode": "v3_missing_prediction_refresh",
            "stopped_by_deadline": stopped_by_deadline,
        }
    except Exception as e:
        logger.exception("V3 refresh hatası")
        return {
            "processed": processed,
            "high_risk": high_risk,
            "total": 0,
            "error": f"{type(e).__name__}: {e}",
        }
    finally:
        db.close()


async def _refresh_weather_and_ml():
    """Tüm aktif hotspot'lar için hava verisi + ML tahmini güncelle."""
    scheduler_status["current_task"] = "Weather + ML güncelleniyor"
    logger.info("🌤️ Weather + ML refresh başladı...")
    try:
        result = await asyncio.to_thread(_refresh_weather_and_ml_sync)
        scheduler_status["ml_processed"] = result["processed"]
        scheduler_status["ml_high_risk"] = result["high_risk"]
        scheduler_status["last_weather_refresh"] = utc_now().isoformat()
        scheduler_status["last_ml_scan"] = utc_now().isoformat()
        await asyncio.to_thread(
            _write_scheduler_state_sync,
            {
                "last_weather_refresh": scheduler_status["last_weather_refresh"],
                "last_ml_scan": scheduler_status["last_ml_scan"],
                "ml_processed": scheduler_status["ml_processed"],
                "ml_high_risk": scheduler_status["ml_high_risk"],
            },
        )
        if result.get("error"):
            scheduler_status["last_refresh_error"] = result["error"]
            scheduler_status["last_error"] = result["error"]
        else:
            _clear_scheduler_error("refresh")

        logger.info(
            f"✅ Refresh tamamlandı: {result['processed']}/{result['total']} işlendi, "
            f"{result['high_risk']} yüksek risk."
        )
        return result
    except Exception as e:
        _set_scheduler_error("refresh", e)
        logger.exception("Weather+ML refresh hatası")
        return {
            "processed": 0,
            "high_risk": 0,
            "total": 0,
        }


def _resolve_cities_background_sync():
    db = SessionLocal()
    try:
        return resolve_missing_cities(db, batch_size=CITY_RESOLVE_BATCH_SIZE)
    finally:
        db.close()


async def _resolve_cities_background():
    """Şehir bilgisi eksik olan noktaları arka planda doldur."""
    scheduler_status["current_task"] = "Şehir isimleri çözülüyor"
    logger.info("🏙️ Arka plan şehir çözümleme başladı...")
    try:
        resolved = await asyncio.to_thread(_resolve_cities_background_sync)
        scheduler_status["last_city_resolve_at"] = utc_now().isoformat()
        scheduler_status["last_city_resolved_count"] = resolved
        await asyncio.to_thread(
            _write_scheduler_state_sync,
            {
                "last_city_resolve_at": scheduler_status["last_city_resolve_at"],
                "last_city_resolved_count": resolved,
            },
        )
        logger.info(f"🏙️ {resolved} noktanın şehri çözüldü.")
        _clear_scheduler_error("city_resolve")
    except Exception as e:
        _set_scheduler_error("city_resolve", e)
        logger.exception("Şehir çözümleme hatası")


async def run_full_cycle():
    """Tam döngü: NASA → Weather → ML → Geocoding → Frontend bildir."""
    lock = _get_scheduler_lock()
    if lock.locked():
        logger.info("Tam scheduler döngüsü atlandı; başka bir döngü çalışıyor.")
        return {"skipped": True, "reason": "scheduler_cycle_already_running"}

    async with lock:
        scheduler_status["is_running"] = True
        scheduler_status["last_cycle_type"] = "full"
        scheduler_status["last_cycle_started_at"] = utc_now().isoformat()
        try:
            await _fetch_nasa_data()
            # City lookup is independent from weather/ML and should not be blocked
            # by slow external weather API calls.
            await _resolve_cities_background()
            await manager.broadcast({
                "type": "HOTSPOT_UPDATED",
                "message": "Şehir bilgileri güncellendi"
            })
            await _refresh_weather_and_ml()
            # Frontend'e hemen bildir — noktalar artık haritada!
            await manager.broadcast({
                "type": "HOTSPOT_UPDATED",
                "message": "Harita verileri güncellendi"
            })
            _clear_scheduler_error("cycle")
            return {"skipped": False, "type": "full"}
        except Exception as e:
            _set_scheduler_error("cycle", e)
            logger.exception("Tam scheduler döngüsü hatası")
            return {"skipped": False, "type": "full", "error": str(e)}
        finally:
            scheduler_status["is_running"] = False
            scheduler_status["current_task"] = None
            scheduler_status["last_cycle_finished_at"] = utc_now().isoformat()


async def run_refresh_cycle():
    """Hafif döngü: Weather + ML refresh → şehir çözümleme → Frontend bildir."""
    lock = _get_scheduler_lock()
    if lock.locked():
        logger.info("Refresh scheduler döngüsü atlandı; başka bir döngü çalışıyor.")
        return {"skipped": True, "reason": "scheduler_cycle_already_running"}

    async with lock:
        scheduler_status["is_running"] = True
        scheduler_status["last_cycle_type"] = "refresh"
        scheduler_status["last_cycle_started_at"] = utc_now().isoformat()
        try:
            # Resolve city names first so geocoding keeps progressing even when
            # weather providers are slow or temporarily unavailable.
            await _resolve_cities_background()
            await manager.broadcast({
                "type": "HOTSPOT_UPDATED",
                "message": "Şehir bilgileri güncellendi"
            })
            result = await _refresh_weather_and_ml()
            await manager.broadcast({
                "type": "HOTSPOT_UPDATED",
                "message": "ML verileri güncellendi"
            })
            _clear_scheduler_error("cycle")
            if not isinstance(result, dict):
                result = {}
            return {"skipped": False, "type": "refresh", **result}
        except Exception as e:
            _set_scheduler_error("refresh", e)
            _set_scheduler_error("cycle", e)
            logger.exception("Refresh scheduler döngüsü hatası")
            return {"skipped": False, "type": "refresh", "error": str(e)}
        finally:
            scheduler_status["is_running"] = False
            scheduler_status["current_task"] = None
            scheduler_status["last_cycle_finished_at"] = utc_now().isoformat()


async def _scheduler_loop():
    """
    Ana zamanlayıcı döngüsü:
    - İlk açılışta hemen tam döngü çalıştır
    - Sonra 1 saatte bir Weather+ML refresh
    - Her 6 saatte bir NASA tam döngü
    """
    logger.info("⏰ Scheduler başlatıldı.")

    try:
        # İlk açılışta hemen çalıştır
        await run_full_cycle()
    except asyncio.CancelledError:
        raise
    except Exception as e:
        _set_scheduler_error("cycle", e)
        logger.exception("İlk scheduler döngüsü beklenmeyen hata ile tamamlanamadı")

    cycle_count = 0
    while True:
        try:
            await asyncio.sleep(WEATHER_ML_INTERVAL)
            cycle_count += 1

            if cycle_count % 6 == 0:
                # Her 6 saatte tam döngü (NASA dahil)
                logger.info("⏰ 6-saatlik NASA döngüsü tetiklendi.")
                await run_full_cycle()
            else:
                # Sadece Weather + ML refresh
                logger.info("⏰ 1-saatlik refresh döngüsü tetiklendi.")
                await run_refresh_cycle()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            _set_scheduler_error("cycle", e)
            logger.exception("Scheduler döngüsü beklenmeyen hata sonrası devam edecek")
            await asyncio.sleep(60)


def _handle_scheduler_task_done(task: asyncio.Task) -> None:
    """Log unexpected scheduler task exits so background work does not fail silently."""
    if task.cancelled():
        return

    try:
        task.result()
    except Exception as e:
        _set_scheduler_error("cycle", e)
        logger.exception("Background scheduler task beklenmeyen şekilde durdu")


def start_scheduler():
    """Scheduler'ı asyncio task olarak başlatır."""
    global _scheduler_task

    if _scheduler_task and not _scheduler_task.done():
        logger.info("Background scheduler zaten çalışıyor.")
        return _scheduler_task

    _scheduler_task = asyncio.create_task(_scheduler_loop())
    _scheduler_task.add_done_callback(_handle_scheduler_task_done)
    logger.info("🚀 Background scheduler başlatıldı.")
    return _scheduler_task


def stop_scheduler():
    """Scheduler'ı durdurur."""
    global _scheduler_task
    if _scheduler_task:
        _scheduler_task.cancel()
        _scheduler_task = None
        logger.info("🛑 Background scheduler durduruldu.")


def get_scheduler_status() -> dict:
    """Frontend ve /map/status için scheduler durumunu döndürür."""
    return {**scheduler_status}
