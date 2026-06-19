"""
Heatmap Grid Model — Pre-computed grid cells for fast map rendering.
"""

from sqlalchemy import (
    Column, String, Float, Integer, DateTime, REAL
)
from app.database import Base


class HeatmapGrid(Base):
    __tablename__ = "heatmap_grid"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cell_lat = Column(Float, nullable=False)
    cell_lon = Column(Float, nullable=False)
    grid_row = Column(Integer)
    grid_col = Column(Integer)

    violation_count = Column(Integer, default=0)
    severity_sum = Column(REAL, default=0)
    density = Column(REAL, default=0)
    dominant_type = Column(String(100))

    time_slice = Column(String(20), default="all")
    computed_at = Column(DateTime(timezone=True))

    def __repr__(self):
        return f"<HeatmapGrid ({self.cell_lat:.4f}, {self.cell_lon:.4f}): {self.violation_count}>"
