"""
Violations Router — Violation data queries, heatmap data, and breakdowns.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text, case
from typing import Optional, List

from app.database import get_db
from app.models.violation import Violation
from app.models.heatmap import HeatmapGrid

router = APIRouter()


@router.get("")
async def get_violations(
    station: Optional[str] = None,
    violation_type: Optional[str] = None,
    vehicle_type: Optional[str] = None,
    hour_min: Optional[int] = None,
    hour_max: Optional[int] = None,
    day_of_week: Optional[int] = None,
    limit: int = Query(default=100, le=1000),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Paginated violation list with filters."""
    query = select(
        Violation.violation_number, Violation.latitude, Violation.longitude,
        Violation.location_text, Violation.vehicle_type,
        Violation.violation_types, Violation.severity_score,
        Violation.created_at_ist, Violation.hour_ist,
        Violation.police_station, Violation.junction_name,
        Violation.is_junction, Violation.validation_status,
    )

    if station:
        query = query.where(Violation.police_station == station)
    if violation_type:
        query = query.where(Violation.violation_type == violation_type)
    if vehicle_type:
        query = query.where(Violation.vehicle_type == vehicle_type)
    if hour_min is not None:
        query = query.where(Violation.hour_ist >= hour_min)
    if hour_max is not None:
        query = query.where(Violation.hour_ist <= hour_max)
    if day_of_week is not None:
        query = query.where(Violation.day_of_week == day_of_week)

    # Count total for pagination
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get page
    query = query.order_by(Violation.created_at_ist.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    violations = []
    for row in rows:
        violations.append({
            "id": row[0],
            "latitude": row[1],
            "longitude": row[2],
            "location": row[3],
            "vehicle_type": row[4],
            "violation_types": row[5],
            "severity_score": row[6],
            "created_at": row[7].isoformat() if row[7] else None,
            "hour_ist": row[8],
            "police_station": row[9],
            "junction_name": row[10],
            "is_junction": row[11],
            "validation_status": row[12],
        })

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "violations": violations,
    }


@router.get("/heatmap")
async def get_heatmap(
    time_slice: str = "all",
    db: AsyncSession = Depends(get_db),
):
    """Heatmap grid data for map overlay."""
    result = await db.execute(
        select(
            HeatmapGrid.cell_lat,
            HeatmapGrid.cell_lon,
            HeatmapGrid.violation_count,
            HeatmapGrid.severity_sum,
            HeatmapGrid.density,
        )
        .where(HeatmapGrid.time_slice == time_slice)
        .where(HeatmapGrid.violation_count > 0)
    )
    rows = result.all()

    points = []
    for row in rows:
        points.append({
            "lat": row[0],
            "lon": row[1],
            "count": row[2],
            "severity": row[3],
            "density": row[4],
        })

    return {"time_slice": time_slice, "points": points}


@router.get("/sample")
async def get_sample_points(
    n: int = Query(default=5000, le=20000),
    station: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Stratified sample of violation points for map markers."""
    query = select(
        Violation.latitude,
        Violation.longitude,
        Violation.severity_score,
    )
    if station:
        query = query.where(Violation.police_station == station)

    # Use TABLESAMPLE or random ordering for sampling
    query = query.order_by(func.random()).limit(n)
    result = await db.execute(query)
    rows = result.all()

    points = [[row[0], row[1], row[2] or 1.0] for row in rows]
    return {"count": len(points), "points": points}


@router.get("/types")
async def get_violation_types(
    station: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Violation type breakdown with counts."""
    if station:
        result = await db.execute(
            text("""
                SELECT violation_type AS vtype, COUNT(*) AS cnt
                FROM violations
                WHERE police_station = :station
                GROUP BY vtype
                ORDER BY cnt DESC
            """),
            {"station": station},
        )
    else:
        result = await db.execute(
            text("""
                SELECT violation_type AS vtype, COUNT(*) AS cnt
                FROM violations
                GROUP BY vtype
                ORDER BY cnt DESC
            """)
        )
    rows = result.all()
    return {
        "types": [{"type": row[0], "count": row[1]} for row in rows]
    }


@router.get("/vehicles")
async def get_vehicle_types(
    station: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Vehicle type breakdown with counts."""
    query = (
        select(Violation.vehicle_type, func.count(Violation.violation_number).label("cnt"))
        .group_by(Violation.vehicle_type)
        .order_by(text("cnt DESC"))
    )
    if station:
        query = query.where(Violation.police_station == station)

    result = await db.execute(query)
    rows = result.all()
    return {
        "vehicles": [{"type": row[0], "count": row[1]} for row in rows]
    }


@router.get("/filters")
async def get_filter_options(db: AsyncSession = Depends(get_db)):
    """Available filter values for the frontend."""
    # Stations
    stations_result = await db.execute(
        select(Violation.police_station)
        .distinct()
        .where(Violation.police_station.isnot(None))
        .order_by(Violation.police_station)
    )
    stations = [row[0] for row in stations_result.all()]

    # Vehicle types
    vehicles_result = await db.execute(
        select(Violation.vehicle_type)
        .distinct()
        .where(Violation.vehicle_type.isnot(None))
        .order_by(Violation.vehicle_type)
    )
    vehicles = [row[0] for row in vehicles_result.all()]

    # Violation types
    vtypes_result = await db.execute(
        text("SELECT DISTINCT violation_type AS vtype FROM violations ORDER BY vtype")
    )
    violation_types = [row[0] for row in vtypes_result.all()]

    return {
        "stations": stations,
        "vehicle_types": vehicles,
        "violation_types": violation_types,
    }
