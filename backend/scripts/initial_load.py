"""
ParkSense AI -- Initial Data Load Script

Loads the hackathon CSV into PostgreSQL and runs the full ML pipeline.

Usage:
    cd backend
    python -m scripts.initial_load
"""

import sys
import os

# Add parent directory to path for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(SCRIPT_DIR, "..")
sys.path.insert(0, BACKEND_DIR)

# Load .env BEFORE any app imports (critical for config to pick up values)
from dotenv import load_dotenv
env_path = os.path.join(BACKEND_DIR, ".env")
load_dotenv(dotenv_path=env_path, override=True)

# Now import app modules (which will read env vars via Settings)
from sqlalchemy import text, create_engine
from app.config import settings
from app.ml.pipeline_runner import PipelineRunner


def create_database():
    """Create the database schema if needed."""
    print("[DB] Setting up database...")
    print(f"[DB] Sync URL: {settings.DATABASE_URL_SYNC[:50]}...")

    # Read and execute schema
    schema_path = os.path.join(BACKEND_DIR, "database", "init.sql")
    if os.path.exists(schema_path):
        engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
        with open(schema_path, "r") as f:
            schema_sql = f.read()

        with engine.connect() as conn:
            statements = [s.strip() for s in schema_sql.split(";") if s.strip()]
            for stmt in statements:
                if stmt and not stmt.startswith("--"):
                    try:
                        conn.execute(text(stmt))
                    except Exception as e:
                        if "already exists" not in str(e).lower():
                            print(f"  [WARN] Schema: {e}")
            conn.commit()
        print("[OK] Database schema ready")
        engine.dispose()
    else:
        print(f"[WARN] Schema file not found at {schema_path}")


def main():
    print("")
    print("=" * 60)
    print(" PARKSENSE AI -- INITIAL DATA LOAD")
    print("=" * 60)

    # Setup database
    create_database()

    # Check if data already exists
    engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM violations"))
        count = result.scalar()
        if count > 0:
            print(f"\n[INFO] Database already has {count} violations. Clearing...")
            conn.execute(text("DELETE FROM violations"))
            conn.execute(text("DELETE FROM hotspots"))
            conn.execute(text("DELETE FROM heatmap_grid"))
            conn.execute(text("DELETE FROM station_stats"))
            conn.execute(text("DELETE FROM pipeline_runs"))
            conn.commit()
            print("   Cleared existing data.")
    engine.dispose()

    # Find CSV file
    csv_path = settings.CSV_PATH
    if not os.path.isabs(csv_path):
        csv_path = os.path.join(BACKEND_DIR, csv_path)
    csv_path = os.path.abspath(csv_path)

    if not os.path.exists(csv_path):
        print(f"\n[ERROR] CSV file not found: {csv_path}")
        print("   Update CSV_PATH in .env or provide the correct path.")
        return

    print(f"\n[FILE] CSV: {csv_path}")
    file_size_mb = os.path.getsize(csv_path) / (1024 * 1024)
    print(f"   Size: {file_size_mb:.1f} MB")

    # Run full pipeline
    runner = PipelineRunner()
    result = runner.run_full_pipeline(csv_path=csv_path)

    print("\n[DONE] Initial load complete!")
    print(f"   Records: {result['records_processed']}")
    print(f"   Hotspots: {result['hotspots_found']}")
    print(f"   Time: {result['elapsed_seconds']}s")
    print("\n   Start the API server with: uvicorn app.main:app --reload")


if __name__ == "__main__":
    main()
