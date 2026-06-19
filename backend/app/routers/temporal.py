"""
Temporal Router — Time-based pattern analysis endpoints.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from typing import Optional

from app.database import get_db
from app.models.violation import Violation

router = APIRouter()


@router.get("/hourly")
async def get_hourly_distribution(
    station: Optional[str] = None,
    violation_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """24-hour violation distribution (IST)."""
    query = (
        select(Violation.hour_ist, func.count(Violation.violation_number).label("count"))
        .where(Violation.hour_ist.isnot(None))
        .group_by(Violation.hour_ist)
        .order_by(Violation.hour_ist)
    )
    if station:
        query = query.where(Violation.police_station == station)
    if violation_type:
        query = query.where(Violation.violation_type == violation_type)

    result = await db.execute(query)
    rows = result.all()

    # Build full 24-hour array (fill missing hours with 0)
    hourly = {int(r[0]): r[1] for r in rows}
    distribution = [{"hour": h, "count": hourly.get(h, 0)} for h in range(24)]

    peak_hour = max(distribution, key=lambda x: x["count"])

    return {
        "distribution": distribution,
        "peak_hour": peak_hour["hour"],
        "peak_count": peak_hour["count"],
    }


@router.get("/daily")
async def get_daily_distribution(
    station: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Day-of-week violation distribution."""
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    query = (
        select(Violation.day_of_week, func.count(Violation.violation_number).label("count"))
        .where(Violation.day_of_week.isnot(None))
        .group_by(Violation.day_of_week)
        .order_by(Violation.day_of_week)
    )
    if station:
        query = query.where(Violation.police_station == station)

    result = await db.execute(query)
    rows = result.all()

    daily = {int(r[0]): r[1] for r in rows}
    distribution = [
        {"day": d, "name": day_names[d], "count": daily.get(d, 0)}
        for d in range(7)
    ]

    peak_day = max(distribution, key=lambda x: x["count"])

    return {
        "distribution": distribution,
        "peak_day": peak_day["name"],
        "peak_count": peak_day["count"],
    }


@router.get("/monthly")
async def get_monthly_trend(
    station: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Monthly violation trend."""
    base_filter = "WHERE violation_date_ist IS NOT NULL"
    params = {}
    if station:
        base_filter += " AND police_station = :station"
        params["station"] = station

    result = await db.execute(
        text(f"""
            SELECT 
                DATE_TRUNC('month', violation_date_ist) AS month,
                COUNT(*) AS count
            FROM violations
            {base_filter}
            GROUP BY 1
            ORDER BY 1
        """),
        params,
    )
    rows = result.all()

    trend = []
    for i, row in enumerate(rows):
        change_pct = None
        if i > 0 and rows[i - 1][1] > 0:
            change_pct = round((row[1] - rows[i - 1][1]) / rows[i - 1][1] * 100, 1)
        trend.append({
            "month": row[0].strftime("%Y-%m") if row[0] else None,
            "count": row[1],
            "change_pct": change_pct,
        })

    return {"trend": trend}


@router.get("/heatmap-matrix")
async def get_hour_day_heatmap(
    station: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Hour × Day-of-week 2D heatmap matrix."""
    base_filter = "WHERE hour_ist IS NOT NULL AND day_of_week IS NOT NULL"
    params = {}
    if station:
        base_filter += " AND police_station = :station"
        params["station"] = station

    result = await db.execute(
        text(f"""
            SELECT hour_ist, day_of_week, COUNT(*) AS count
            FROM violations
            {base_filter}
            GROUP BY hour_ist, day_of_week
            ORDER BY day_of_week, hour_ist
        """),
        params,
    )
    rows = result.all()

    # Build 7×24 matrix
    matrix = [[0] * 24 for _ in range(7)]
    for row in rows:
        h, d, c = int(row[0]), int(row[1]), row[2]
        if 0 <= d < 7 and 0 <= h < 24:
            matrix[d][h] = c

    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    return {
        "matrix": matrix,
        "day_labels": day_names,
        "hour_labels": [f"{h:02d}:00" for h in range(24)],
    }


@router.get("/station/{station_name}")
async def get_station_temporal(
    station_name: str,
    db: AsyncSession = Depends(get_db),
):
    """Temporal profile for a specific station."""
    hourly = await get_hourly_distribution(station=station_name, db=db)
    daily = await get_daily_distribution(station=station_name, db=db)
    monthly = await get_monthly_trend(station=station_name, db=db)
    heatmap = await get_hour_day_heatmap(station=station_name, db=db)

    return {
        "station": station_name,
        "hourly": hourly,
        "daily": daily,
        "monthly": monthly,
        "heatmap_matrix": heatmap,
    }
