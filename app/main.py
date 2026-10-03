from fastapi import FastAPI

from app import models  
from app.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Wayward", description="Tracks device locations and alerts on theft risk")


@app.get("/")
def root():
    return {"status": "ok"}