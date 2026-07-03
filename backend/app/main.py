import threading

from fastapi import FastAPI
from sqlalchemy import text

from app.api.routes import router as danger_zone_router
from app.api.forest_routes import router as forest_router
from app.core.config import settings
from app.db import Base, engine
from app.models import DangerZone, GeoEvent, TelanganaRegion, ForestChange
from app.services.background_worker import run_background_worker

app = FastAPI(title=settings.app_name)
app.include_router(danger_zone_router)
app.include_router(forest_router)


@app.on_event("startup")
def create_tables():
    """Create all database tables on startup."""
    Base.metadata.create_all(bind=engine)


@app.on_event("startup")
def start_background_worker():
    thread = threading.Thread(target=run_background_worker, daemon=True)
    thread.start()


@app.get("/health")
def health_check() -> dict:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "service": settings.app_name}


@app.get("/")
def root() -> dict:
    return {"message": "Eco-Guard backend is running"}