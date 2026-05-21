import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.health import router as health_router
from app.api.nasa import router as nasa_router
from app.api.hotspots import router as hotspots_router
from app.api.weather import router as weather_router
from app.api.ml import router as ml_router
from app.api.alerts import router as alerts_router
from app.api.map import router as map_router
from app.api.scheduler import router as scheduler_router
from app.api.system import router as system_router
from app.core.config import settings
from app.services.ml_service import load_ml_model
from app.services.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger("fire_detection")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if getattr(settings, "APP_ENV", "development") == "test":
        logger.info("Test ortami algilandi; startup ML model yukleme atlandi.")
    elif settings.ENABLE_ML_PREDICTION:
        try:
            load_ml_model()
        except Exception:
            logger.exception("ML model yuklenemedi; API mevcut DB verileriyle calismaya devam edecek.")
    else:
        logger.info("ML model yukleme ayar geregi atlandi.")
    if settings.ENABLE_SCHEDULER:
        # Startup: arka plan scheduler'i baslat
        # NASA (6h) + Weather+ML (1h) dongusu otomatik calisir
        start_scheduler()
        logger.info("Uygulama baslatildi; scheduler aktif.")
    else:
        logger.info("Uygulama baslatildi; scheduler devre disi.")
    yield
    if settings.ENABLE_SCHEDULER:
        # Shutdown: scheduler'i temiz kapat
        stop_scheduler()
    logger.info("Uygulama kapatildi.")


app = FastAPI(
    title="Fire Detection API",
    description="Orman Yangını Tespit ve İzleme Sistemi — ML Tabanlı",
    version="2.0.0",
    lifespan=lifespan,
)

cors_origins = settings.allowed_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router kayıt
app.include_router(health_router)
app.include_router(nasa_router)
app.include_router(hotspots_router)
app.include_router(hotspots_router, prefix="/api")
app.include_router(weather_router)
app.include_router(ml_router, prefix="/api")
app.include_router(alerts_router)
app.include_router(map_router)
app.include_router(scheduler_router)
app.include_router(system_router)
app.include_router(system_router, prefix="/api")
