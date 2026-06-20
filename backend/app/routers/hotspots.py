"""
Hotspots Router — DBSCAN cluster data and spatial queries.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from typing import Optional

from app.database import get_db
from app.models.hotspot import Hotspot

router = APIRouter()


def hotspot_to_dict(h) -> dict:
    """Convert a Hotspot row to a serializable dict."""
    return {
        "id": h.id,
        "cluster_label": h.cluster_label,
        "centroid_lat": h.centroid_lat,
        "centroid_lon": h.centroid_lon,
        "radius_meters": h.radius_meters,
        "violation_count": h.violation_count,
        "unique_days": h.unique_days,
        "dominant_violation": h.dominant_violation,
        "dominant_vehicle": h.dominant_vehicle,
        "police_station": h.police_station,
        "location_label": h.location_label,
        "congestion_impact_score": round(h.congestion_impact_score, 2) if h.congestion_impact_score else 0,
        "cis_tier": h.cis_tier,
        "priority_score": round(h.priority_score, 2) if h.priority_score else 0,
        "peak_hour": h.peak_hour,
        "hourly_distribution": h.hourly_distribution,
        "daily_distribution": h.daily_distribution,
        "time_slice": h.time_slice,
    }


@router.get("")
async def get_hotspots(
    time_slice: str = "all",
    tier: Optional[str] = None,
    station: Optional[str] = None,
    sort_by: str = "congestion_impact_score",
    limit: int = Query(default=5000, le=10000),
    db: AsyncSession = Depends(get_db),
):
    """All hotspots with CIS scores, filterable by tier/station/time_slice."""
    query = select(Hotspot).where(Hotspot.time_slice == time_slice)

    if tier:
        query = query.where(Hotspot.cis_tier == tier)
    if station:
        query = query.where(Hotspot.police_station == station)

    # Sort
    sort_col = getattr(Hotspot, sort_by, Hotspot.congestion_impact_score)
    query = query.order_by(sort_col.desc()).limit(limit)

    result = await db.execute(query)
    hotspots = result.scalars().all()

    return {
        "count": len(hotspots),
        "time_slice": time_slice,
        "hotspots": [hotspot_to_dict(h) for h in hotspots],
    }


@router.get("/top")
async def get_top_hotspots(
    n: int = Query(default=20, le=100),
    time_slice: str = "all",
    db: AsyncSession = Depends(get_db),
):
    """Top-N hotspots by CIS score."""
    result = await db.execute(
        select(Hotspot)
        .where(Hotspot.time_slice == time_slice)
        .order_by(Hotspot.congestion_impact_score.desc())
        .limit(n)
    )
    hotspots = result.scalars().all()
    return {
        "count": len(hotspots),
        "hotspots": [hotspot_to_dict(h) for h in hotspots],
    }


@router.get("/summary")
async def get_hotspot_summary(
    time_slice: str = "all",
    db: AsyncSession = Depends(get_db),
):
    """Summary statistics about hotspots."""
    result = await db.execute(
        select(
            func.count(Hotspot.id),
            func.avg(Hotspot.congestion_impact_score),
            func.max(Hotspot.congestion_impact_score),
            func.sum(Hotspot.violation_count),
        ).where(Hotspot.time_slice == time_slice)
    )
    row = result.one()

    # Tier breakdown
    tier_result = await db.execute(
        select(Hotspot.cis_tier, func.count(Hotspot.id))
        .where(Hotspot.time_slice == time_slice)
        .group_by(Hotspot.cis_tier)
    )
    tier_breakdown = {row[0]: row[1] for row in tier_result.all()}

    return {
        "total_hotspots": row[0] or 0,
        "avg_cis": round(row[1], 2) if row[1] else 0,
        "max_cis": round(row[2], 2) if row[2] else 0,
        "total_violations_in_hotspots": row[3] or 0,
        "tier_breakdown": tier_breakdown,
    }


@router.get("/nearby")
async def get_nearby_hotspots(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    radius: int = Query(default=1000, description="Radius in meters"),
    time_slice: str = "all",
    db: AsyncSession = Depends(get_db),
):
    """Find hotspots near a given point using PostGIS spatial query."""
    # Standard Haversine formula in SQL since we aren't using PostGIS
    result = await db.execute(
        text("""
            SELECT *,
                   ( 6371000 * acos( cos( radians(:lat) ) * cos( radians( centroid_lat ) ) 
                   * cos( radians( centroid_lon ) - radians(:lon) ) + sin( radians(:lat) ) 
                   * sin( radians( centroid_lat ) ) ) ) AS distance_m
            FROM hotspots
            WHERE time_slice = :time_slice
              AND ( 6371000 * acos( cos( radians(:lat) ) * cos( radians( centroid_lat ) ) 
                   * cos( radians( centroid_lon ) - radians(:lon) ) + sin( radians(:lat) ) 
                   * sin( radians( centroid_lat ) ) ) ) < :radius
            ORDER BY distance_m
        """),
        {"lat": lat, "lon": lon, "radius": radius, "time_slice": time_slice},
    )
    rows = result.mappings().all()

    hotspots = []
    for row in rows:
        h = dict(row)
        h["distance_meters"] = round(h.get("distance_m", 0), 1)
        # Remove raw geography objects
        h.pop("centroid", None)
        hotspots.append(h)

    return {"count": len(hotspots), "hotspots": hotspots}


@router.get("/{hotspot_id}")
async def get_hotspot_detail(
    hotspot_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Detailed view of a specific hotspot."""
    result = await db.execute(select(Hotspot).where(Hotspot.id == hotspot_id))
    hotspot = result.scalar_one_or_none()

    if not hotspot:
        return {"error": "Hotspot not found"}

    return {"hotspot": hotspot_to_dict(hotspot)}
