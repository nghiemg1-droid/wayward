from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import models  # noqa: F401  (đăng ký các model với SQLAlchemy)
from app.database import Base, engine
from app.routers import devices, pings, users

STATIC_DIR = Path(__file__).parent / "static"

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Wayward", description="Tracks device locations and alerts on theft risk")

app.include_router(users.router)
app.include_router(devices.router)
app.include_router(pings.router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}
