"""
Pipeline Run Model — Tracks data ingestion and ML pipeline execution history.
"""

from sqlalchemy import (
    Column, String, Integer, DateTime, Text
)
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_type = Column(String(50), nullable=False)  # ingestion / hotspot_compute / full
    status = Column(String(20), nullable=False, default="running")  # running / completed / failed
    records_processed = Column(Integer, default=0)
    records_inserted = Column(Integer, default=0)
    records_skipped = Column(Integer, default=0)
    hotspots_found = Column(Integer, default=0)
    error_message = Column(Text)
    details = Column(JSONB, default={})
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    def __repr__(self):
        return f"<PipelineRun {self.id} ({self.run_type}): {self.status}>"
