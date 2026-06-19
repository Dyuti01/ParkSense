"""
Stations Router — Police station analytics and comparison.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from typing import Optional, List

from app.database import get_db
from app.models.station_stats import StationStats
from app.models.hotspot import Hotspot

router = APIRouter()


def station_to_dict(s) -> dict:
    return {
        "police_station": s.police_station,
        "total_violations": s.total_violations,
        "approved_count": s.approved_count,
        "rejected_count": s.rejected_count,
        "violation_breakdown": s.violation_breakdown,
        "vehicle_breakdown": s.vehicle_breakdown,
        "hourly_distribution": s.hourly_distribution,
        "daily_distribution": s.daily_distribution,
        "monthly_trend": s.monthly_trend,
        "top_locations": s.top_locations,
        "top_junctions": s.top_junctions,
        "cis_avg": round(s.cis_avg, 2) if s.cis_avg else 0,
        "cis_max": round(s.cis_max, 2) if s.cis_max else 0,
        "enforcement_rate": round(s.enforcement_rate, 1) if s.enforcement_rate else 0,
        "validation_rate": round(s.validation_rate, 1) if s.validation_rate else 0,
        "hotspot_count": s.hotspot_count,
        "critical_hotspots": s.critical_hotspots,
        "peak_hour": s.peak_hour,
        "peak_day": s.peak_day,
        "trend_direction": s.trend_direction,
        "trend_percentage": s.trend_percentage,
    }


@router.get("")
async def get_stations(
    sort_by: str = "total_violations",
    db: AsyncSession = Depends(get_db),
):
    """All stations with summary stats, sortable."""
    sort_col = getattr(StationStats, sort_by, StationStats.total_violations)
    result = await db.execute(
        select(StationStats).order_by(sort_col.desc())
    )
    stations = result.scalars().all()

    return {
        "count": len(stations),
        "stations": [station_to_dict(s) for s in stations],
    }


@router.get("/compare")
async def compare_stations(
    stations: str = Query(..., description="Comma-separated station names"),
    db: AsyncSession = Depends(get_db),
):
    """Side-by-side comparison of selected stations."""
    station_list = [s.strip() for s in stations.split(",")]

    result = await db.execute(
        select(StationStats).where(StationStats.police_station.in_(station_list))
    )
    station_data = result.scalars().all()

    return {
        "stations": [station_to_dict(s) for s in station_data],
    }


@router.get("/{station_name}")
async def get_station_detail(
    station_name: str,
    db: AsyncSession = Depends(get_db),
):
    """Detailed station view with hotspots."""
    # Station stats
    result = await db.execute(
        select(StationStats).where(StationStats.police_station == station_name)
    )
    station = result.scalar_one_or_none()

    if not station:
        return {"error": f"Station '{station_name}' not found"}

    # Station's hotspots
    hotspot_result = await db.execute(
        select(Hotspot)
        .where(Hotspot.police_station == station_name, Hotspot.time_slice == "all")
        .order_by(Hotspot.congestion_impact_score.desc())
        .limit(20)
    )
    hotspots = hotspot_result.scalars().all()

    return {
        "station": station_to_dict(station),
        "hotspots": [
            {
                "id": h.id,
                "centroid_lat": h.centroid_lat,
                "centroid_lon": h.centroid_lon,
                "location_label": h.location_label,
                "violation_count": h.violation_count,
                "congestion_impact_score": round(h.congestion_impact_score, 2),
                "cis_tier": h.cis_tier,
                "dominant_violation": h.dominant_violation,
                "peak_hour": h.peak_hour,
            }
            for h in hotspots
        ],
    }


@router.get("/{station_name}/hotspots")
async def get_station_hotspots(
    station_name: str,
    time_slice: str = "all",
    db: AsyncSession = Depends(get_db),
):
    """Hotspots within a station's jurisdiction."""
    result = await db.execute(
        select(Hotspot)
        .where(Hotspot.police_station == station_name, Hotspot.time_slice == time_slice)
        .order_by(Hotspot.congestion_impact_score.desc())
    )
    hotspots = result.scalars().all()

    from app.routers.hotspots import hotspot_to_dict
    return {
        "station": station_name,
        "count": len(hotspots),
        "hotspots": [hotspot_to_dict(h) for h in hotspots],
    }
