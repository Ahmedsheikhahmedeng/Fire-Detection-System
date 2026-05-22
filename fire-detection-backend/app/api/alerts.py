import asyncio
from email.utils import parseaddr
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_api_key
from app.core.time_utils import utc_now
from app.core.config import settings
from app.services.email_service import email_alert_service
from app.services.alert_service import alert_service, create_alert_for_hotspot
from app.services.twilio_sms_service import send_sms_alert, twilio_sms_alert_service
from app.models.alert import Alert
from app.models.hotspot import Hotspot
from app.models.prediction import Prediction
from app.websocket.manager import manager

router = APIRouter(prefix="/alerts", tags=["Alerts"])


class AlertStatusUpdate(BaseModel):
    status: str


class TestEmailRequest(BaseModel):
    email: str


class TestSmsRequest(BaseModel):
    phone: str


def is_valid_email(value: str) -> bool:
    _, parsed_email = parseaddr(value)
    return bool(parsed_email and parsed_email == value and "@" in parsed_email)


def normalize_phone(value: str) -> str:
    return value.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")


@router.post("/check/{hotspot_id}")
def check_alert(
    hotspot_id: int,
    _: bool = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    result = create_alert_for_hotspot(hotspot_id, db)

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Prediction not found"
        )

    return result


@router.post("/test-email")
def send_test_email(
    payload: TestEmailRequest,
    _: bool = Depends(verify_api_key),
):
    recipient = payload.email.strip()

    if not is_valid_email(recipient):
        raise HTTPException(status_code=400, detail="Geçerli bir e-posta adresi girin")

    if not email_alert_service.has_smtp_credentials():
        raise HTTPException(status_code=503, detail="SMTP ayarları eksik")

    sent = email_alert_service.send_email(
        to_emails=[recipient],
        subject="Yangın Uyarısı - Test Mesajı",
        message=(
            "Bu bir test yangın uyarısıdır.\n"
            "Sistem e-posta bildirimi başarıyla çalışıyor.\n"
            "Risk seviyesi: TEST\n"
            "Olasılık: %92.0"
        ),
    )

    if not sent:
        raise HTTPException(status_code=502, detail="E-posta gönderilemedi")

    return {
        "sent": True,
        "email": recipient,
        "message": "Test e-postası gönderildi",
    }


@router.post("/test-sms")
def send_test_sms(payload: TestSmsRequest):
    recipient = normalize_phone(payload.phone.strip())
    configured_recipient = normalize_phone(settings.ALERT_SMS_TO.strip())

    if not recipient.startswith("+"):
        raise HTTPException(status_code=400, detail="Telefon numarasını +90 formatında girin")

    if not configured_recipient or recipient != configured_recipient:
        raise HTTPException(
            status_code=400,
            detail="Bu demo için yalnızca kayıtlı SMS numarası kullanılabilir",
        )

    if not twilio_sms_alert_service.is_configured():
        raise HTTPException(status_code=503, detail="Twilio SMS ayarları eksik")

    sid = send_sms_alert(
        "[YanginIzle]\n"
        "SMS bildirimi aktif.\n"
        "Yuksek riskli yangin alarmlarinda bu numaraya SMS gonderilecek."
    )

    if not sid:
        raise HTTPException(status_code=502, detail="SMS gönderilemedi")

    return {
        "sent": True,
        "phone": recipient,
        "sid": sid,
        "message": "Test SMS gönderildi",
    }


def serialize_alert(alert: Alert):
    return {
        "alert_id": alert.id,
        "hotspot_id": alert.hotspot_id,
        "risk_level": alert.risk_level,
        "message": alert.message,
        "status": alert.status,
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
        "updated_at": alert.updated_at.isoformat() if getattr(alert, "updated_at", None) else None,
        "resolved_at": alert.resolved_at.isoformat() if getattr(alert, "resolved_at", None) else None,
    }


def latest_prediction_subquery(db: Session, hotspot_ids=None):
    query = db.query(
        Prediction.hotspot_id,
        func.max(Prediction.id).label("max_prediction_id"),
    )
    if hotspot_ids is not None:
        query = query.filter(Prediction.hotspot_id.in_(hotspot_ids))
    return query.group_by(Prediction.hotspot_id).subquery()


@router.get("")
def list_alerts(
    status: Optional[str] = Query(None),
    hotspot_id: Optional[int] = Query(None),
    risk_level: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Alert)

    if status:
        query = query.filter(Alert.status == status.strip().upper())

    if hotspot_id is not None:
        query = query.filter(Alert.hotspot_id == hotspot_id)

    if risk_level:
        query = query.filter(Alert.risk_level == risk_level.strip().upper())

    total = query.count()
    rows = (
        query
        .order_by(Alert.created_at.desc(), Alert.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "items": [serialize_alert(alert) for alert in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/active")
def list_active_alerts(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    ML modeli tarafından HIGH risk olarak işaretlenmiş,
    aktif uyarısı olan tüm hotspot'ları döner.
    Frontend alarm banner'ı için kullanılır.
    """
    active_alerts = (
        db.query(Alert)
        .filter(Alert.status == "ACTIVE")
        .order_by(Alert.created_at.desc(), Alert.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    if not active_alerts:
        return []

    hotspot_ids = [alert.hotspot_id for alert in active_alerts if alert.hotspot_id is not None]

    hotspots = (
        db.query(Hotspot)
        .filter(Hotspot.id.in_(hotspot_ids))
        .all()
        if hotspot_ids else []
    )
    hotspot_map = {hotspot.id: hotspot for hotspot in hotspots}

    latest_pred_sub = latest_prediction_subquery(db, hotspot_ids)
    predictions = (
        db.query(Prediction)
        .join(latest_pred_sub, Prediction.id == latest_pred_sub.c.max_prediction_id)
        .all()
        if hotspot_ids else []
    )
    prediction_map = {prediction.hotspot_id: prediction for prediction in predictions}

    result = []
    for alert in active_alerts:
        hotspot = hotspot_map.get(alert.hotspot_id)
        prediction = prediction_map.get(alert.hotspot_id)
        result.append({
            "alert_id": alert.id,
            "hotspot_id": alert.hotspot_id,
            "risk_level": alert.risk_level,
            "message": alert.message,
            "status": alert.status,
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
            "latitude": hotspot.latitude if hotspot else None,
            "longitude": hotspot.longitude if hotspot else None,
            "fire_probability": prediction.fire_probability if prediction else None,
        })

    return result


@router.patch("/{alert_id}/status")
def update_alert_status(
    alert_id: int,
    payload: AlertStatusUpdate,
    _: bool = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    try:
        alert = alert_service.update_alert_status(
            db=db,
            alert_id=alert_id,
            status=payload.status,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    manager.broadcast_threadsafe({
        "type": "ALERT_STATUS_UPDATED",
        "alert_id": alert.id,
        "hotspot_id": alert.hotspot_id,
        "status": alert.status,
    })

    return serialize_alert(alert)


@router.post("/{alert_id}/close")
def close_alert(
    alert_id: int,
    _: bool = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    alert = alert_service.close_alert(db=db, alert_id=alert_id)

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    manager.broadcast_threadsafe({
        "type": "ALERT_STATUS_UPDATED",
        "alert_id": alert.id,
        "hotspot_id": alert.hotspot_id,
        "status": alert.status,
    })

    return serialize_alert(alert)


@router.websocket("/ws")
async def alerts_ws(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=25)
                if message == "ping":
                    await websocket.send_json({
                        "type": "heartbeat",
                        "status": "ok",
                        "ts": utc_now().isoformat(),
                    })
            except asyncio.TimeoutError:
                await websocket.send_json({
                    "type": "heartbeat",
                    "status": "ok",
                    "ts": utc_now().isoformat(),
                })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
