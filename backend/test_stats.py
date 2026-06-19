from app.database import sync_engine
from sqlalchemy import text

with sync_engine.connect() as conn:
    row = conn.execute(text("SELECT police_station, violation_breakdown, vehicle_breakdown FROM station_stats LIMIT 1")).fetchone()
    print(row.police_station if row else None)
    print(repr(row.violation_breakdown) if row else None)
    print(type(row.violation_breakdown) if row else None)
