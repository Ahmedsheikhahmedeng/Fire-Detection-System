import csv
import os
from datetime import datetime, timedelta
from io import StringIO

import httpx
import psycopg2
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware


DB_PARAMS = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "fire_db"),
    "user": os.getenv("DB_USER", "deneme"),
    "password": os.getenv("DB_PASSWORD", ""),
}

NASA_FIRMS_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
FIRMS_SOURCES = [
    "VIIRS_SNPP_NRT",
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA21_NRT",
]
TURKEY_BOUNDS = "26,36,45,42"

app = FastAPI(title="Fire Detection Recovery API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def db_conn():
    return psycopg2.connect(**DB_PARAMS)


def verify_key(x_api_key: str | None):
    expected = os.getenv("API_KEY", "")
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def hours_ago(acq_date, acq_time):
    if not acq_date:
        return 9999.0
    t = str(acq_time or "0000").replace(".0", "").zfill(4)
    try:
        observed = datetime.combine(acq_date, datetime.min.time()).replace(
            hour=int(t[:2]), minute=int(t[2:])
        )
    except Exception:
        observed = datetime.combine(acq_date, datetime.min.time())
    return max(0.1, round((datetime.utcnow() - observed).total_seconds() / 3600, 1))


@app.get("/health")
def health():
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute("select 1")
    return {
        "status": "ok",
        "app": "Fire Detection API",
        "environment": "development",
        "version": "recovery",
        "database": "connected",
        "ml_model": "not_loaded",
        "scheduler": "manual",
        "security": "enabled",
    }


@app.get("/map/hotspots")
def map_hotspots():
    cutoff_date = (datetime.utcnow() - timedelta(days=2)).date()
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            select
                h.id, h.latitude, h.longitude, h.brightness, h.city, h.acq_date, h.acq_time,
                p.fire_probability, p.risk_level, p.decision_level, p.decision_name,
                a.id as alert_id, a.message as alert_message
            from hotspots h
            left join lateral (
                select fire_probability, risk_level, decision_level, decision_name
                from predictions
                where hotspot_id = h.id
                order by id desc
                limit 1
            ) p on true
            left join alerts a on a.hotspot_id = h.id and a.status = 'ACTIVE'
            where h.acq_date >= %s
            order by h.id desc
            limit 1000
            """,
            (cutoff_date,),
        )
        rows = cur.fetchall()

    result = []
    for row in rows:
        h = hours_ago(row[5], row[6])
        if h > 24:
            continue
        result.append(
            {
                "id": row[0],
                "latitude": float(row[1]),
                "longitude": float(row[2]),
                "brightness": float(row[3]) if row[3] is not None else None,
                "city": row[4] or "Çözülüyor...",
                "temperature": None,
                "humidity": None,
                "wind_speed": None,
                "spread_direction": "Bilinmiyor",
                "risk_level": row[8] or "UNKNOWN",
                "fire_probability": float(row[7]) if row[7] is not None else None,
                "risk_percent": round(float(row[7]) * 100, 1) if row[7] is not None else None,
                "decision_level": row[9],
                "decision_name": row[10],
                "hours_ago": h,
                "alert": row[11] is not None,
                "has_active_alert": row[11] is not None,
                "alert_id": row[11],
                "alert_message": row[12],
                "ml_source": "model" if row[7] is not None else "pending",
            }
        )
    return result


@app.get("/map/stats")
def map_stats():
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute("select count(*) from hotspots")
        total = cur.fetchone()[0]
        cur.execute(
            """
            select acq_date, count(*)
            from hotspots
            where acq_date >= %s
            group by acq_date
            order by acq_date
            """,
            ((datetime.utcnow() - timedelta(days=7)).date(),),
        )
        trend = [{"date": str(d), "count": c} for d, c in cur.fetchall()]
    return {
        "total_hotspots": total,
        "sampled_hotspots": total,
        "risk_distribution": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "WATCH": 0, "LOW": 0, "UNKNOWN": total},
        "city_stats": [],
        "trend": trend,
        "weather_summary": {"avg_temp": 0, "avg_humidity": 0, "avg_wind": 0, "min_temp": 0, "max_temp": 0},
        "alerts": {"active": 0, "total": 0},
    }


@app.get("/scheduler/status")
@app.get("/map/status")
def scheduler_status():
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute("select max(acq_date), max(acq_time) from hotspots")
        d, t = cur.fetchone()
    return {
        "status": "ok",
        "scheduler": "manual",
        "enabled": True,
        "api_scheduler_enabled": True,
        "worker_alive": False,
        "last_nasa_observation_at": datetime.combine(d, datetime.min.time()).replace(
            hour=int(str(t or "0000").zfill(4)[:2]),
            minute=int(str(t or "0000").zfill(4)[2:]),
        ).isoformat() if d else None,
        "last_error": None,
    }


@app.post("/nasa/fetch-hotspots")
def fetch_nasa_hotspots(country: str = "TUR", days: int = 3, x_api_key: str | None = Header(None)):
    verify_key(x_api_key)
    nasa_key = os.getenv("NASA_API_KEY", "")
    if not nasa_key:
        raise HTTPException(status_code=500, detail="NASA_API_KEY is not configured")
    rows = []
    source_errors = []
    for source in FIRMS_SOURCES:
        url = f"{NASA_FIRMS_URL}/{nasa_key}/{source}/{TURKEY_BOUNDS}/{days}"
        try:
            response = httpx.get(url, timeout=30.0)
            response.raise_for_status()
            source_rows = list(csv.DictReader(StringIO(response.text.strip())))
            for row in source_rows:
                row["source"] = source
            rows.extend(source_rows)
        except Exception as exc:
            source_errors.append({"source": source, "error": str(exc)})
    inserted = 0
    duplicates = 0
    with db_conn() as conn, conn.cursor() as cur:
        for row in rows:
            lat = float(row.get("latitude", 0))
            lon = float(row.get("longitude", 0))
            acq_date = datetime.strptime(row.get("acq_date"), "%Y-%m-%d").date()
            acq_time = str(row.get("acq_time", "")).replace(".0", "").zfill(4)
            sat = row.get("satellite", "")
            inst = row.get("instrument", "VIIRS")
            source = row.get("source", "VIIRS_SNPP_NRT")
            cur.execute(
                """
                select id from hotspots
                where latitude=%s and longitude=%s and acq_date=%s and acq_time=%s
                  and satellite=%s and instrument=%s and firms_source=%s
                limit 1
                """,
                (lat, lon, acq_date, acq_time, sat, inst, source),
            )
            if cur.fetchone():
                duplicates += 1
                continue
            cur.execute(
                """
                insert into hotspots
                (latitude, longitude, brightness, bright_ti5, frp, scan, track, confidence,
                 daynight, satellite, instrument, firms_source, type, version, acq_date, acq_time, city)
                values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    lat,
                    lon,
                    float(row.get("bright_ti4") or 0),
                    float(row.get("bright_ti5") or 0),
                    float(row.get("frp") or 0),
                    float(row.get("scan") or 1),
                    float(row.get("track") or 1),
                    row.get("confidence", ""),
                    row.get("daynight", "unknown"),
                    sat,
                    inst,
                    source,
                    float(row.get("type") or 0),
                    float(row.get("version") or 2),
                    acq_date,
                    acq_time,
                    None,
                ),
            )
            inserted += 1
        conn.commit()
    return {
        "received_count": len(rows),
        "inserted_count": inserted,
        "duplicate_count": duplicates,
        "source_error_count": len(source_errors),
        "source_errors": source_errors[:10],
    }
