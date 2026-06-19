"""
User Model — Authentication and role-based access control.
"""

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime
)
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    full_name = Column(String(100))
    role = Column(String(20), nullable=False, default="officer")  # admin / officer / analyst
    police_station = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True))
    last_login = Column(DateTime(timezone=True))

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"
