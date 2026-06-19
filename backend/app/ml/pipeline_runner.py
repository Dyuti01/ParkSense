"""
ParkSense AI — Pipeline Runner

Orchestrates the complete ML pipeline:
1. Data preprocessing
2. Hotspot detection (DBSCAN)
3. Congestion impact scoring
4. Heatmap grid generation
5. Station analytics
6. Database persistence

Can be triggered by initial load, CSV upload, or manual recompute.
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import sync_engine
from app.ml.preprocessor import preprocess_dataframe
from app.ml.hotspot_detector import detect_hotspots
from app.ml.congestion_scorer import compute_cis
from app.ml.heatmap_generator import generate_heatmap_grid
from app.ml.station_analyzer import analyze_stations


class PipelineRunner:
    """Orchestrates the full ML pipeline."""

    def run_full_pipeline(self, csv_path: str = None, df: pd.DataFrame = None, run_id: int = None):
        """
        Run the complete pipeline: load → preprocess → cluster → score → persist.
        """
        start_time = datetime.now(timezone.utc)

        with Session(sync_engine) as session:
            try:
                # Log pipeline start
                if run_id:
                    session.execute(text(
                        "UPDATE pipeline_runs SET status = 'running', run_type = 'full', started_at = :started_at "
                        "WHERE id = :run_id"
                    ), {"started_at": start_time, "run_id": run_id})
                else:
                    session.execute(text(
                        "INSERT INTO pipeline_runs (run_type, status, started_at) "
                        "VALUES (:run_type, 'running', :started_at)"
                    ), {"run_type": "full", "started_at": start_time})
                    result = session.execute(text("SELECT MAX(id) FROM pipeline_runs"))
                    run_id = result.scalar()
                
                session.commit()

                # Step 1: Load & Preprocess
                print("\n" + "=" * 60)
                print("🚀 PARKSENSE AI — FULL PIPELINE")
                print("=" * 60)

                if df is None and csv_path:
                    print(f"\n📁 Loading CSV: {csv_path}")
                    df = pd.read_csv(csv_path, low_memory=False)
                    print(f"   Loaded {len(df)} records")

                if df is None or len(df) == 0:
                    raise ValueError("No data to process")

                print("\n── Step 1: Preprocessing ──────────────────")
                df = preprocess_dataframe(df)

                # Step 2: Insert violations into DB
                print("\n── Step 2: Database Insertion ─────────────")
                records_inserted = self._insert_violations(session, df)
                print(f"   ✅ {records_inserted} records inserted")

                # Step 3: Hotspot Detection
                print("\n── Step 3: Hotspot Detection (DBSCAN) ────")
                hotspots = detect_hotspots(df, eps_meters=150, min_samples=15)

                # Step 4: Congestion Impact Scoring
                print("\n── Step 4: Congestion Impact Scoring ─────")
                for time_slice in set(h["time_slice"] for h in hotspots):
                    slice_hotspots = [h for h in hotspots if h["time_slice"] == time_slice]
                    compute_cis(slice_hotspots)

                # Step 5: Persist hotspots
                print("\n── Step 5: Persisting Hotspots ────────────")
                self._insert_hotspots(session, hotspots)
                print(f"   ✅ {len(hotspots)} hotspots saved")

                # Step 6: Heatmap Grid
                print("\n── Step 6: Heatmap Grid Generation ───────")
                grid_cells = generate_heatmap_grid(df)
                self._insert_heatmap(session, grid_cells)
                print(f"   ✅ {len(grid_cells)} grid cells saved")

                # Step 7: Station Analytics
                print("\n── Step 7: Station Analytics ──────────────")
                station_stats = analyze_stations(df, hotspots)
                self._insert_station_stats(session, station_stats)
                print(f"   ✅ {len(station_stats)} station profiles saved")

                # Update pipeline run
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                session.execute(text(
                    "UPDATE pipeline_runs SET status = 'completed', "
                    "records_processed = :processed, records_inserted = :inserted, "
                    "hotspots_found = :hotspots, completed_at = :completed "
                    "WHERE id = :run_id"
                ), {
                    "processed": len(df),
                    "inserted": records_inserted,
                    "hotspots": len(hotspots),
                    "completed": datetime.now(timezone.utc),
                    "run_id": run_id,
                })
                session.commit()

                print(f"\n{'=' * 60}")
                print(f"✅ PIPELINE COMPLETE in {elapsed:.1f}s")
                print(f"   Records: {len(df)} | Hotspots: {len(hotspots)} | Stations: {len(station_stats)}")
                print(f"{'=' * 60}\n")

                return {
                    "status": "completed",
                    "records_processed": len(df),
                    "hotspots_found": len(hotspots),
                    "elapsed_seconds": round(elapsed, 1),
                }

            except Exception as e:
                print(f"\n❌ Pipeline failed: {e}")
                import traceback
                traceback.print_exc()
                if run_id:
                    session.execute(text(
                        "UPDATE pipeline_runs SET status = 'failed', "
                        "error_message = :error, completed_at = :completed "
                        "WHERE id = :run_id"
                    ), {
                        "error": str(e)[:500],
                        "completed": datetime.now(timezone.utc),
                        "run_id": run_id,
                    })
                    session.commit()
                raise

    def _insert_violations(self, session: Session, df: pd.DataFrame) -> int:
        """Batch insert violations into the database using bulk dictionaries."""
        inserted = 0
        batch_size = 5000  # Increased batch size since dict generation is fast

        # 0. Deduplicate: Prevent inserting records that already exist
        existing_res = session.execute(text("SELECT violation_number FROM violations"))
        existing_vnos = set(row[0] for row in existing_res)
        
        clean_df = df.copy()
        clean_df["violation_number"] = clean_df["violation_number"].fillna("").astype(str)
        
        # Drop intra-CSV duplicates
        clean_df = clean_df.drop_duplicates(subset=["violation_number"])
        
        # Drop duplicates already in DB
        clean_df = clean_df[~clean_df["violation_number"].isin(existing_vnos)]
        
        total = len(clean_df)
        if total == 0:
            print("   ⚠️  All records in this CSV are already in the database. Skipping insertion.")
            return 0
        
        # Strings
        clean_df["violation_number"] = clean_df["violation_number"].fillna("").astype(str)
        clean_df["violation_type"] = clean_df["violation_type"].fillna("UNKNOWN").astype(str)
        clean_df["vehicle_number_hash"] = clean_df["vehicle_number_hash"].fillna("").astype(str)
        
        if "place" in clean_df.columns:
            clean_df["place"] = clean_df["place"].fillna("Unknown").astype(str).str.slice(0, 500)
            
        # Optional strings (None if missing)
        for col in ["vehicle_type", "police_station"]:
            if col in clean_df.columns:
                clean_df[col] = clean_df[col].where(pd.notna(clean_df[col]), None)

        # Numerics (floats)
        clean_df["latitude"] = pd.to_numeric(clean_df["latitude"], errors='coerce').fillna(0.0)
        clean_df["longitude"] = pd.to_numeric(clean_df["longitude"], errors='coerce').fillna(0.0)
        clean_df["severity_score"] = pd.to_numeric(clean_df.get("severity_score", 0), errors='coerce').fillna(0.0)
        
        # Integers (must handle Pandas automatic float-casting when NaN is present)
        for col in ["hour_ist", "day_of_week", "month"]:
            if col in clean_df.columns:
                clean_df[col] = pd.to_numeric(clean_df[col], errors='coerce')
                # Explicitly cast to Python int to strip the .0 decimal, while keeping NaNs as None
                clean_df[col] = clean_df[col].apply(lambda x: int(x) if pd.notna(x) else None)

        # Datetimes (SQLAlchemy cannot adapt pd.Timestamp)
        for col in ["violation_date", "violation_date_ist", "booked_date"]:
            if col in clean_df.columns:
                clean_df[col] = pd.to_datetime(clean_df[col], errors='coerce')
                clean_df[col] = clean_df[col].apply(lambda x: x.to_pydatetime() if pd.notna(x) else None)

        # 2. Convert directly to native dictionary list
        records = clean_df.to_dict(orient='records')

        # 3. Bulk Execute via SQLAlchemy
        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            batch = records[start:end]

            try:
                session.execute(text("""
                    INSERT INTO violations (
                        violation_number, violation_date, violation_date_ist, booked_date,
                        violation_type, vehicle_type, vehicle_number_hash,
                        place, police_station, latitude, longitude,
                        severity_score, hour_ist, day_of_week, month
                    ) VALUES (
                        :violation_number, :violation_date, :violation_date_ist, :booked_date,
                        :violation_type, :vehicle_type, :vehicle_number_hash,
                        :place, :police_station, :latitude, :longitude,
                        :severity_score, :hour_ist, :day_of_week, :month
                    )
                    ON CONFLICT (violation_number) DO NOTHING
                """), batch)
                inserted += len(batch)
                
                if end % 20000 == 0 or end == total:
                    session.commit()
                    print(f"   Inserted {end}/{total} records...")
                    
            except Exception as e:
                session.rollback()
                print(f"   [WARN] Batch {start}-{end} failed: {e}")
                continue

        return inserted

    def _insert_hotspots(self, session: Session, hotspots: list):
        """Clear old hotspots and insert new ones."""
        session.execute(text("DELETE FROM hotspots"))

        for h in hotspots:
            session.execute(text("""
                INSERT INTO hotspots (
                    cluster_label, centroid_lat, centroid_lon, radius_meters,
                    violation_count, unique_days,
                    dominant_violation, dominant_vehicle, police_station,
                    location_label, congestion_impact_score, cis_tier,
                    priority_score, peak_hour,
                    hourly_distribution, daily_distribution,
                    time_slice, computed_at
                ) VALUES (
                    :cluster_label, :centroid_lat, :centroid_lon, :radius_meters,
                    :violation_count, :unique_days,
                    :dominant_violation, :dominant_vehicle, :police_station,
                    :location_label, :congestion_impact_score, :cis_tier,
                    :priority_score, :peak_hour,
                    CAST(:hourly_distribution AS jsonb), CAST(:daily_distribution AS jsonb),
                    :time_slice, NOW()
                )
            """), {
                "cluster_label": h.get("cluster_label", 0),
                "centroid_lat": h["centroid_lat"],
                "centroid_lon": h["centroid_lon"],
                "radius_meters": h.get("radius_meters", 0),
                "violation_count": h["violation_count"],
                "unique_days": h.get("unique_days", 0),
                "dominant_violation": h.get("dominant_violation"),
                "dominant_vehicle": h.get("dominant_vehicle"),
                "police_station": h.get("police_station"),
                "location_label": h.get("location_label", f"Cluster {h.get('cluster_label', '?')}"),
                "congestion_impact_score": round(h.get("congestion_impact_score", 0), 2),
                "cis_tier": h.get("cis_tier", "low"),
                "priority_score": round(h.get("priority_score", 0), 2),
                "peak_hour": h.get("peak_hour"),
                "hourly_distribution": json.dumps(h.get("hourly_distribution", [])),
                "daily_distribution": json.dumps(h.get("daily_distribution", [])),
                "time_slice": h.get("time_slice", "all"),
            })

        session.commit()

    def _insert_heatmap(self, session: Session, grid_cells: list):
        """Clear old heatmap and insert new grid cells."""
        session.execute(text("DELETE FROM heatmap_grid"))

        for cell in grid_cells:
            session.execute(text("""
                INSERT INTO heatmap_grid (cell_lat, cell_lon, density, time_slice, computed_at)
                VALUES (:cell_lat, :cell_lon, :density, :time_slice, NOW())
            """), {
                "cell_lat": cell.get("cell_lat", cell.get("grid_lat")),
                "cell_lon": cell.get("cell_lon", cell.get("grid_lon")),
                "density": cell.get("density", cell.get("weight", 0)),
                "time_slice": cell.get("time_slice", "all"),
            })

        session.commit()

    def _insert_station_stats(self, session: Session, station_stats: list):
        """Clear old stats and insert new ones."""
        session.execute(text("DELETE FROM station_stats"))

        for s in station_stats:
            session.execute(text("""
                INSERT INTO station_stats (
                    police_station, total_violations, hotspot_count, critical_hotspots,
                    cis_avg, enforcement_rate, peak_hour,
                    trend_direction, trend_percentage,
                    violation_breakdown, vehicle_breakdown, computed_at
                ) VALUES (
                    :police_station, :total_violations, :hotspot_count, :critical_hotspots,
                    :cis_avg, :enforcement_rate, :peak_hour,
                    :trend_direction, :trend_percentage,
                    CAST(:violation_breakdown AS jsonb), CAST(:vehicle_breakdown AS jsonb), NOW()
                )
            """), {
                "police_station": s["police_station"],
                "total_violations": s["total_violations"],
                "hotspot_count": s.get("hotspot_count", 0),
                "critical_hotspots": s.get("critical_hotspots", 0),
                "cis_avg": round(s.get("cis_avg", 0), 2),
                "enforcement_rate": round(s.get("enforcement_rate", 0), 2),
                "peak_hour": s.get("peak_hour"),
                "trend_direction": s.get("trend_direction", "stable"),
                "trend_percentage": round(s.get("trend_percentage", 0), 2),
                "violation_breakdown": json.dumps(s.get("violation_breakdown", {})),
                "vehicle_breakdown": json.dumps(s.get("vehicle_breakdown", {})),
            })

        session.commit()

    def run_ingestion(self, file_path: str, run_id: int):
        """Wrapper for CSV ingestion (called from background task)."""
        self.run_full_pipeline(csv_path=file_path, run_id=run_id)

    def run_recompute(self, run_id: int):
        """Wrapper for recomputation."""
        with Session(sync_engine) as session:
            result = session.execute(text(
                "SELECT violation_number, violation_date, violation_date_ist, "
                "violation_type, vehicle_type, vehicle_number_hash, place, "
                "police_station, latitude, longitude, severity_score, "
                "hour_ist, day_of_week, month FROM violations"
            ))
            rows = result.all()

        if not rows:
            return

        df = pd.DataFrame(rows, columns=[
            "violation_number", "violation_date", "violation_date_ist",
            "violation_type", "vehicle_type", "vehicle_number_hash", "place",
            "police_station", "latitude", "longitude", "severity_score",
            "hour_ist", "day_of_week", "month",
        ])

        # Run analysis pipeline (skip preprocessing since data is already clean)
        print("\n── Recomputing hotspots from existing data ──")
        hotspots = detect_hotspots(df, eps_meters=150, min_samples=15)
        for time_slice in set(h["time_slice"] for h in hotspots):
            slice_hotspots = [h for h in hotspots if h["time_slice"] == time_slice]
            compute_cis(slice_hotspots)

        grid_cells = generate_heatmap_grid(df)
        station_stats = analyze_stations(df, hotspots)

        with Session(sync_engine) as session:
            self._insert_hotspots(session, hotspots)
            self._insert_heatmap(session, grid_cells)
            self._insert_station_stats(session, station_stats)

            session.execute(text(
                "UPDATE pipeline_runs SET status = 'completed', "
                "records_processed = :processed, "
                "hotspots_found = :hotspots, completed_at = NOW() "
                "WHERE id = :run_id"
            ), {"processed": len(df), "hotspots": len(hotspots), "run_id": run_id})
            session.commit()
