-- ParkSense AI — Database Init Script
-- Creates tables without PostGIS extension (using plain lat/lon columns)

-- Violations table (main data)
CREATE TABLE IF NOT EXISTS violations (
    violation_number VARCHAR(100) PRIMARY KEY,
    violation_date TIMESTAMP WITH TIME ZONE NOT NULL,
    violation_date_ist TIMESTAMP NOT NULL,
    booked_date TIMESTAMP WITH TIME ZONE,
    violation_type VARCHAR(255) NOT NULL,
    vehicle_type VARCHAR(100),
    vehicle_number_hash VARCHAR(100),
    place VARCHAR(500) NOT NULL,
    police_station VARCHAR(200),
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    amount NUMERIC(10, 2),
    payment_status VARCHAR(50),
    severity_score DOUBLE PRECISION DEFAULT 0,
    hour_ist INTEGER,
    day_of_week INTEGER,
    month INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Hotspots table (ML pipeline output)
CREATE TABLE IF NOT EXISTS hotspots (
    id SERIAL PRIMARY KEY,
    cluster_label INTEGER NOT NULL,
    centroid_lat DOUBLE PRECISION NOT NULL,
    centroid_lon DOUBLE PRECISION NOT NULL,
    radius_meters DOUBLE PRECISION,
    violation_count INTEGER NOT NULL,
    unique_days INTEGER,
    dominant_violation VARCHAR(255),
    dominant_vehicle VARCHAR(100),
    police_station VARCHAR(200),
    location_label VARCHAR(500),
    congestion_impact_score DOUBLE PRECISION NOT NULL,
    cis_tier VARCHAR(20) NOT NULL,
    priority_score DOUBLE PRECISION DEFAULT 0,
    peak_hour INTEGER,
    hourly_distribution JSONB,
    daily_distribution JSONB,
    time_slice VARCHAR(20) DEFAULT 'all',
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Station statistics (aggregated)
CREATE TABLE IF NOT EXISTS station_stats (
    id SERIAL PRIMARY KEY,
    police_station VARCHAR(200) UNIQUE NOT NULL,
    total_violations INTEGER NOT NULL,
    approved_count INTEGER DEFAULT 0,
    rejected_count INTEGER DEFAULT 0,
    violation_breakdown JSONB,
    vehicle_breakdown JSONB,
    hourly_distribution JSONB,
    daily_distribution JSONB,
    monthly_trend JSONB,
    top_locations JSONB,
    top_junctions JSONB,
    cis_avg DOUBLE PRECISION DEFAULT 0,
    cis_max DOUBLE PRECISION DEFAULT 0,
    enforcement_rate DOUBLE PRECISION DEFAULT 0,
    validation_rate DOUBLE PRECISION DEFAULT 0,
    hotspot_count INTEGER DEFAULT 0,
    critical_hotspots INTEGER DEFAULT 0,
    peak_hour INTEGER,
    peak_day INTEGER,
    trend_direction VARCHAR(20) DEFAULT 'stable',
    trend_percentage DOUBLE PRECISION DEFAULT 0,
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Heatmap grid (pre-computed)
CREATE TABLE IF NOT EXISTS heatmap_grid (
    id SERIAL PRIMARY KEY,
    cell_lat DOUBLE PRECISION NOT NULL,
    cell_lon DOUBLE PRECISION NOT NULL,
    grid_row INTEGER,
    grid_col INTEGER,
    violation_count INTEGER DEFAULT 0,
    severity_sum DOUBLE PRECISION DEFAULT 0,
    density DOUBLE PRECISION DEFAULT 0,
    dominant_type VARCHAR(100),
    time_slice VARCHAR(20) DEFAULT 'all',
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Pipeline run history
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id SERIAL PRIMARY KEY,
    run_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    records_processed INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    records_skipped INTEGER DEFAULT 0,
    hotspots_found INTEGER DEFAULT 0,
    error_message TEXT,
    details JSONB,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Users table (authentication)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(200),
    role VARCHAR(20) DEFAULT 'officer',
    police_station VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_violations_station ON violations(police_station);
CREATE INDEX IF NOT EXISTS idx_violations_type ON violations(violation_type);
CREATE INDEX IF NOT EXISTS idx_violations_date ON violations(violation_date_ist);
CREATE INDEX IF NOT EXISTS idx_violations_hour ON violations(hour_ist);
CREATE INDEX IF NOT EXISTS idx_violations_latlon ON violations(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_hotspots_tier ON hotspots(cis_tier);
CREATE INDEX IF NOT EXISTS idx_hotspots_station ON hotspots(police_station);
CREATE INDEX IF NOT EXISTS idx_hotspots_cis ON hotspots(congestion_impact_score DESC);
CREATE INDEX IF NOT EXISTS idx_hotspots_time_slice ON hotspots(time_slice);
CREATE INDEX IF NOT EXISTS idx_heatmap_time_slice ON heatmap_grid(time_slice);

-- Default admin user (password: admin123 — change in production!)
INSERT INTO users (username, email, hashed_password, full_name, role)
VALUES ('admin', 'admin@parksense.ai', '$2b$12$P1SI5vkw67Tf3VbOLZ/.buwfFa719AWe1nXNU9Qy636y/5uf61Ioe', 'System Admin', 'admin')
ON CONFLICT (username) DO NOTHING;
