import fastf1

fastf1.Cache.enable_cache("../data")

session = fastf1.get_session(2024, "Monaco", "R")
session.load()

laps = session.laps
print(laps.columns.tolist())