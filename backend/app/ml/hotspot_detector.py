"""
ParkSense AI -- Hotspot Detection Engine

Uses grid-based spatial aggregation + DBSCAN clustering to identify
illegal parking hotspots from violation coordinates.

Strategy for 300K+ points:
1. Bin coordinates into ~50m grid cells
2. Aggregate violation stats per cell
3. Run DBSCAN on cell centroids (weighted)
4. Merge cell-level stats into cluster-level hotspot profiles
"""

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from collections import Counter
from typing import List, Dict
from math import radians, cos, sin, asin, sqrt


# Time slices for analysis
TIME_SLICES = {
    "all": (0, 24),
    "morning": (6, 12),     # 6 AM - 12 PM IST
    "afternoon": (12, 18),  # 12 PM - 6 PM IST
    "evening": (18, 24),    # 6 PM - 12 AM IST
    "night": (0, 6),        # 12 AM - 6 AM IST
}

# Grid cell size in degrees (~50m at Bangalore's latitude)
GRID_SIZE_DEG = 0.0005  # ~55m at 13 deg N


def haversine(lat1, lon1, lat2, lon2):
    """Distance in meters between two coordinates."""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371000 * 2 * asin(sqrt(a))


def grid_aggregate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate violations into spatial grid cells.
    Reduces 300K points to ~5-15K grid cells for DBSCAN.
    """
    df = df.copy()
    df["grid_lat"] = (df["latitude"] / GRID_SIZE_DEG).round() * GRID_SIZE_DEG
    df["grid_lon"] = (df["longitude"] / GRID_SIZE_DEG).round() * GRID_SIZE_DEG

    agg = df.groupby(["grid_lat", "grid_lon"]).agg(
        latitude=("latitude", "mean"),
        longitude=("longitude", "mean"),
        count=("latitude", "size"),
        severity_mean=("severity_score", "mean"),
        dominant_violation=("violation_type", lambda x: x.mode().iloc[0] if len(x) > 0 else "UNKNOWN"),
        dominant_vehicle=("vehicle_type", lambda x: x.dropna().mode().iloc[0] if len(x.dropna()) > 0 else None),
        police_station=("police_station", lambda x: x.dropna().mode().iloc[0] if len(x.dropna()) > 0 else None),
        place=("place", "first"),
        peak_hour=("hour_ist", lambda x: int(x.mode().iloc[0]) if len(x.dropna()) > 0 else 0),
    ).reset_index()

    return agg


def run_dbscan_on_grid(
    grid_df: pd.DataFrame,
    eps_meters: float = 200.0,
    min_cells: int = 3,
) -> np.ndarray:
    """
    Run DBSCAN on grid cell centroids (much fewer points than raw).
    """
    coords_rad = np.radians(
        np.column_stack([grid_df["latitude"].values, grid_df["longitude"].values])
    )
    eps_rad = eps_meters / 6_371_000

    db = DBSCAN(
        eps=eps_rad,
        min_samples=min_cells,
        metric="haversine",
        algorithm="ball_tree",
        n_jobs=1,  # Single thread to avoid memory issues
    )
    labels = db.fit_predict(coords_rad)
    return labels


def compute_cluster_stats(
    grid_df: pd.DataFrame,
    labels: np.ndarray,
    raw_df: pd.DataFrame,
    time_slice: str = "all",
) -> List[Dict]:
    """
    Compute statistics for each DBSCAN cluster from grid cells.
    """
    grid_df = grid_df.copy()
    grid_df["cluster_label"] = labels

    clustered = grid_df[grid_df["cluster_label"] != -1]
    if len(clustered) == 0:
        return []

    clusters = []
    for label in sorted(clustered["cluster_label"].unique()):
        cells = clustered[clustered["cluster_label"] == label]

        # Weighted centroid (by violation count)
        total_count = cells["count"].sum()
        centroid_lat = (cells["latitude"] * cells["count"]).sum() / total_count
        centroid_lon = (cells["longitude"] * cells["count"]).sum() / total_count

        # Radius
        if len(cells) > 1:
            distances = cells.apply(
                lambda row: haversine(centroid_lat, centroid_lon, row["latitude"], row["longitude"]),
                axis=1,
            )
            radius = distances.max()
        else:
            radius = 50.0  # Single cell

        # Dominant types from the densest cell
        max_idx = cells["count"].idxmax()
        dominant_violation = cells.loc[max_idx, "dominant_violation"]
        dominant_vehicle = cells.loc[max_idx, "dominant_vehicle"]
        police_station = cells.loc[max_idx, "police_station"]

        # Peak hour (weighted by count)
        peak_hour = int(cells.loc[max_idx, "peak_hour"])

        # Hourly distribution from raw data (match by proximity)
        # Use a fast bounding box to find raw violations near this cluster
        # Dynamic expansion: 1 deg lon shrinks by cos(lat)
        mean_lat = cells["latitude"].mean()
        lat_delta = 0.002 # ~222 meters
        lon_delta = 0.002 / max(0.1, cos(radians(mean_lat)))
        
        lat_min, lat_max = cells["latitude"].min() - lat_delta, cells["latitude"].max() + lat_delta
        lon_min, lon_max = cells["longitude"].min() - lon_delta, cells["longitude"].max() + lon_delta
        
        nearby = raw_df[
            (raw_df["latitude"] >= lat_min) & (raw_df["latitude"] <= lat_max) &
            (raw_df["longitude"] >= lon_min) & (raw_df["longitude"] <= lon_max)
        ]

        hourly_dist = [0] * 24
        if len(nearby) > 0 and "hour_ist" in nearby.columns:
            hour_counts = nearby["hour_ist"].dropna().astype(int).value_counts()
            for h, c in hour_counts.items():
                if 0 <= h < 24:
                    hourly_dist[h] = int(c)

        daily_dist = [0] * 7
        if len(nearby) > 0 and "day_of_week" in nearby.columns:
            day_counts = nearby["day_of_week"].dropna().astype(int).value_counts()
            for d, c in day_counts.items():
                if 0 <= d < 7:
                    daily_dist[d] = int(c)

        # Unique days
        unique_days = 1
        if len(nearby) > 0 and "violation_date_ist" in nearby.columns:
            unique_days = max(1, nearby["violation_date_ist"].dt.date.nunique())

        # Severity
        severity = cells["severity_mean"].mean()

        # Location label
        place_text = cells.loc[cells["count"].idxmax(), "place"]
        if pd.notna(place_text):
            parts = str(place_text).split(",")
            location_label = ", ".join(parts[:2]).strip() if len(parts) > 1 else str(place_text)[:100]
        else:
            location_label = f"Cluster {label}"

        clusters.append({
            "cluster_label": int(label),
            "centroid_lat": round(float(centroid_lat), 6),
            "centroid_lon": round(float(centroid_lon), 6),
            "location_label": location_label[:500],
            "violation_count": int(total_count),
            "unique_days": int(unique_days),
            "radius_meters": round(float(radius), 1),
            "dominant_violation": dominant_violation,
            "dominant_vehicle": dominant_vehicle,
            "peak_hour": peak_hour,
            "hourly_distribution": hourly_dist,
            "daily_distribution": daily_dist,
            "severity_score": round(float(severity), 2),
            "police_station": police_station,
            "time_slice": time_slice,
            # These will be set by congestion_scorer
            "congestion_impact_score": 0.0,
            "cis_tier": "low",
            "priority_score": 0.0,
        })

    return clusters


def detect_hotspots(
    df: pd.DataFrame,
    eps_meters: float = 200.0,
    min_samples: int = 15,
) -> List[Dict]:
    """
    Run hotspot detection across all time slices.
    Uses grid-based aggregation to handle 300K+ records without MemoryError.
    """
    all_hotspots = []
    min_cells = 3  # Minimum grid cells to form a cluster

    for slice_name, (hour_start, hour_end) in TIME_SLICES.items():
        if slice_name == "all":
            slice_df = df
        else:
            slice_df = df[
                (df["hour_ist"] >= hour_start) & (df["hour_ist"] < hour_end)
            ]

        if len(slice_df) < min_samples:
            print(f"  [SKIP] {slice_name}: only {len(slice_df)} records")
            continue

        print(f"  [CLUSTER] {slice_name}: {len(slice_df)} violations...")

        # Step 1: Grid aggregation
        grid_df = grid_aggregate(slice_df)
        print(f"     -> Aggregated into {len(grid_df)} grid cells")

        # Step 2: DBSCAN on grid cells
        labels = run_dbscan_on_grid(grid_df, eps_meters=eps_meters, min_cells=min_cells)

        n_clusters = len(set(labels) - {-1})
        n_noise = (labels == -1).sum()
        print(f"     -> {n_clusters} clusters found, {n_noise} noise cells")

        # Step 3: Compute cluster stats
        clusters = compute_cluster_stats(grid_df, labels, slice_df, time_slice=slice_name)
        all_hotspots.extend(clusters)

    print(f"\n[DONE] Total hotspots: {len(all_hotspots)} across {len(TIME_SLICES)} time slices")
    return all_hotspots
