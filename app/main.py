from fastapi import FastAPI

app = FastAPI(title="Wayward", description="Tracks device locations and alerts on theft risk")

@app.get("/")
def root():
    return {"status": "ok"}