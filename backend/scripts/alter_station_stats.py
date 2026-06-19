from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv(override=True)
engine = create_engine(os.getenv('DATABASE_URL_SYNC'))
with engine.connect() as conn:
    cols_jsonb = [
        "violation_breakdown", "vehicle_breakdown", "hourly_distribution", 
        "daily_distribution", "monthly_trend", "top_locations", "top_junctions"
    ]
    for c in cols_jsonb:
        conn.execute(text(f"ALTER TABLE station_stats ADD COLUMN IF NOT EXISTS {c} JSONB DEFAULT '{{}}'::jsonb"))
    
    cols_real = ["cis_avg", "cis_max", "enforcement_rate", "validation_rate", "trend_percentage"]
    for c in cols_real:
        conn.execute(text(f"ALTER TABLE station_stats ADD COLUMN IF NOT EXISTS {c} REAL DEFAULT 0"))
        
    cols_int = ["hotspot_count", "critical_hotspots", "peak_hour", "peak_day", "approved_count", "rejected_count"]
    for c in cols_int:
        conn.execute(text(f"ALTER TABLE station_stats ADD COLUMN IF NOT EXISTS {c} INTEGER DEFAULT 0"))
        
    conn.execute(text("ALTER TABLE station_stats ADD COLUMN IF NOT EXISTS trend_direction VARCHAR(20) DEFAULT 'stable'"))
    conn.execute(text("ALTER TABLE station_stats ADD COLUMN IF NOT EXISTS computed_at TIMESTAMP WITH TIME ZONE"))
    conn.commit()
print("Station stats all missing columns added")
