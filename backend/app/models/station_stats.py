"""
Station Stats Model — Aggregated analytics per police station.
"""

from sqlalchemy import (
    Column, String, Float, Integer, SmallInteger,
    DateTime, REAL
)
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base


class StationStats(Base):
    __tablename__ = "station_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    police_station = Column(String(100), unique=True, nullable=False)
    total_violations = Column(Integer, default=0)
    approved_count = Column(Integer, default=0)
    rejected_count = Column(Integer, default=0)

    violation_breakdown = Column(JSONB, default={})
    vehicle_breakdown = Column(JSONB, default={})
    hourly_distribution = Column(JSONB, default=[])
    daily_distribution = Column(JSONB, default=[])
    monthly_trend = Column(JSONB, default=[])

    top_locations = Column(JSONB, default=[])
    top_junctions = Column(JSONB, default=[])

    cis_avg = Column(REAL, default=0)
    cis_max = Column(REAL, default=0)
    enforcement_rate = Column(REAL, default=0)
    validation_rate = Column(REAL, default=0)

    hotspot_count = Column(Integer, default=0)
    critical_hotspots = Column(Integer, default=0)

    peak_hour = Column(SmallInteger)
    peak_day = Column(SmallInteger)

    trend_direction = Column(String(20), default="stable")
    trend_percentage = Column(REAL, default=0)

    computed_at = Column(DateTime(timezone=True))

    def __repr__(self):
        return f"<StationStats {self.police_station}: {self.total_violations} violations>"
