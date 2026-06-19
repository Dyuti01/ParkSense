"""
Ingestion Router — CSV upload and pipeline trigger endpoints.
"""

from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
import os
import tempfile

from app.database import get_db
from app.models.pipeline_run import PipelineRun

router = APIRouter()


@router.post("/csv")
async def upload_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a new CSV file for ingestion."""
    if not file.filename.endswith(".csv"):
        return {"error": "Only CSV files are accepted"}

    # Save uploaded file temporarily
    upload_dir = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Create pipeline run record
    run = PipelineRun(
        run_type="ingestion",
        status="queued",
        started_at=datetime.now(timezone.utc),
        details={"filename": file.filename, "file_path": file_path, "size_bytes": len(content)},
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)

    # Queue background pipeline execution
    background_tasks.add_task(run_ingestion_pipeline, file_path, run.id)

    return {
        "message": "CSV uploaded successfully. Pipeline queued.",
        "run_id": run.id,
        "filename": file.filename,
        "size_bytes": len(content),
    }


@router.post("/recompute")
async def recompute_pipeline(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger hotspot/score recomputation on existing data."""
    run = PipelineRun(
        run_type="recompute",
        status="queued",
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)

    background_tasks.add_task(run_recompute_pipeline, run.id)

    return {
        "message": "Recomputation pipeline queued.",
        "run_id": run.id,
    }


@router.get("/history")
async def get_ingestion_history(db: AsyncSession = Depends(get_db)):
    """Past pipeline runs with status."""
    result = await db.execute(
        select(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(20)
    )
    runs = result.scalars().all()

    return {
        "runs": [
            {
                "id": r.id,
                "run_type": r.run_type,
                "status": r.status,
                "records_processed": r.records_processed,
                "records_inserted": r.records_inserted,
                "hotspots_found": r.hotspots_found,
                "error_message": r.error_message,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "details": r.details,
            }
            for r in runs
        ]
    }


@router.delete("/history/{run_id}")
async def delete_pipeline_run(run_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a pipeline run from history."""
    result = await db.execute(select(PipelineRun).where(PipelineRun.id == run_id))
    run = result.scalar_one_or_none()
    
    if not run:
        return {"error": "Pipeline run not found"}
        
    await db.delete(run)
    await db.commit()
    return {"message": f"Run {run_id} deleted successfully"}


# ── Background Task Functions ───────────────────────────────
def run_ingestion_pipeline(file_path: str, run_id: int):
    """Background task: run the full ingestion + ML pipeline."""
    from app.ml.pipeline_runner import PipelineRunner
    runner = PipelineRunner()
    runner.run_ingestion(file_path, run_id)


def run_recompute_pipeline(run_id: int):
    """Background task: recompute hotspots and scores on existing data."""
    from app.ml.pipeline_runner import PipelineRunner
    runner = PipelineRunner()
    runner.run_recompute(run_id)
