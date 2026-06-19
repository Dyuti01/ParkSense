"""
ParkSense AI -- Station Analyzer

Computes per-station aggregate statistics and stores them
in the station_stats table for fast API serving.
"""

import pandas as pd
import numpy as np
from collections import Counter
from typing import List, Dict


def analyze_stations(df: pd.DataFrame, hotspots: List[Dict] = None) -> List[Dict]:
    """
    Compute per-station aggregate statistics.

    Args:
        df: Preprocessed violations DataFrame
        hotspots: List of hotspot dicts (for CIS aggregation)

    Returns:
        List of station stat dicts ready for DB insertion.
    """
    print(f"[STATIONS] Analyzing {df['police_station'].nunique()} police stations...")

    stations = []

    for station_name, sdf in df.groupby("police_station"):
        if pd.isna(station_name) or not station_name:
            continue

        # Violation type breakdown (now a single string column)
        violation_breakdown = {k: int(v) for k, v in sdf["violation_type"].value_counts().head(15).items()}

        # Vehicle type breakdown
        vehicle_breakdown = {k: int(v) for k, v in sdf["vehicle_type"].dropna().value_counts().head(15).items()}

        # Hourly distribution
        hourly = sdf["hour_ist"].dropna().value_counts().sort_index()

        # Peak hour and day
        peak_hour = int(hourly.idxmax()) if len(hourly) > 0 else None

        daily = sdf["day_of_week"].dropna().value_counts().sort_index()
        peak_day = int(daily.idxmax()) if len(daily) > 0 else None

        # CIS from hotspots
        station_hotspots = [
            h for h in (hotspots or [])
            if h.get("police_station") == station_name and h.get("time_slice") == "all"
        ]
        cis_avg = np.mean([h["congestion_impact_score"] for h in station_hotspots]) if station_hotspots else 0
        critical_count = sum(1 for h in station_hotspots if h.get("cis_tier") == "critical")

        # Enforcement rate (from payment_status or validation proxy)
        if "payment_status" in sdf.columns:
            approved = (sdf["payment_status"] == "approved").sum()
            enforcement_rate = (approved / len(sdf) * 100) if len(sdf) > 0 else 0
        else:
            enforcement_rate = 0

        # Trend: compare by month
        if "violation_date_ist" in sdf.columns:
            monthly = sdf.groupby(sdf["violation_date_ist"].dt.strftime('%Y-%m')).size()
            if len(monthly) >= 2:
                last = monthly.iloc[-1]
                prev = monthly.iloc[-2]
                if prev > 0:
                    trend_pct = round((last - prev) / prev * 100, 1)
                    trend_dir = "increasing" if trend_pct > 5 else ("decreasing" if trend_pct < -5 else "stable")
                else:
                    trend_pct = 0
                    trend_dir = "stable"
            else:
                trend_pct = 0
                trend_dir = "stable"
        else:
            trend_pct = 0
            trend_dir = "stable"

        stations.append({
            "police_station": station_name,
            "total_violations": len(sdf),
            "violation_breakdown": violation_breakdown,
            "vehicle_breakdown": vehicle_breakdown,
            "hotspot_count": len(station_hotspots),
            "critical_hotspots": critical_count,
            "cis_avg": round(float(cis_avg), 2),
            "enforcement_rate": round(float(enforcement_rate), 1),
            "peak_hour": peak_hour,
            "trend_direction": trend_dir,
            "trend_percentage": float(trend_pct),
        })

    # Sort by total violations
    stations.sort(key=lambda x: x["total_violations"], reverse=True)
    print(f"[DONE] Station analysis: {len(stations)} stations")
    return stations
