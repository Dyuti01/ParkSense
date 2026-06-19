"""
Hotspot Model — DBSCAN-clustered parking violation hotspots.
"""

from sqlalchemy import (
    Column, String, Float, Integer, SmallInteger,
    DateTime, Text
)
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base


class Hotspot(Base):
    __tablename__ = "hotspots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cluster_label = Column(Integer, nullable=False)
    centroid_lat = Column(Float, nullable=False)
    centroid_lon = Column(Float, nullable=False)
    radius_meters = Column(Float, default=0)
    violation_count = Column(Integer, nullable=False, default=0)
    unique_days = Column(Integer, default=0)
    dominant_violation = Column(String(255))
    dominant_vehicle = Column(String(100))
    police_station = Column(String(200))
    location_label = Column(String(500))
    congestion_impact_score = Column(Float, nullable=False, default=0)
    cis_tier = Column(String(20), nullable=False, default="low")
    priority_score = Column(Float, default=0)
    peak_hour = Column(Integer)
    hourly_distribution = Column(JSONB, default=[])
    daily_distribution = Column(JSONB, default=[])
    time_slice = Column(String(20), default="all")
    computed_at = Column(DateTime(timezone=True))

    def __repr__(self):
        return f"<Hotspot {self.id} CIS={self.congestion_impact_score:.1f} ({self.cis_tier})>"
