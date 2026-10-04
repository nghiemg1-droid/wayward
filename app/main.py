from fastapi import FastAPI

from app import models  # noqa: F401  (đăng ký các model với SQLAlchemy)
from app.database import Base, engine
from app.routers import devices, pings, users

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Wayward", description="Tracks device locations and alerts on theft risk")

app.include_router(users.router)
app.include_router(devices.router)
app.include_router(pings.router)


@app.get("/")
def root():
    return {"status": "ok"}
