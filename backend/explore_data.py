import fastf1
import pandas as pd

fastf1.Cache.enable_cache("../data")

session = fastf1.get_session(2024, "Monaco", "R")
session.load()

laps = session.laps[['Driver', 'LapNumber', 'LapTime', 'Compound', 'TyreLife']].copy()

#Remove rows with missing lap times
laps = laps.dropna(subset=['LapTime'])

#Convert lap time to seconds
laps['LapTimeSeconds'] = laps['LapTime'].dt.total_seconds()

#REMOVE unrealistic lap times (safety cars, pit laps, etc.)
laps = laps[laps['LapTimeSeconds'] < 200]  # ~3:20 max

print(laps.head(10))
print("\nDrivers:", laps['Driver'].unique())
print("\nCompounds:", laps['Compound'].dropna().unique())