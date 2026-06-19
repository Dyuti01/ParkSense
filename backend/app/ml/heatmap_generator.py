"""
ParkSense AI -- Heatmap Grid Generator

Divides Bengaluru into a grid and computes violation density per cell
for fast map rendering.
"""

import numpy as np
import pandas as pd
from typing import List, Dict

# Bengaluru bounding box
LAT_MIN = 12.80
LAT_MAX = 13.30
LON_MIN = 77.44
LON_MAX = 77.78

# Grid cell size in degrees (~200m at Bengaluru's latitude)
CELL_SIZE_LAT = 0.0018
CELL_SIZE_LON = 0.00185


def generate_heatmap_grid(
    df: pd.DataFrame,
    time_slices: Dict[str, tuple] = None,
) -> List[Dict]:
    """
    Generate heatmap grid cells from violation data.
    Only generates for "all" time slice to keep DB size manageable.
    """
    if time_slices is None:
        time_slices = {"all": (0, 24)}

    all_cells = []

    for slice_name, (hour_start, hour_end) in time_slices.items():
        if slice_name == "all":
            slice_df = df
        else:
            slice_df = df[
                (df["hour_ist"] >= hour_start) & (df["hour_ist"] < hour_end)
            ]

        if len(slice_df) == 0:
            continue

        print(f"  [HEATMAP] '{slice_name}': {len(slice_df)} violations...")

        # Assign each violation to a grid cell
        slice_df = slice_df.copy()
        slice_df["grid_row"] = ((slice_df["latitude"] - LAT_MIN) / CELL_SIZE_LAT).astype(int)
        slice_df["grid_col"] = ((slice_df["longitude"] - LON_MIN) / CELL_SIZE_LON).astype(int)

        # Aggregate per cell using vectorized groupby
        cell_stats = slice_df.groupby(["grid_row", "grid_col"]).agg(
            violation_count=("latitude", "count"),
            severity_sum=("severity_score", "sum"),
            lat_mean=("latitude", "mean"),
            lon_mean=("longitude", "mean"),
        ).reset_index()

        # Compute density (violations per hectare)
        # Each cell is ~200m x 200m = 4 hectares
        cell_stats["density"] = cell_stats["violation_count"] / 4.0

        # Convert to list of dicts for DB insertion
        for _, row in cell_stats.iterrows():
            all_cells.append({
                "grid_lat": round(float(row["lat_mean"]), 6),
                "grid_lon": round(float(row["lon_mean"]), 6),
                "weight": round(float(row["density"]), 2),
                "time_slice": slice_name,
            })

    print(f"[DONE] Heatmap: {len(all_cells)} non-empty cells")
    return all_cells
