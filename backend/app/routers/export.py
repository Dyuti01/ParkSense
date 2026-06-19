"""
Export Router — CSV download and report generation.
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from typing import Optional
import io
import csv

from app.database import get_db
from app.models.violation import Violation
from app.models.hotspot import Hotspot
from app.models.station_stats import StationStats

router = APIRouter()


@router.get("/csv")
async def export_csv(
    station: Optional[str] = None,
    violation_type: Optional[str] = None,
    limit: int = Query(default=10000, le=50000),
    db: AsyncSession = Depends(get_db),
):
    """Download filtered violations as CSV."""
    query = select(
        Violation.violation_number, Violation.latitude, Violation.longitude,
        Violation.place, Violation.vehicle_type,
        Violation.violation_type, Violation.severity_score,
        Violation.violation_date_ist, Violation.hour_ist,
        Violation.day_of_week, Violation.police_station,
        Violation.amount, Violation.payment_status,
    )

    if station:
        query = query.where(Violation.police_station == station)
    if violation_type:
        query = query.where(Violation.violation_type == violation_type)

    query = query.order_by(Violation.violation_date_ist.desc()).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    # Generate CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "latitude", "longitude", "place", "vehicle_type",
        "violation_type", "severity_score", "datetime_ist", "hour_ist",
        "day_of_week", "police_station", "amount", "payment_status",
    ])
    for row in rows:
        writer.writerow([
            row[0], row[1], row[2], row[3], row[4],
            row[5], row[6],
            row[7].isoformat() if row[7] else "", row[8],
            row[9], row[10], row[11], row[12],
        ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=parksense_violations_export.csv"},
    )


@router.get("/report")
async def get_report_data(db: AsyncSession = Depends(get_db)):
    """Generate executive summary report data."""

    # Overall stats
    total_result = await db.execute(select(func.count(Violation.violation_number)))
    total = total_result.scalar() or 0

    # Top 5 stations
    top_stations = await db.execute(
        select(StationStats)
        .order_by(StationStats.total_violations.desc())
        .limit(5)
    )
    top_stations_data = top_stations.scalars().all()

    # Top 5 hotspots
    top_hotspots = await db.execute(
        select(Hotspot)
        .where(Hotspot.time_slice == "all")
        .order_by(Hotspot.congestion_impact_score.desc())
        .limit(5)
    )
    top_hotspots_data = top_hotspots.scalars().all()

    # Violation type breakdown
    types_result = await db.execute(
        text("""
            SELECT violation_type AS vtype, COUNT(*) AS cnt
            FROM violations GROUP BY vtype ORDER BY cnt DESC LIMIT 10
        """)
    )
    type_rows = types_result.all()

    # Auto-generated insights
    insights = []

    if top_stations_data:
        s = top_stations_data[0]
        pct = round(s.total_violations / total * 100, 1) if total > 0 else 0
        insights.append(
            f"{s.police_station} has the highest violation count with {s.total_violations:,} "
            f"violations — {pct}% of all city violations."
        )



    # Day insight
    day_result = await db.execute(
        select(Violation.day_of_week, func.count(Violation.violation_number).label("cnt"))
        .group_by(Violation.day_of_week)
        .order_by(text("cnt DESC"))
        .limit(1)
    )
    day_row = day_result.one_or_none()
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    if day_row:
        insights.append(
            f"{day_names[int(day_row[0])]} has the highest violation count at {day_row[1]:,}, "
            f"suggesting increased enforcement is needed on this day."
        )

    return {
        "total_violations": total,
        "top_stations": [
            {"name": s.police_station, "count": s.total_violations, "cis_avg": round(s.cis_avg, 2) if s.cis_avg else 0}
            for s in top_stations_data
        ],
        "top_hotspots": [
            {"location": h.location_label, "cis": round(h.congestion_impact_score, 2), "count": h.violation_count}
            for h in top_hotspots_data
        ],
        "violation_types": [{"type": r[0], "count": r[1]} for r in type_rows],
        "insights": insights,
    }
