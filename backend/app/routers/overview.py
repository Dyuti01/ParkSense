"""
Overview Router — Global KPIs and summary statistics.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text

from app.database import get_db
from app.models.violation import Violation
from app.models.hotspot import Hotspot
from app.models.station_stats import StationStats
from app.models.pipeline_run import PipelineRun

router = APIRouter()


@router.get("")
async def get_overview(db: AsyncSession = Depends(get_db)):
    """Global KPIs: total violations, hotspots, critical zones, enforcement coverage."""

    # Total violations
    total_result = await db.execute(select(func.count(Violation.violation_number)))
    total_violations = total_result.scalar() or 0

    # Date range
    date_range_result = await db.execute(
        select(func.min(Violation.violation_date_ist), func.max(Violation.violation_date_ist))
    )
    date_row = date_range_result.one_or_none()
    min_date = date_row[0].isoformat() if date_row and date_row[0] else None
    max_date = date_row[1].isoformat() if date_row and date_row[1] else None

    # Hotspot counts
    hotspot_total = await db.execute(
        select(func.count(Hotspot.id)).where(Hotspot.time_slice == "all")
    )
    total_hotspots = hotspot_total.scalar() or 0

    critical_result = await db.execute(
        select(func.count(Hotspot.id)).where(
            Hotspot.time_slice == "all",
            Hotspot.cis_tier == "critical",
        )
    )
    critical_zones = critical_result.scalar() or 0

    # Enforcement coverage (SCITA rate mock)
    enforcement_result = await db.execute(
        select(
            func.count(Violation.violation_number).filter(Violation.payment_status == 'PAID'),
            func.count(Violation.violation_number),
        )
    )
    enf_row = enforcement_result.one()
    enforcement_pct = (enf_row[0] / enf_row[1] * 100) if enf_row[1] > 0 else 0

    # Top station
    top_station_result = await db.execute(
        select(Violation.police_station, func.count(Violation.violation_number).label("cnt"))
        .group_by(Violation.police_station)
        .order_by(text("cnt DESC"))
        .limit(1)
    )
    top_station_row = top_station_result.one_or_none()
    top_station = {
        "name": top_station_row[0] if top_station_row else None,
        "count": top_station_row[1] if top_station_row else 0,
    }

    # Peak hour
    peak_hour_result = await db.execute(
        select(Violation.hour_ist, func.count(Violation.violation_number).label("cnt"))
        .group_by(Violation.hour_ist)
        .order_by(text("cnt DESC"))
        .limit(1)
    )
    peak_hour_row = peak_hour_result.one_or_none()
    peak_hour = peak_hour_row[0] if peak_hour_row else None

    # Unique stations count
    station_count_result = await db.execute(
        select(func.count(func.distinct(Violation.police_station)))
    )
    station_count = station_count_result.scalar() or 0

    # Unique devices count (Mocked as we removed device_id)
    device_count = 0

    # Junction vs non-junction (Mocked using place text)
    junction_result = await db.execute(
        select(func.count(Violation.violation_number)).where(Violation.place.ilike("%junction%"))
    )
    junction_count = junction_result.scalar() or 0
    junction_pct = (junction_count / total_violations * 100) if total_violations > 0 else 0

    # Last pipeline run
    last_run_result = await db.execute(
        select(PipelineRun)
        .where(PipelineRun.status == "completed")
        .order_by(PipelineRun.completed_at.desc())
        .limit(1)
    )
    last_run = last_run_result.scalar_one_or_none()

    return {
        "total_violations": total_violations,
        "total_hotspots": total_hotspots,
        "critical_zones": critical_zones,
        "enforcement_coverage_pct": round(enforcement_pct, 1),
        "top_station": top_station,
        "peak_hour_ist": peak_hour,
        "station_count": station_count,
        "device_count": device_count,
        "junction_violation_pct": round(junction_pct, 1),
        "date_range": {"start": min_date, "end": max_date},
        "last_pipeline_run": {
            "status": last_run.status if last_run else None,
            "completed_at": last_run.completed_at.isoformat() if last_run and last_run.completed_at else None,
            "hotspots_found": last_run.hotspots_found if last_run else 0,
        },
    }


@router.get("/trends")
async def get_trends(db: AsyncSession = Depends(get_db)):
    """Month-over-month violation trends."""
    result = await db.execute(
        text("""
            SELECT 
                DATE_TRUNC('month', violation_date_ist) AS month,
                COUNT(*) AS count
            FROM violations
            WHERE violation_date_ist IS NOT NULL
            GROUP BY 1
            ORDER BY 1
        """)
    )
    rows = result.all()

    trends = []
    for i, row in enumerate(rows):
        change_pct = None
        if i > 0 and rows[i - 1][1] > 0:
            change_pct = round((row[1] - rows[i - 1][1]) / rows[i - 1][1] * 100, 1)
        trends.append({
            "month": row[0].isoformat() if row[0] else None,
            "count": row[1],
            "change_pct": change_pct,
        })

    return {"monthly_trends": trends}
