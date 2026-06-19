"""
ParkSense AI -- Congestion Impact Scorer

Computes the Congestion Impact Score (CIS) for each hotspot,
quantifying how parking violations at that location affect traffic flow.
"""

import numpy as np
from typing import List, Dict


def compute_gini(values: list) -> float:
    """
    Compute Gini coefficient of a distribution.
    Higher = more concentrated (all violations in few hours).
    """
    arr = np.asarray(values, dtype=float)
    if arr.sum() == 0:
        return 0.0
    arr = np.sort(arr)
    n = len(arr)
    index = np.arange(1, n + 1)
    gini = (np.sum((2 * index - n - 1) * arr)) / (n * np.sum(arr))
    
    if n > 1:
        gini = gini * (n / (n - 1))
        
    return max(0.0, min(1.0, float(gini)))


def compute_cis(
    hotspots: List[Dict],
    weights: Dict[str, float] = None,
) -> List[Dict]:
    """
    Compute Congestion Impact Score (CIS) for each hotspot.

    CIS = w1*ViolationVolume + w2*SeverityScore + w3*TemporalConcentration
        + w4*RecurrenceDays

    Each component is min-max normalized to [0, 1], then CIS is scaled to [0, 100].

    IMPORTANT: To maintain mathematical integrity, this function MUST be called 
    on isolated time slices (e.g., all 'morning' hotspots together, all 'night' 
    hotspots together). Passing hotspots from different temporal cohorts in the 
    same list will cause global Min-Max volume scaling to wash out low-volume 
    time slices (like night), rendering their priority scores meaningless.
    """
    if not hotspots:
        return hotspots

    if weights is None:
        weights = {
            "volume": 0.35,
            "severity": 0.25,
            "temporal": 0.20,
            "recurrence": 0.20,
        }

    # Extract raw values for normalization
    volumes = [h["violation_count"] for h in hotspots]
    severities = [h.get("severity_score", 0) for h in hotspots]
    unique_days_list = [h.get("unique_days", 1) for h in hotspots]

    # Temporal concentration: Gini coefficient of hourly distribution
    temporal_concentrations = []
    for h in hotspots:
        dist = h.get("hourly_distribution", [0] * 24)
        gini = compute_gini(dist)
        temporal_concentrations.append(gini)

    # Min-max normalize each component
    def normalize(values):
        arr = np.array(values, dtype=float)
        min_val, max_val = arr.min(), arr.max()
        if max_val == min_val:
            return np.full_like(arr, 0.5)  # All same = moderate
        return (arr - min_val) / (max_val - min_val)

    norm_volume = normalize(volumes)
    norm_severity = normalize(severities)
    norm_temporal = normalize(temporal_concentrations)
    norm_recurrence = normalize(unique_days_list)

    # Compute CIS
    for i, h in enumerate(hotspots):
        cis = (
            weights["volume"] * norm_volume[i]
            + weights["severity"] * norm_severity[i]
            + weights["temporal"] * norm_temporal[i]
            + weights["recurrence"] * norm_recurrence[i]
        ) * 100  # Scale to 0-100

        h["congestion_impact_score"] = round(float(cis), 2)

        # Assign tier
        if cis >= 75:
            h["cis_tier"] = "critical"
        elif cis >= 50:
            h["cis_tier"] = "high"
        elif cis >= 25:
            h["cis_tier"] = "moderate"
        else:
            h["cis_tier"] = "low"

    # Priority score = CIS * log(violation_count)
    for h in hotspots:
        vol_boost = np.log1p(h["violation_count"]) / np.log1p(max(volumes))
        h["priority_score"] = round(float(h["congestion_impact_score"] * (0.5 + 0.5 * vol_boost)), 2)

    # Sort by CIS descending
    hotspots.sort(key=lambda x: x["congestion_impact_score"], reverse=True)

    # Stats
    cis_values = [h["congestion_impact_score"] for h in hotspots]
    tiers = [h["cis_tier"] for h in hotspots]
    print(f"\n[CIS] Scoring Results:")
    print(f"   Mean CIS: {np.mean(cis_values):.1f}")
    print(f"   Max CIS:  {np.max(cis_values):.1f}")
    print(f"   Critical: {tiers.count('critical')} | High: {tiers.count('high')} | Moderate: {tiers.count('moderate')} | Low: {tiers.count('low')}")

    return hotspots
