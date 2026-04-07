from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import threading
import fastf1
import pandas as pd
from datetime import datetime
import pickle
import numpy as np
import os
from supabase import create_client, Client

# ─── Supabase client ──────────────────────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ─── In-memory cache ──────────────────────────────────────────────────────────
session_cache = {}
laps_cache = {}
status_cache = {}
stints_cache = {}
positions_cache = {}
overview_cache = {}

def cache_key(year: int, gp: str) -> str:
    return f"{year}_{gp}"

# ─── FastF1 disk cache ────────────────────────────────────────────────────────
cache_dir = os.environ.get("FASTF1_CACHE", "/tmp/fastf1_cache")
os.makedirs(cache_dir, exist_ok=True)
fastf1.Cache.enable_cache(cache_dir)


# ─── Load all races from Supabase into memory ────────────────────────────────
def load_from_supabase():
    print("📦 Loading cached races from Supabase...")
    try:
        overview_rows = supabase.table("race_overview").select("*").execute().data
        if not overview_rows:
            print("  No cached races found in Supabase.")
            return

        for row in overview_rows:
            year = row["year"]
            gp = row["gp"]
            key = cache_key(year, gp)
            try:
                overview_cache[key] = {
                    "fastestLap": {
                        "driver": row["fastest_driver"],
                        "lapNumber": row["fastest_lap_number"],
                        "timeSeconds": row["fastest_lap_seconds"],
                    },
                    "podium": row["podium"],
                }

                laps_rows = supabase.table("race_laps").select("*").eq("year", year).eq("gp", gp).execute().data
                laps_cache[key] = [
                    {"Driver": r["driver"], "LapNumber": r["lap_number"], "LapTimeSeconds": r["lap_time_seconds"], "Compound": r["compound"], "TyreLife": r["tyre_life"]}
                    for r in laps_rows
                ]

                status_rows = supabase.table("race_status").select("*").eq("year", year).eq("gp", gp).execute().data
                status_cache[key] = {r["driver"]: {"status": r["status"], "finished": r["finished"]} for r in status_rows}

                stints_rows = supabase.table("race_stints").select("*").eq("year", year).eq("gp", gp).execute().data
                stints_cache[key] = [
                    {"Driver": r["driver"], "Stint": r["stint"], "Compound": r["compound"], "StartLap": r["start_lap"], "EndLap": r["end_lap"]}
                    for r in stints_rows
                ]

                pos_rows = supabase.table("race_positions").select("*").eq("year", year).eq("gp", gp).execute().data
                positions_cache[key] = [
                    {"Driver": r["driver"], "LapNumber": r["lap_number"], "Position": r["position"]}
                    for r in pos_rows
                ]

                print(f"  ✅ Loaded {year} {gp} from Supabase")

            except Exception as e:
                print(f"  ❌ Failed to load {year} {gp}: {e}")
                continue

    except Exception as e:
        print(f"  ❌ Supabase load failed: {e}")

    print(f"📦 Loaded {len(overview_cache)} races from Supabase into memory.")


# ─── Save a race to Supabase ─────────────────────────────────────────────────
def save_to_supabase(year: int, gp: str, key: str):
    try:
        overview = overview_cache[key]
        supabase.table("race_overview").upsert({
            "year": year, "gp": gp,
            "fastest_driver": overview["fastestLap"]["driver"],
            "fastest_lap_number": overview["fastestLap"]["lapNumber"],
            "fastest_lap_seconds": overview["fastestLap"]["timeSeconds"],
            "podium": overview["podium"],
        }).execute()

        laps_rows = [
            {"year": year, "gp": gp, "driver": l["Driver"], "lap_number": int(l["LapNumber"]),
             "lap_time_seconds": float(l["LapTimeSeconds"]), "compound": l.get("Compound"),
             "tyre_life": int(l["TyreLife"]) if l.get("TyreLife") else None}
            for l in laps_cache[key]
        ]
        for i in range(0, len(laps_rows), 500):
            supabase.table("race_laps").upsert(laps_rows[i:i+500]).execute()

        status_rows = [
            {"year": year, "gp": gp, "driver": driver, "status": v["status"], "finished": v["finished"]}
            for driver, v in status_cache[key].items()
        ]
        supabase.table("race_status").upsert(status_rows).execute()

        stints_rows = [
            {"year": year, "gp": gp, "driver": s["Driver"], "stint": int(s["Stint"]),
             "compound": s["Compound"], "start_lap": int(s["StartLap"]), "end_lap": int(s["EndLap"])}
            for s in stints_cache[key]
        ]
        supabase.table("race_stints").upsert(stints_rows).execute()

        pos_rows = [
            {"year": year, "gp": gp, "driver": p["Driver"], "lap_number": int(p["LapNumber"]), "position": int(p["Position"])}
            for p in positions_cache[key]
        ]
        for i in range(0, len(pos_rows), 500):
            supabase.table("race_positions").upsert(pos_rows[i:i+500]).execute()

        print(f"  💾 Saved {year} {gp} to Supabase")

    except Exception as e:
        print(f"  ❌ Failed to save {year} {gp} to Supabase: {e}")


# ─── Session loader ───────────────────────────────────────────────────────────
def load_session(year: int, gp: str):
    key = cache_key(year, gp)
    if key not in session_cache:
        session = fastf1.get_session(year, gp, "R")
        session.load()
        session_cache[key] = session
    return session_cache[key]


# ─── Build all cache dicts from a FastF1 session ─────────────────────────────
def build_cache_from_session(session, key: str):
    laps = session.laps[["Driver", "LapNumber", "LapTime", "Compound", "TyreLife"]].copy()
    laps = laps.dropna(subset=["LapTime"])
    laps["LapTimeSeconds"] = laps["LapTime"].dt.total_seconds()
    laps = laps[laps["LapTimeSeconds"] < 200]
    laps_cache[key] = laps.to_dict(orient="records")

    results = session.results[["Abbreviation", "Status", "ClassifiedPosition"]].copy()
    status_map = {}
    for _, row in results.iterrows():
        finished = str(row["ClassifiedPosition"]) != "R"
        status_map[row["Abbreviation"]] = {"status": str(row["Status"]), "finished": finished}
    status_cache[key] = status_map

    stint_laps = session.laps[["Driver", "LapNumber", "Compound", "Stint"]].copy()
    stint_laps = stint_laps.dropna(subset=["Compound", "Stint"])
    stints = (
        stint_laps.groupby(["Driver", "Stint", "Compound"])
        .agg(StartLap=("LapNumber", "min"), EndLap=("LapNumber", "max"))
        .reset_index()
    )
    stints_cache[key] = stints.to_dict(orient="records")

    pos_laps = session.laps[["Driver", "LapNumber", "Position"]].copy()
    pos_laps = pos_laps.dropna(subset=["Position"])
    pos_laps["Position"] = pos_laps["Position"].astype(int)
    positions_cache[key] = pos_laps.to_dict(orient="records")

    ov_laps = session.laps[["Driver", "LapNumber", "LapTime"]].copy()
    ov_laps = ov_laps.dropna(subset=["LapTime"])
    ov_laps["LapTimeSeconds"] = ov_laps["LapTime"].dt.total_seconds()
    ov_laps = ov_laps[ov_laps["LapTimeSeconds"] < 200]
    fastest_row = ov_laps.loc[ov_laps["LapTimeSeconds"].idxmin()]
    ov_results = session.results[["Abbreviation", "ClassifiedPosition"]].copy()
    ov_results = ov_results[ov_results["ClassifiedPosition"].apply(lambda x: str(x).isdigit())]
    ov_results["ClassifiedPosition"] = ov_results["ClassifiedPosition"].astype(int)
    podium = (
        ov_results.sort_values("ClassifiedPosition")
        .head(3)[["Abbreviation", "ClassifiedPosition"]]
        .to_dict(orient="records")
    )
    overview_cache[key] = {
        "fastestLap": {
            "driver": fastest_row["Driver"],
            "lapNumber": int(fastest_row["LapNumber"]),
            "timeSeconds": fastest_row["LapTimeSeconds"],
        },
        "podium": podium,
    }


# ─── Prewarm: only download races not already in Supabase ────────────────────
def prewarm_all_races():
    print("🔥 Starting background pre-warm of missing races...")
    now = datetime.now()

    for year in range(2022, 2027):
        try:
            schedule = fastf1.get_event_schedule(year, include_testing=False)
            schedule = schedule.copy()
            schedule["EventDate"] = pd.to_datetime(schedule["EventDate"], utc=True)
            cutoff = pd.Timestamp(now, tz="UTC")
            past = schedule[schedule["EventDate"] <= cutoff]

            for _, event in past.iterrows():
                gp = event["EventName"]
                key = cache_key(year, gp)

                if key in laps_cache:
                    continue

                try:
                    print(f"  Downloading {year} {gp} from FastF1...")
                    session = load_session(year, gp)
                    build_cache_from_session(session, key)
                    save_to_supabase(year, gp, key)

                    if key in session_cache:
                        del session_cache[key]

                    print(f"  ✅ {year} {gp} cached and saved")

                except Exception as e:
                    print(f"  ❌ Failed {year} {gp}: {e}")
                    continue

        except Exception as e:
            print(f"Schedule failed for {year}: {e}")
            continue

    print("✅ Pre-warm complete!")


# ─── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    load_from_supabase()
    thread = threading.Thread(target=prewarm_all_races, daemon=True)
    thread.start()
    yield


# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Available races ──────────────────────────────────────────────────────────
@app.get("/available-races")
def get_available_races():
    races = {}
    now = datetime.now()
    for year in range(2022, 2027):
        try:
            schedule = fastf1.get_event_schedule(year, include_testing=False)
            schedule = schedule.copy()
            schedule["EventDate"] = pd.to_datetime(schedule["EventDate"], utc=True)
            cutoff = pd.Timestamp(now, tz="UTC")
            past = schedule[schedule["EventDate"] <= cutoff]
            gp_names = past["EventName"].tolist()
            if gp_names:
                races[str(year)] = gp_names
        except Exception as e:
            print(f"Schedule load failed for {year}: {e}")
            continue
    return races


# ─── Combined race data endpoint ──────────────────────────────────────────────
@app.get("/race-data")
def get_race_data(year: int = 2024, gp: str = "Monaco"):
    key = cache_key(year, gp)

    if (key in laps_cache and key in status_cache and
            key in stints_cache and key in positions_cache and
            key in overview_cache):
        return {
            "laps": laps_cache[key],
            "driverStatus": status_cache[key],
            "stints": stints_cache[key],
            "positions": positions_cache[key],
            "overview": overview_cache[key],
        }

    session = load_session(year, gp)
    build_cache_from_session(session, key)
    save_to_supabase(year, gp, key)

    return {
        "laps": laps_cache.get(key, []),
        "driverStatus": status_cache.get(key, {}),
        "stints": stints_cache.get(key, []),
        "positions": positions_cache.get(key, []),
        "overview": overview_cache.get(key, {}),
    }


# ─── Individual endpoints ─────────────────────────────────────────────────────
@app.get("/race-laps")
def get_race_laps(year: int = 2024, gp: str = "Monaco"):
    key = cache_key(year, gp)
    if key in laps_cache:
        return laps_cache[key]
    session = load_session(year, gp)
    build_cache_from_session(session, key)
    save_to_supabase(year, gp, key)
    return laps_cache[key]


@app.get("/driver-status")
def get_driver_status(year: int = 2024, gp: str = "Monaco"):
    key = cache_key(year, gp)
    if key in status_cache:
        return status_cache[key]
    session = load_session(year, gp)
    build_cache_from_session(session, key)
    save_to_supabase(year, gp, key)
    return status_cache[key]


@app.get("/stint-data")
def get_stint_data(year: int = 2024, gp: str = "Monaco"):
    key = cache_key(year, gp)
    if key in stints_cache:
        return stints_cache[key]
    session = load_session(year, gp)
    build_cache_from_session(session, key)
    save_to_supabase(year, gp, key)
    return stints_cache[key]


@app.get("/position-data")
def get_position_data(year: int = 2024, gp: str = "Monaco"):
    key = cache_key(year, gp)
    if key in positions_cache:
        return positions_cache[key]
    session = load_session(year, gp)
    build_cache_from_session(session, key)
    save_to_supabase(year, gp, key)
    return positions_cache[key]


@app.get("/race-overview")
def get_race_overview(year: int = 2024, gp: str = "Monaco"):
    key = cache_key(year, gp)
    if key in overview_cache:
        return overview_cache[key]
    session = load_session(year, gp)
    build_cache_from_session(session, key)
    save_to_supabase(year, gp, key)
    return overview_cache[key]


# ─── Prewarm status ───────────────────────────────────────────────────────────
@app.get("/prewarm-status")
def prewarm_status():
    return {
        "cachedRaces": list(laps_cache.keys()),
        "totalCached": len(laps_cache),
    }


# ─── Debug ────────────────────────────────────────────────────────────────────
@app.get("/debug-status")
def debug_status(year: int = 2024, gp: str = "Monaco"):
    session = load_session(year, gp)
    results = session.results[["Abbreviation", "Status", "ClassifiedPosition"]].copy()
    output = []
    for _, row in results.iterrows():
        output.append({
            "driver": row["Abbreviation"],
            "status": str(row["Status"]),
            "classifiedPosition": str(row["ClassifiedPosition"]),
        })
    return output


# ─── ML model ─────────────────────────────────────────────────────────────────
model_data = None

def get_model():
    global model_data
    if model_data is None:
        try:
            with open("lap_time_model.pkl", "rb") as f:
                model_data = pickle.load(f)
        except FileNotFoundError:
            return None
    return model_data


@app.get("/predict-laptime")
def predict_laptime(
    compound: str = "MEDIUM",
    tyre_life: int = 10,
    lap_number: int = 30,
    total_laps: int = 78,
    baseline_seconds: float = 0,
):
    md = get_model()
    if md is None:
        return {"error": "Model not trained yet."}

    compound_map = md["compound_map"]
    compound_code = compound_map.get(compound.upper(), 1)
    lap_normalized = lap_number / max(total_laps, 1)
    features = np.array([[tyre_life, tyre_life ** 2, tyre_life * compound_code, compound_code, lap_normalized]])
    predicted_delta = float(md["model"].predict(features)[0])
    predicted_seconds = round(baseline_seconds + predicted_delta if baseline_seconds > 0 else predicted_delta, 3)

    return {
        "predictedSeconds": predicted_seconds,
        "predictedDelta": round(predicted_delta, 3),
        "compound": compound,
        "tyreLife": tyre_life,
        "lapNumber": lap_number,
        "modelMAE": round(md["mae_seconds"], 3),
        "hasBaseline": baseline_seconds > 0,
    }


@app.get("/model-info")
def model_info():
    md = get_model()
    if md is None:
        return {"trained": False}
    return {"trained": True, "trainedOnLaps": md["trained_on"], "maeSeconds": round(md["mae_seconds"], 3)}


@app.get("/simulate-strategy")
def simulate_strategy(
    year: int = 2024,
    gp: str = "Monaco",
    driver: str = "LEC",
    custom_pit_lap: int = 0,
    custom_compound_1: str = "MEDIUM",
    custom_compound_2: str = "HARD",
):
    md = get_model()
    if md is None:
        return {"error": "Model not trained yet."}

    session = load_session(year, gp)
    laps = session.laps[["Driver", "LapNumber", "LapTime", "Compound", "TyreLife"]].copy()
    laps = laps.dropna(subset=["LapTime", "Compound"])
    laps["LapTimeSeconds"] = laps["LapTime"].dt.total_seconds()
    laps = laps[(laps["LapTimeSeconds"] > 60) & (laps["LapTimeSeconds"] < 200)]

    driver_laps = laps[laps["Driver"] == driver].copy()
    if driver_laps.empty:
        return {"error": f"No lap data for {driver}"}

    total_laps = int(driver_laps["LapNumber"].max())
    baseline = float(driver_laps["LapTimeSeconds"].quantile(0.05))
    compound_map = md["compound_map"]

    def predict_lap(compound, tyre_life, lap_number):
        compound_code = compound_map.get(compound.upper(), 1)
        lap_normalized = lap_number / max(total_laps, 1)
        features = np.array([[tyre_life, tyre_life ** 2, tyre_life * compound_code, compound_code, lap_normalized]])
        return round(baseline + float(md["model"].predict(features)[0]), 3)

    actual_laps_detail = []
    for _, row in driver_laps.iterrows():
        predicted = predict_lap(row["Compound"], int(row["TyreLife"]), int(row["LapNumber"]))
        actual_laps_detail.append({
            "lap": int(row["LapNumber"]), "compound": row["Compound"],
            "tyreLife": int(row["TyreLife"]), "actualSeconds": round(row["LapTimeSeconds"], 3),
            "predictedSeconds": predicted,
        })

    actual_predicted_total = sum(l["predictedSeconds"] for l in actual_laps_detail)
    actual_real_total = sum(l["actualSeconds"] for l in actual_laps_detail)

    stint_data = session.laps[session.laps["Driver"] == driver][["LapNumber", "Compound", "Stint", "TyreLife"]].dropna()
    actual_stints = (
        stint_data.groupby(["Stint", "Compound"])
        .agg(StartLap=("LapNumber", "min"), EndLap=("LapNumber", "max"))
        .reset_index().sort_values("StartLap").to_dict(orient="records")
    )

    custom_laps_detail = []
    if custom_pit_lap > 0 and custom_pit_lap < total_laps:
        for lap in range(1, custom_pit_lap + 1):
            custom_laps_detail.append({"lap": lap, "compound": custom_compound_1, "predictedSeconds": predict_lap(custom_compound_1, lap, lap)})
        for lap in range(custom_pit_lap + 1, total_laps + 1):
            custom_laps_detail.append({"lap": lap, "compound": custom_compound_2, "predictedSeconds": predict_lap(custom_compound_2, lap - custom_pit_lap, lap)})

    custom_predicted_total = sum(l["predictedSeconds"] for l in custom_laps_detail)
    delta = round(custom_predicted_total - actual_predicted_total, 3) if custom_laps_detail else None

    return {
        "driver": driver, "totalLaps": total_laps, "baseline": round(baseline, 3),
        "actualStints": actual_stints,
        "actualPredictedTotal": round(actual_predicted_total, 3),
        "actualRealTotal": round(actual_real_total, 3),
        "customPredictedTotal": round(custom_predicted_total, 3) if custom_laps_detail else None,
        "delta": delta, "actualLaps": actual_laps_detail, "customLaps": custom_laps_detail,
    }