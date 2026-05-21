from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.hotspots import router as hotspots_router
from app.api.map import router as map_router
from app.api.nasa import router as nasa_router
from app.api.scheduler import router as scheduler_router


app = FastAPI(
    title="Fire Detection API",
    description="Light startup entrypoint for map/NASA/scheduler recovery.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(hotspots_router)
app.include_router(map_router)
app.include_router(nasa_router)
app.include_router(scheduler_router)
