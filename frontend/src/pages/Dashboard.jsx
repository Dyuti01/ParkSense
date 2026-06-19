/**
 * ParkSense AI — Dashboard Page (Command Center)
 * 
 * The main overview page with KPIs, interactive map, 
 * hotspot rankings, and temporal charts.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet.heat';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area, PieChart, Pie, Cell, LineChart, Line,
} from 'recharts';
import {
  AlertTriangle, TrendingUp, MapPin, Car, Clock,
  Building2, Shield, Activity, Zap, Target,
} from 'lucide-react';
import {
  fetchOverview, fetchTopHotspots, fetchHourlyDistribution,
  fetchDailyDistribution, fetchViolationTypes, fetchVehicleTypes,
  fetchMonthlyTrend,
} from '../api';
import { useTheme } from '../context/ThemeContext';
import 'leaflet/dist/leaflet.css';

// ── Chart Colors ────────────────────────────────────────────
const CHART_COLORS = ['#3b82f6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#6366f1'];
const TIER_COLORS = { critical: '#ef4444', high: '#f59e0b', moderate: '#06b6d4', low: '#10b981' };

// Custom Recharts tooltip
const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="recharts-default-tooltip" style={{ padding: '10px 14px' }}>
      <p className="recharts-tooltip-label">{label}</p>
      {payload.map((p, i) => (
        <p key={i} className="recharts-tooltip-item" style={{ color: p.color || 'var(--primary-light)', fontWeight: 600 }}>
          {p.name}: {typeof p.value === 'number' ? p.value.toLocaleString() : p.value}
        </p>
      ))}
    </div>
  );
};

// Animated counter hook
function useAnimatedCounter(target, duration = 1200) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (!target) return;
    let start = 0;
    const end = parseInt(target);
    const step = Math.max(1, Math.floor(end / (duration / 16)));
    const timer = setInterval(() => {
      start += step;
      if (start >= end) {
        setCount(end);
        clearInterval(timer);
      } else {
        setCount(start);
      }
    }, 16);
    return () => clearInterval(timer);
  }, [target, duration]);
  return count;
}

// ── Map Component ───────────────────────────────────────────
function HeatmapLayer({ hotspots }) {
  const map = useMap();
  useEffect(() => {
    if (!hotspots || hotspots.length === 0) return;
    const points = hotspots.map(h => [h.centroid_lat, h.centroid_lon, h.congestion_impact_score || h.violation_count]);
    const heat = L.heatLayer(points, { radius: 25, blur: 15, maxZoom: 14 }).addTo(map);
    return () => { map.removeLayer(heat); };
  }, [map, hotspots]);
  return null;
}

function MapFlyTo({ selectedHotspot }) {
  const map = useMap();
  useEffect(() => {
    if (selectedHotspot) {
      map.flyTo([selectedHotspot.centroid_lat, selectedHotspot.centroid_lon], 15, { duration: 1.5 });
    }
  }, [map, selectedHotspot]);
  return null;
}

function HotspotMap({ hotspots, selectedHotspot, onHotspotClick, showHeatmap }) {
  const { theme } = useTheme();
  const center = [12.97, 77.59]; // Bangalore center

  return (
    <MapContainer center={center} zoom={12} style={{ height: '100%', width: '100%' }}>
      <TileLayer
        url={theme === 'dark' ? "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" : "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"}
        attribution='&copy; <a href="https://carto.com">CARTO</a>'
      />
      <MapFlyTo selectedHotspot={selectedHotspot} />
      {showHeatmap ? (
        <HeatmapLayer hotspots={hotspots} />
      ) : (
        hotspots.map((h, i) => {
          const color = TIER_COLORS[h.cis_tier] || TIER_COLORS.low;
          const radius = Math.max(6, Math.min(20, h.violation_count / 50));
          return (
            <CircleMarker
              key={h.id || i}
              center={[h.centroid_lat, h.centroid_lon]}
              radius={radius}
              pathOptions={{
                fillColor: color,
                fillOpacity: 0.6,
                color: color,
                weight: 2,
                opacity: 0.8,
              }}
              eventHandlers={{ click: () => onHotspotClick?.(h) }}
            >
              <Popup>
                <div style={{ minWidth: '200px' }}>
                  <h4 style={{ marginBottom: '6px', fontSize: '14px' }}>{h.location_label}</h4>
                  <div style={{ display: 'flex', gap: '8px', marginBottom: '6px', flexWrap: 'wrap' }}>
                    <span className={`cis-badge ${h.cis_tier}`}>
                      CIS {h.congestion_impact_score}
                    </span>
                    <span style={{ fontSize: '12px', color: '#9ca3af' }}>
                      {h.violation_count} violations
                    </span>
                  </div>
                  <p style={{ fontSize: '12px', color: '#9ca3af', margin: 0 }}>
                    {h.dominant_violation} | Peak: {h.peak_hour}:00 IST
                  </p>
                  {h.police_station && (
                    <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                      📍 {h.police_station}
                    </p>
                  )}
                </div>
              </Popup>
            </CircleMarker>
          );
        }))}
    </MapContainer>
  );
}

// ── Main Dashboard ──────────────────────────────────────────
export default function Dashboard() {
  const [overview, setOverview] = useState(null);
  const [hotspots, setHotspots] = useState([]);
  const [hourly, setHourly] = useState([]);
  const [daily, setDaily] = useState([]);
  const [monthly, setMonthly] = useState([]);
  const [violTypes, setViolTypes] = useState([]);
  const [vehicleTypes, setVehicleTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedHotspot, setSelectedHotspot] = useState(null);
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [sortBy, setSortBy] = useState('cis');

  useEffect(() => {
    async function loadData() {
      try {
        const [ov, hs, hr, dy, mn, vt, ve] = await Promise.all([
          fetchOverview(),
          fetchTopHotspots(20),
          fetchHourlyDistribution(),
          fetchDailyDistribution(),
          fetchMonthlyTrend(),
          fetchViolationTypes(),
          fetchVehicleTypes(),
        ]);
        setOverview(ov.data);
        setHotspots(hs.data.hotspots || []);
        setHourly(hr.data.distribution || []);
        setDaily(dy.data.distribution || []);
        setMonthly(mn.data.trend || []);
        setViolTypes((vt.data.types || []).slice(0, 8));
        setVehicleTypes((ve.data.vehicles || []).slice(0, 8));
      } catch (err) {
        console.error('Dashboard load error:', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  // Animated counters
  const totalViolations = useAnimatedCounter(overview?.total_violations);
  const totalHotspots = useAnimatedCounter(overview?.total_hotspots);
  const criticalZones = useAnimatedCounter(overview?.critical_zones);

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p className="loading-text">Loading command center...</p>
      </div>
    );
  }

  return (
    <div className="animate-in">
      {/* KPI Cards */}
      <div className="kpi-grid stagger-in">
        <div className="kpi-card">
          <div className="kpi-label"><Activity size={16} /> Total Violations</div>
          <div className="kpi-value" style={{ color: 'var(--primary-light)' }}>
            {totalViolations.toLocaleString()}
          </div>
          <div className="kpi-sub">
            {overview?.date_range?.start?.slice(0, 10)} → {overview?.date_range?.end?.slice(0, 10)}
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label"><MapPin size={16} /> Active Hotspots</div>
          <div className="kpi-value" style={{ color: 'var(--high-light)' }}>
            {totalHotspots.toLocaleString()}
          </div>
          <div className="kpi-sub">Detected by DBSCAN clustering</div>
        </div>

        <div className="kpi-card critical">
          <div className="kpi-label"><AlertTriangle size={16} /> Critical Zones</div>
          <div className="kpi-value" style={{ color: 'var(--critical-light)' }}>
            {criticalZones}
          </div>
          <div className="kpi-sub">CIS ≥ 75 — Immediate action needed</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label"><Shield size={16} /> Enforcement Rate</div>
          <div className="kpi-value" style={{ color: 'var(--low-light)' }}>
            {overview?.enforcement_coverage_pct || 0}%
          </div>
          <div className="kpi-sub">Violations processed by SCITA</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label"><Clock size={16} /> Peak Hour</div>
          <div className="kpi-value" style={{ color: 'var(--moderate-light)' }}>
            {overview?.peak_hour_ist != null ? `${overview.peak_hour_ist}:00` : '—'}
          </div>
          <div className="kpi-sub">IST — Highest violation frequency</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label"><Building2 size={16} /> Stations</div>
          <div className="kpi-value" style={{ color: 'var(--text-primary)' }}>
            {overview?.station_count || 0}
          </div>
          <div className="kpi-sub">Active police stations</div>
        </div>
      </div>

      {/* Map + Hotspot Ranking */}
      <div className="map-section">
        <div className="map-container" id="dashboard-map">
          {/* Map Controls */}
          <div style={{ position: 'absolute', top: 10, right: 10, zIndex: 1000, background: 'var(--bg-surface)', padding: '6px', borderRadius: '6px', border: '1px solid var(--border)' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', cursor: 'pointer' }}>
              <input type="checkbox" checked={showHeatmap} onChange={(e) => setShowHeatmap(e.target.checked)} />
              Show Heatmap Layer
            </label>
          </div>
          {hotspots.length > 0 ? (
            <HotspotMap
              hotspots={hotspots}
              selectedHotspot={selectedHotspot}
              onHotspotClick={(h) => setSelectedHotspot(h)}
              showHeatmap={showHeatmap}
            />
          ) : (
            <div className="loading-container" style={{ background: 'var(--bg-secondary)' }}>
              <MapPin size={48} style={{ opacity: 0.3 }} />
              <p className="loading-text">No hotspot data available. Run the ML pipeline first.</p>
            </div>
          )}
        </div>

        {/* Hotspot Ranking Panel */}
        <div className="card">
          <div className="card-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            Top Hotspots
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', color: 'var(--text-primary)', fontSize: '12px', padding: '2px 6px', borderRadius: '4px' }}
            >
              <option value="cis">Highest CIS</option>
              <option value="violations">Most Violations</option>
            </select>
          </div>
          <div className="hotspot-panel">
            {[...hotspots]
              .sort((a, b) => sortBy === 'cis' ? b.congestion_impact_score - a.congestion_impact_score : b.violation_count - a.violation_count)
              .slice(0, 15)
              .map((h, i) => (
                <div
                  key={h.id || i}
                  className="hotspot-card"
                  onClick={() => setSelectedHotspot(h)}
                  style={selectedHotspot?.id === h.id ? { borderColor: 'var(--primary)' } : {}}
                >
                  <div
                    className="hotspot-rank"
                    style={{
                      background: i < 3 ? 'var(--critical-glow)' : 'var(--bg-surface-hover)',
                      color: i < 3 ? 'var(--critical-light)' : 'var(--text-secondary)',
                    }}
                  >
                    {i + 1}
                  </div>
                  <div className="hotspot-info">
                    <div className="location" title={h.location_label}>
                      {h.location_label || `Cluster ${h.cluster_label}`}
                    </div>
                    <div className="meta">
                      <span className={`cis-badge ${h.cis_tier}`}>
                        {h.cis_tier?.toUpperCase()}
                      </span>
                      <span>CIS {h.congestion_impact_score}</span>
                      <span>{h.violation_count} viols</span>
                    </div>
                  </div>
                </div>
              ))}
            {hotspots.length === 0 && (
              <div className="empty-state">
                <p>No hotspots detected yet</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Charts Row 1: Temporal */}
      <div className="charts-grid">
        {/* Hourly Distribution */}
        <div className="chart-card">
          <h3>Hourly Violation Pattern (IST)</h3>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={hourly}>
              <defs>
                <linearGradient id="hourlyGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(75,85,99,0.2)" />
              <XAxis
                dataKey="hour"
                tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                tickFormatter={(h) => `${h}:00`}
              />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
              <Tooltip  />
              <Area
                type="monotone"
                dataKey="count"
                name="Violations"
                stroke="#3b82f6"
                fill="url(#hourlyGrad)"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Daily Distribution */}
        <div className="chart-card">
          <h3>Day-of-Week Distribution</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={daily}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(75,85,99,0.2)" />
              <XAxis dataKey="name" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
              <Tooltip  />
              <Bar dataKey="count" name="Violations" radius={[4, 4, 0, 0]}>
                {daily.map((entry, i) => (
                  <Cell key={i} fill={CHART_COLORS[i%CHART_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Charts Row 2: Breakdowns */}
      <div className="charts-grid">
        {/* Violation Types */}
        <div className="chart-card">
          <h3>Top Violation Types</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={violTypes} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(75,85,99,0.2)" />
              <XAxis type="number" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
              <YAxis
                type="category"
                dataKey="type"
                width={160}
                tick={{ fill: '#9ca3af', fontSize: 11 }}
                tickFormatter={(v) => v.length > 22 ? v.slice(0, 22) + '…' : v}
              />
              <Tooltip  />
              <Bar dataKey="count" name="Count" radius={[0, 4, 4, 0]}>
                {violTypes.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Vehicle Types */}
        <div className="chart-card">
          <h3>Vehicle Type Distribution</h3>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={vehicleTypes}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                dataKey="count"
                nameKey="type"
                label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                labelLine={{ stroke: 'var(--text-muted)' }}
              >
                {vehicleTypes.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip  />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Monthly Trend */}
      <div className="charts-grid">
        <div className="chart-card" style={{ gridColumn: '1 / -1' }}>
          <h3>Monthly Violation Trend</h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={monthly}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(75,85,99,0.2)" />
              <XAxis dataKey="month" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
              <Tooltip  />
              <Line
                type="monotone"
                dataKey="count"
                name="Violations"
                stroke="#06b6d4"
                strokeWidth={2.5}
                dot={{ fill: '#06b6d4', r: 4, strokeWidth: 2, stroke: '#111827' }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
