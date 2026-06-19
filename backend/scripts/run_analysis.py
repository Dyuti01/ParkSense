"""
Quick script to run ONLY the ML analysis pipeline (skip data insertion).
Assumes violations are already in the database.
"""
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(SCRIPT_DIR, "..")
sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(BACKEND_DIR, ".env"), override=True)

import pandas as pd
from sqlalchemy import text, create_engine
from app.config import settings
from app.ml.hotspot_detector import detect_hotspots
from app.ml.congestion_scorer import compute_cis
from app.ml.heatmap_generator import generate_heatmap_grid
from app.ml.station_analyzer import analyze_stations
from app.ml.pipeline_runner import PipelineRunner
from datetime import datetime, timezone


def main():
    print("\n" + "=" * 60)
    print(" PARKSENSE AI -- ML ANALYSIS (skip insertion)")
    print("=" * 60)

    engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)

    # Load violations from DB
    print("\n[LOAD] Reading violations from database...")
    df = pd.read_sql(
        "SELECT violation_number, violation_date, violation_date_ist, "
        "violation_type, vehicle_type, vehicle_number_hash, place, "
        "police_station, latitude, longitude, severity_score, "
        "hour_ist, day_of_week, month, payment_status "
        "FROM violations",
        engine,
    )
    print(f"   Loaded {len(df)} records")

    if len(df) == 0:
        print("[ERROR] No data in violations table!")
        return

    # Log pipeline start
    with engine.connect() as conn:
        conn.execute(text(
            "INSERT INTO pipeline_runs (run_type, status, started_at, records_processed) "
            "VALUES ('analysis', 'running', :now, :count)"
        ), {"now": datetime.now(timezone.utc), "count": len(df)})
        conn.commit()
        result = conn.execute(text("SELECT MAX(id) FROM pipeline_runs"))
        run_id = result.scalar()

    start = datetime.now(timezone.utc)

    try:
        # Step 1: Hotspot Detection
        print("\n-- Step 1: Hotspot Detection (DBSCAN) --")
        hotspots = detect_hotspots(df, eps_meters=200, min_samples=15)

        # Step 2: CIS Scoring
        print("\n-- Step 2: Congestion Impact Scoring --")
        for ts in set(h["time_slice"] for h in hotspots):
            slice_h = [h for h in hotspots if h["time_slice"] == ts]
            compute_cis(slice_h)

        # Step 3: Heatmap Grid
        print("\n-- Step 3: Heatmap Grid --")
        grid_cells = generate_heatmap_grid(df)

        # Step 4: Station Analytics
        print("\n-- Step 4: Station Analytics --")
        station_stats = analyze_stations(df, hotspots)

        # Step 5: Persist results
        print("\n-- Step 5: Persisting Results --")
        runner = PipelineRunner()
        from sqlalchemy.orm import Session
        with Session(engine) as session:
            runner._insert_hotspots(session, hotspots)
            runner._insert_heatmap(session, grid_cells)
            runner._insert_station_stats(session, station_stats)

        elapsed = (datetime.now(timezone.utc) - start).total_seconds()

        with engine.connect() as conn:
            conn.execute(text(
                "UPDATE pipeline_runs SET status = 'completed', "
                "hotspots_found = :h, completed_at = :now WHERE id = :id"
            ), {"h": len(hotspots), "now": datetime.now(timezone.utc), "id": run_id})
            conn.commit()

        print(f"\n{'=' * 60}")
        print(f"[DONE] ML Analysis complete in {elapsed:.1f}s")
        print(f"   Hotspots: {len(hotspots)}")
        print(f"   Grid cells: {len(grid_cells)}")
        print(f"   Stations: {len(station_stats)}")
        print(f"{'=' * 60}")

    except Exception as e:
        import traceback
        traceback.print_exc()
        with engine.connect() as conn:
            conn.execute(text(
                "UPDATE pipeline_runs SET status = 'failed', "
                "error_message = :err, completed_at = :now WHERE id = :id"
            ), {"err": str(e)[:500], "now": datetime.now(timezone.utc), "id": run_id})
            conn.commit()
        raise

    engine.dispose()


if __name__ == "__main__":
    main()
