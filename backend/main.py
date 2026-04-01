from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import fastf1
import pandas as pd

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

fastf1.Cache.enable_cache("../data")

cached_data = None

@app.get("/")
def home():
    return {"message": "F1 AI Platform running"}

@app.get("/race-laps")
def get_race_laps():
    global cached_data
    if cached_data is not None:
        return cached_data

    session = fastf1.get_session(2024, "Monaco", "R")
    session.load()

    laps = session.laps[['Driver', 'LapNumber', 'LapTime', 'Compound', 'TyreLife']].copy()
    laps = laps.dropna(subset=['LapTime'])
    laps['LapTimeSeconds'] = laps['LapTime'].dt.total_seconds()
    laps = laps[laps['LapTimeSeconds'] < 200]

    cached_data = laps.to_dict(orient="records")
    return cached_data