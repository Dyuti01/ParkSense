"""
ParkSense AI — Data Preprocessor

Cleans, enriches, and transforms raw violation data for analysis.
Handles CSV parsing, UTC→IST conversion, violation type parsing,
severity scoring, and derived feature creation.
"""

import pandas as pd
import numpy as np
import re
import json
from datetime import timedelta
from typing import Dict, List, Optional

# Violation severity weights: how much each type impacts traffic flow (1-10)
SEVERITY_WEIGHTS: Dict[str, float] = {
    "DOUBLE PARKING": 10.0,
    "PARKING IN A MAIN ROAD": 9.0,
    "PARKING NEAR ROAD CROSSING": 8.5,
    "PARKING NEAR TRAFFIC LIGHT OR ZEBRA CROSS": 8.5,
    "PARKING OPPOSITE TO ANOTHER PARKED VEHICLE": 8.0,
    "WRONG PARKING": 7.0,
    "PARKING NEAR BUSTOP/SCHOOL/HOSPITAL ETC": 7.0,
    "NO PARKING": 6.0,
    "PARKING ON FOOTPATH": 4.0,
    "PARKING OTHER THAN BUS STOP": 5.0,
    "H T V PROHIBITED": 6.0,
    "AGAINST ONE WAY/NO ENTRY": 7.0,
    "DEFECTIVE NUMBER PLATE": 2.0,
    "USING BLACK FILM/OTHER MATERIALS": 1.0,
    "WITHOUT SIDE MIRROR": 1.0,
    "REFUSE TO GO FOR HIRE": 1.0,
    "DEMANDING EXCESS FARE": 1.0,
    "OBSTRUCTING DRIVER": 3.0,
    "FAIL TO USE SAFETY BELTS": 2.0,
    "VIOLATING LANE DISIPLINE": 3.0,
    "RIDER NOT WEARING HELMET": 2.0,
    "2W/3W - USING MOBILE PHONE": 2.0,
    "OTHER - USING MOBILE PHONE": 2.0,
    "CARRYING LENGHTY MATERIAL": 3.0,
    "JUMPING TRAFFIC SIGNAL": 5.0,
    "U TURN PROHIBITED": 4.0,
    "STOPING ON WHITE/STOP LINE": 5.0,
}


def parse_violation_types(raw: str) -> List[str]:
    """Parse the JSON-encoded violation_type column into a clean list."""
    if pd.isna(raw) or raw == "NULL":
        return []
    try:
        # Handle double-escaped quotes: ["WRONG PARKING","NO PARKING"]
        cleaned = raw.replace('""', '"')
        if cleaned.startswith('["') or cleaned.startswith("[\""):
            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                return [str(v).strip() for v in parsed if v]
    except (json.JSONDecodeError, TypeError):
        pass

    # Fallback: regex extraction
    matches = re.findall(r'[A-Z][A-Z /]+[A-Z]', str(raw))
    return matches if matches else [str(raw).strip()]


def compute_severity(violation_types: List[str]) -> float:
    """Compute aggregate severity score from violation types."""
    if not violation_types:
        return 0.0
    scores = [SEVERITY_WEIGHTS.get(vt, 3.0) for vt in violation_types]
    return max(scores)  # Take the most severe


def preprocess_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Full preprocessing pipeline for violation data.
    
    Transforms raw CSV data into analysis-ready format with:
    - Parsed violation types
    - UTC to IST time conversion
    - Derived temporal features (hour, day, month)
    - Severity scoring
    - Primary violation type extraction
    
    Output columns match the `violations` table in init.sql.
    """
    print(f"📊 Preprocessing {len(df)} records...")

    # Drop rows with missing coordinates
    initial_count = len(df)
    df = df.dropna(subset=["latitude", "longitude"])
    dropped_coords = initial_count - len(df)
    if dropped_coords > 0:
        print(f"   ⚠️  Dropped {dropped_coords} rows with missing lat/lon")

    # Parse violation types (JSON array string → list)
    df["violation_types_list"] = df["violation_type"].apply(parse_violation_types)

    # Take the PRIMARY (most severe) violation type for the DB column
    def primary_violation(types_list):
        if not types_list:
            return "UNKNOWN"
        scored = [(vt, SEVERITY_WEIGHTS.get(vt, 3.0)) for vt in types_list]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0]

    df["primary_violation"] = df["violation_types_list"].apply(primary_violation)

    # Compute severity score
    df["severity_score"] = df["violation_types_list"].apply(compute_severity)

    # Time conversion: UTC → IST (UTC+5:30)
    df["created_at"] = pd.to_datetime(df["created_datetime"], errors="coerce", utc=True)
    df = df.dropna(subset=["created_at"])
    df["created_at_ist"] = df["created_at"] + timedelta(hours=5, minutes=30)

    # Derived temporal features
    df["hour_ist"] = df["created_at_ist"].dt.hour.astype("Int16")
    df["day_of_week"] = df["created_at_ist"].dt.dayofweek.astype("Int16")  # 0=Monday
    df["month_num"] = df["created_at_ist"].dt.month.astype("Int16")

    # Vehicle type: prefer updated_vehicle_type if available
    df["final_vehicle_type"] = df["updated_vehicle_type"].fillna(df["vehicle_type"])

    # Build output DataFrame matching the violations table schema
    out = pd.DataFrame({
        "violation_number": df["id"],
        "violation_date": df["created_at"],
        "violation_date_ist": df["created_at_ist"],
        "booked_date": pd.to_datetime(df.get("closed_datetime"), errors="coerce", utc=True),
        "violation_type": df["primary_violation"],
        "vehicle_type": df["final_vehicle_type"],
        "vehicle_number_hash": df["vehicle_number"],
        "place": df["location"].fillna("Unknown Location"),
        "police_station": df["police_station"],
        "latitude": df["latitude"],
        "longitude": df["longitude"],
        "amount": None,
        "payment_status": df.get("validation_status"),
        "severity_score": df["severity_score"],
        "hour_ist": df["hour_ist"],
        "day_of_week": df["day_of_week"],
        "month": df["month_num"],
    })

    # Also keep raw columns for the ML pipeline
    out["_all_violation_types"] = df["violation_types_list"].values
    out["_data_sent_to_scita"] = df.get("data_sent_to_scita", False)
    out["_junction_name"] = df.get("junction_name")

    print(f"✅ Preprocessing complete:")
    print(f"   - Records: {len(out)}")
    print(f"   - Severity scores: mean={out['severity_score'].mean():.1f}, max={out['severity_score'].max():.1f}")
    print(f"   - Date range: {out['violation_date_ist'].min()} to {out['violation_date_ist'].max()}")
    print(f"   - Stations: {out['police_station'].nunique()}")
    print(f"   - Violation types: {out['violation_type'].nunique()}")

    return out
