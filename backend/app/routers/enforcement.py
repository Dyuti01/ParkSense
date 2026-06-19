"""
Enforcement Router — Priority ranking and patrol recommendations.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from typing import Optional

from app.database import get_db
from app.models.hotspot import Hotspot
from app.models.station_stats import StationStats

router = APIRouter()


@router.get("/priorities")
async def get_enforcement_priorities(
    n: int = Query(default=50, le=200),
    station: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Ranked enforcement targets by priority score."""
    query = (
        select(Hotspot)
        .where(Hotspot.time_slice == "all")
        .order_by(Hotspot.priority_score.desc())
        .limit(n)
    )
    if station:
        query = query.where(Hotspot.police_station == station)

    result = await db.execute(query)
    hotspots = result.scalars().all()

    priorities = []
    for rank, h in enumerate(hotspots, 1):
        # Determine recommended patrol time based on peak hour
        peak = h.peak_hour or 10
        patrol_start = max(0, peak - 1)
        patrol_end = min(23, peak + 2)

        priorities.append({
            "rank": rank,
            "hotspot_id": h.id,
            "location": h.location_label,
            "centroid_lat": h.centroid_lat,
            "centroid_lon": h.centroid_lon,
            "priority_score": round(h.priority_score, 2) if h.priority_score else 0,
            "congestion_impact_score": round(h.congestion_impact_score, 2) if h.congestion_impact_score else 0,
            "cis_tier": h.cis_tier,
            "violation_count": h.violation_count,
            "dominant_violation": h.dominant_violation,
            "dominant_vehicle": h.dominant_vehicle,
            "police_station": h.police_station,
            "enforcement_gap": round(h.priority_score / 100, 2) if h.priority_score else 0,
            "recurrence_rate": 0,
            "recommended_patrol": {
                "time_range": f"{patrol_start:02d}:00 - {patrol_end:02d}:00 IST",
                "peak_hour": peak,
                "peak_day": 0,
                "what_to_look_for": h.dominant_violation,
                "vehicle_focus": h.dominant_vehicle,
            },
        })

    return {"count": len(priorities), "priorities": priorities}


@router.get("/gaps")
async def get_enforcement_gaps(
    db: AsyncSession = Depends(get_db),
):
    """Zones with high violations but low enforcement (SCITA) coverage."""
    result = await db.execute(
        select(Hotspot)
        .where(
            Hotspot.time_slice == "all",
            Hotspot.priority_score > 40,  # Prioritize high score ones
        )
        .order_by(Hotspot.priority_score.desc())
        .limit(30)
    )
    hotspots = result.scalars().all()

    gaps = []
    for h in hotspots:
        gaps.append({
            "hotspot_id": h.id,
            "location": h.location_label,
            "centroid_lat": h.centroid_lat,
            "centroid_lon": h.centroid_lon,
            "violation_count": h.violation_count,
            "enforcement_gap": round(((h.priority_score or 0) / 100) * 100, 1),  # Simulated gap
            "congestion_impact_score": round(h.congestion_impact_score, 2) if h.congestion_impact_score else 0,
            "police_station": h.police_station,
        })

    return {"count": len(gaps), "gaps": gaps}


@router.get("/patrol-plan/{station_name}")
async def get_patrol_plan(
    station_name: str,
    db: AsyncSession = Depends(get_db),
):
    """Suggested patrol schedule for a station's hotspots."""
    result = await db.execute(
        select(Hotspot)
        .where(
            Hotspot.police_station == station_name,
            Hotspot.time_slice == "all",
        )
        .order_by(Hotspot.priority_score.desc())
        .limit(10)
    )
    hotspots = result.scalars().all()

    # Group by time windows
    time_windows = {
        "early_morning": {"range": "06:00 - 09:00", "hotspots": []},
        "morning": {"range": "09:00 - 12:00", "hotspots": []},
        "afternoon": {"range": "12:00 - 15:00", "hotspots": []},
        "evening": {"range": "15:00 - 18:00", "hotspots": []},
        "night": {"range": "18:00 - 22:00", "hotspots": []},
    }

    for h in hotspots:
        peak = h.peak_hour or 10
        if peak < 9:
            window = "early_morning"
        elif peak < 12:
            window = "morning"
        elif peak < 15:
            window = "afternoon"
        elif peak < 18:
            window = "evening"
        else:
            window = "night"

        time_windows[window]["hotspots"].append({
            "location": h.location_label,
            "centroid_lat": h.centroid_lat,
            "centroid_lon": h.centroid_lon,
            "priority_score": round(h.priority_score, 2) if h.priority_score else 0,
            "violation_count": h.violation_count,
            "dominant_violation": h.dominant_violation,
        })

    return {
        "station": station_name,
        "patrol_plan": time_windows,
        "total_hotspots": len(hotspots),
    }


@router.get("/resource-allocation")
async def get_resource_allocation(
    db: AsyncSession = Depends(get_db),
):
    """Recommended officer deployment per station zone based on violation volume and CIS."""
    result = await db.execute(
        select(StationStats)
        .order_by(StationStats.total_violations.desc())
    )
    stations = result.scalars().all()

    if not stations:
        return {"allocations": []}

    # Compute proportional allocation
    total_violations = sum(s.total_violations for s in stations)
    total_officers = 100  # hypothetical total enforcement units

    allocations = []
    for s in stations:
        share = s.total_violations / total_violations if total_violations > 0 else 0
        # Weight by CIS average to prioritize high-impact zones
        cis_weight = 1 + (s.cis_avg or 0) / 100
        weighted_share = share * cis_weight

        allocations.append({
            "station": s.police_station,
            "total_violations": s.total_violations,
            "cis_avg": round(s.cis_avg, 2) if s.cis_avg else 0,
            "violation_share_pct": round(share * 100, 1),
            "recommended_units": max(1, round(weighted_share * total_officers)),
            "critical_hotspots": s.critical_hotspots,
            "peak_hour": s.peak_hour,
        })

    # Re-normalize to total_officers
    total_allocated = sum(a["recommended_units"] for a in allocations)
    if total_allocated > 0:
        scale = total_officers / total_allocated
        for a in allocations:
            a["recommended_units"] = max(1, round(a["recommended_units"] * scale))

    allocations.sort(key=lambda x: x["recommended_units"], reverse=True)

    return {"total_units": total_officers, "allocations": allocations}
