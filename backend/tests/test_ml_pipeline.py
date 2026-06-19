import pandas as pd
import numpy as np
from app.ml.hotspot_detector import detect_hotspots, haversine
from app.ml.congestion_scorer import compute_cis

def test_haversine():
    # Distance between same points should be 0
    assert haversine(12.0, 77.0, 12.0, 77.0) == 0.0

def test_hotspot_detection():
    # Create a dummy dataframe with points spread across at least 3 grid cells
    # Grid size is 0.0005, so we space them by 0.0006
    data = []
    
    # Cluster 1: spread across 3 cells (latitudes 12.9710, 12.9716, 12.9722)
    lats = [12.9710, 12.9716, 12.9722]
    for lat in lats:
        for i in range(10): # 10 points per cell = 30 points total
            data.append({
                "latitude": lat + np.random.uniform(-0.0001, 0.0001),
                "longitude": 77.5946 + np.random.uniform(-0.0001, 0.0001),
                "severity_score": 5.0,
                "violation_type": "NO PARKING",
                "vehicle_type": "2 W",
                "police_station": "Station A",
                "place": "Test Place 1",
                "hour_ist": 10,
                "day_of_week": 1,
            })
            
    # Cluster 2: spread across 4 cells
    lats2 = [13.0000, 13.0006, 13.0012, 13.0018]
    for lat in lats2:
        for i in range(10): # 10 points per cell = 40 points total
            data.append({
                "latitude": lat + np.random.uniform(-0.0001, 0.0001),
                "longitude": 77.6000 + np.random.uniform(-0.0001, 0.0001),
                "severity_score": 8.0,
                "violation_type": "WRONG PARKING",
                "vehicle_type": "4 W",
                "police_station": "Station B",
                "place": "Test Place 2",
                "hour_ist": 15,
                "day_of_week": 2,
            })
    
    df = pd.DataFrame(data)
    # Convert dates or handle missing columns since our mock is simple
    df["violation_date_ist"] = pd.to_datetime("2024-01-01")

    hotspots = detect_hotspots(df, eps_meters=200, min_samples=10)
    
    # We should have 2 clusters in 'all' time slice
    all_slice_hotspots = [h for h in hotspots if h["time_slice"] == "all"]
    assert len(all_slice_hotspots) == 2
    
    # Run congestion scorer
    scored_hotspots = compute_cis(all_slice_hotspots)
    
    assert len(scored_hotspots) == 2
    assert "congestion_impact_score" in scored_hotspots[0]
    assert scored_hotspots[0]["cis_tier"] in ["critical", "high", "moderate", "low"]
