"""
Violation Model — Core data record for parking violations.
Simplified to work with standard PostgreSQL (no PostGIS).
"""

from sqlalchemy import (
    Column, String, Float, Integer, SmallInteger,
    DateTime, Text, Numeric, Boolean
)
from app.database import Base


class Violation(Base):
    __tablename__ = "violations"

    violation_number = Column(String(100), primary_key=True)
    violation_date = Column(DateTime(timezone=True), nullable=False)
    violation_date_ist = Column(DateTime, nullable=False)
    booked_date = Column(DateTime(timezone=True))
    violation_type = Column(String(255), nullable=False)
    vehicle_type = Column(String(100))
    vehicle_number_hash = Column(String(100))
    place = Column(String(500), nullable=False)
    police_station = Column(String(200))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    amount = Column(Numeric(10, 2))
    payment_status = Column(String(50))
    severity_score = Column(Float, default=0)
    hour_ist = Column(Integer)
    day_of_week = Column(Integer)
    month = Column(Integer)
    created_at = Column(DateTime(timezone=True))

    def __repr__(self):
        return f"<Violation {self.violation_number} at ({self.latitude}, {self.longitude})>"
