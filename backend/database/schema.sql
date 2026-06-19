-- ParkSense AI — Database Schema
-- PostgreSQL 17 + PostGIS

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- ============================================================
-- Core violation records table
-- ============================================================
CREATE TABLE IF NOT EXISTS violations (
    id VARCHAR(20) PRIMARY KEY,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    location_point GEOGRAPHY(POINT, 4326),
    location_text TEXT,
    area_name VARCHAR(200),
    pin_code VARCHAR(10),
    road_type VARCHAR(50),

    vehicle_number VARCHAR(30) NOT NULL,
    vehicle_type VARCHAR(50),
    updated_vehicle_type VARCHAR(50),

    violation_types TEXT[] NOT NULL,
    offence_codes INTEGER[],
    severity_score REAL DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL,
    created_at_ist TIMESTAMPTZ,
    hour_ist SMALLINT,
    day_of_week SMALLINT,
    month_num SMALLINT,
    is_weekend BOOLEAN DEFAULT FALSE,

    device_id VARCHAR(20),
    created_by_id VARCHAR(20),
    center_code INTEGER,
    police_station VARCHAR(100),
    junction_name VARCHAR(200),
    is_junction BOOLEAN DEFAULT FALSE,

    data_sent_to_scita BOOLEAN DEFAULT FALSE,
    validation_status VARCHAR(20),
    validation_timestamp TIMESTAMPTZ,

    modified_datetime TIMESTAMPTZ,
    closed_datetime TIMESTAMPTZ,

    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    batch_id VARCHAR(50)
);

-- Spatial index for PostGIS geo queries
CREATE INDEX IF NOT EXISTS idx_violations_geo ON violations USING GIST(location_point);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_violations_station ON violations(police_station);
CREATE INDEX IF NOT EXISTS idx_violations_created ON violations(created_at_ist);
CREATE INDEX IF NOT EXISTS idx_violations_hour ON violations(hour_ist);
CREATE INDEX IF NOT EXISTS idx_violations_dow ON violations(day_of_week);
CREATE INDEX IF NOT EXISTS idx_violations_type ON violations USING GIN(violation_types);
CREATE INDEX IF NOT EXISTS idx_violations_junction ON violations(is_junction);
CREATE INDEX IF NOT EXISTS idx_violations_vehicle ON violations(vehicle_type);
CREATE INDEX IF NOT EXISTS idx_violations_batch ON violations(batch_id);

-- ============================================================
-- Computed hotspot clusters (refreshed by ML pipeline)
-- ============================================================
CREATE TABLE IF NOT EXISTS hotspots (
    id SERIAL PRIMARY KEY,
    cluster_label INTEGER,
    centroid_lat DOUBLE PRECISION NOT NULL,
    centroid_lon DOUBLE PRECISION NOT NULL,
    centroid GEOGRAPHY(POINT, 4326),
    location_label VARCHAR(300),

    violation_count INTEGER NOT NULL DEFAULT 0,
    unique_days INTEGER DEFAULT 0,
    density REAL DEFAULT 0,
    radius_meters REAL DEFAULT 0,

    dominant_violation VARCHAR(100),
    dominant_vehicle VARCHAR(50),
    violation_breakdown JSONB DEFAULT '{}',
    vehicle_breakdown JSONB DEFAULT '{}',

    peak_hour SMALLINT,
    peak_day SMALLINT,
    hourly_distribution JSONB DEFAULT '[]',

    severity_score REAL DEFAULT 0,
    congestion_impact_score REAL DEFAULT 0,
    cis_tier VARCHAR(20) DEFAULT 'low',

    junction_proximity REAL DEFAULT 0,
    temporal_concentration REAL DEFAULT 0,
    recurrence_rate REAL DEFAULT 0,
    enforcement_gap REAL DEFAULT 0,
    priority_score REAL DEFAULT 0,

    police_station VARCHAR(100),
    junction_name VARCHAR(200),

    time_slice VARCHAR(20) DEFAULT 'all',
    data_start_date DATE,
    data_end_date DATE,
    computed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hotspots_geo ON hotspots USING GIST(centroid);
CREATE INDEX IF NOT EXISTS idx_hotspots_cis ON hotspots(congestion_impact_score DESC);
CREATE INDEX IF NOT EXISTS idx_hotspots_priority ON hotspots(priority_score DESC);
CREATE INDEX IF NOT EXISTS idx_hotspots_tier ON hotspots(cis_tier);
CREATE INDEX IF NOT EXISTS idx_hotspots_slice ON hotspots(time_slice);

-- ============================================================
-- Station-level aggregated statistics
-- ============================================================
CREATE TABLE IF NOT EXISTS station_stats (
    id SERIAL PRIMARY KEY,
    police_station VARCHAR(100) UNIQUE NOT NULL,
    total_violations INTEGER DEFAULT 0,
    approved_count INTEGER DEFAULT 0,
    rejected_count INTEGER DEFAULT 0,

    violation_breakdown JSONB DEFAULT '{}',
    vehicle_breakdown JSONB DEFAULT '{}',
    hourly_distribution JSONB DEFAULT '[]',
    daily_distribution JSONB DEFAULT '[]',
    monthly_trend JSONB DEFAULT '[]',

    top_locations JSONB DEFAULT '[]',
    top_junctions JSONB DEFAULT '[]',

    cis_avg REAL DEFAULT 0,
    cis_max REAL DEFAULT 0,
    enforcement_rate REAL DEFAULT 0,
    validation_rate REAL DEFAULT 0,

    hotspot_count INTEGER DEFAULT 0,
    critical_hotspots INTEGER DEFAULT 0,

    peak_hour SMALLINT,
    peak_day SMALLINT,

    trend_direction VARCHAR(20) DEFAULT 'stable',
    trend_percentage REAL DEFAULT 0,

    computed_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- Heatmap grid cells for fast map rendering
-- ============================================================
CREATE TABLE IF NOT EXISTS heatmap_grid (
    id SERIAL PRIMARY KEY,
    cell_lat DOUBLE PRECISION NOT NULL,
    cell_lon DOUBLE PRECISION NOT NULL,
    cell_point GEOGRAPHY(POINT, 4326),
    grid_row INTEGER,
    grid_col INTEGER,

    violation_count INTEGER DEFAULT 0,
    severity_sum REAL DEFAULT 0,
    density REAL DEFAULT 0,
    dominant_type VARCHAR(100),

    time_slice VARCHAR(20) DEFAULT 'all',
    computed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_heatmap_geo ON heatmap_grid USING GIST(cell_point);
CREATE INDEX IF NOT EXISTS idx_heatmap_slice ON heatmap_grid(time_slice);

-- ============================================================
-- Pipeline execution log
-- ============================================================
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id SERIAL PRIMARY KEY,
    run_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    records_processed INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    records_skipped INTEGER DEFAULT 0,
    hotspots_found INTEGER DEFAULT 0,
    error_message TEXT,
    details JSONB DEFAULT '{}',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- ============================================================
-- Users table (for authentication)
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(200) NOT NULL,
    full_name VARCHAR(100),
    role VARCHAR(20) NOT NULL DEFAULT 'officer',
    police_station VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);

-- Default admin user (password: admin123 — change in production!)
-- Hash generated with passlib bcrypt
-- INSERT INTO users (username, email, hashed_password, full_name, role)
-- VALUES ('admin', 'admin@parksense.ai', '<bcrypt_hash>', 'System Admin', 'admin');
