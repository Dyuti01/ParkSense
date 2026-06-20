/**
 * ParkSense AI — Hotspot Analysis Page
 */

import { useState, useEffect } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Cell, RadialBarChart, RadialBar, Legend,
} from 'recharts';
import { useTheme } from '../context/ThemeContext';
import { AlertTriangle, Filter, MapPin, Zap } from 'lucide-react';
import { fetchHotspots, fetchHotspotSummary, fetchFilterOptions } from '../api';
import 'leaflet/dist/leaflet.css';

const TIER_COLORS = { critical: '#ef4444', high: '#f59e0b', moderate: '#06b6d4', low: '#10b981' };

export default function HotspotAnalysis() {
  const { theme } = useTheme();
  const [hotspots, setHotspots] = useState([]);
  const [summary, setSummary] = useState(null);
  const [filters, setFilters] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedTier, setSelectedTier] = useState('');
  const [selectedStation, setSelectedStation] = useState('');
  const [timeSlice, setTimeSlice] = useState('all');
  const [selectedHotspot, setSelectedHotspot] = useState(null);

  useEffect(() => {
    fetchFilterOptions().then(r => setFilters(r.data)).catch(() => {});
  }, []);

  useEffect(() => {
    loadData();
  }, [selectedTier, selectedStation, timeSlice]);

  async function loadData() {
    setLoading(true);
    try {
      const params = { time_slice: timeSlice, limit: 1000 };
      if (selectedTier) params.tier = selectedTier;
      if (selectedStation) params.station = selectedStation;

      const res = await fetchHotspots(params);
      setHotspots(res.data.hotspots || []);
    } catch (err) {
      console.error('Hotspot load error:', err);
    } finally {
      setLoading(false);
    }
  }

  // Dynamically calculate KPIs based on the filtered list of hotspots
  const dynamicSummary = {
    total_hotspots: hotspots.length,
    avg_cis: hotspots.length > 0 
      ? (hotspots.reduce((sum, h) => sum + h.congestion_impact_score, 0) / hotspots.length).toFixed(1) 
      : 0,
    max_cis: hotspots.length > 0 
      ? Math.max(...hotspots.map(h => h.congestion_impact_score)).toFixed(1) 
      : 0,
    total_violations: hotspots.reduce((sum, h) => sum + h.violation_count, 0),
    tier_breakdown: hotspots.reduce((acc, h) => {
      acc[h.cis_tier] = (acc[h.cis_tier] || 0) + 1;
      return acc;
    }, {})
  };

  const tierBreakdown = Object.entries(dynamicSummary.tier_breakdown).map(([tier, count]) => ({
    name: tier.charAt(0).toUpperCase() + tier.slice(1),
    value: count,
    fill: TIER_COLORS[tier] || '#6b7280',
  }));

  return (
    <div className="animate-in">
      <div className="page-header">
        <h2>Hotspot Analysis</h2>
        <p>DBSCAN-detected illegal parking clusters with Congestion Impact Scores</p>
      </div>

      {/* Filters */}
      <div className="filter-panel">
        <div className="filter-group">
          <label>Time Slice</label>
          <select value={timeSlice} onChange={(e) => setTimeSlice(e.target.value)}>
            <option value="all">All Hours</option>
            <option value="morning">Morning (6-12)</option>
            <option value="afternoon">Afternoon (12-18)</option>
            <option value="evening">Evening (18-24)</option>
            <option value="night">Night (0-6)</option>
          </select>
        </div>
        <div className="filter-group">
          <label>CIS Tier</label>
          <select value={selectedTier} onChange={(e) => setSelectedTier(e.target.value)}>
            <option value="">All Tiers</option>
            <option value="critical">Critical (75+)</option>
            <option value="high">High (50-75)</option>
            <option value="moderate">Moderate (25-50)</option>
            <option value="low">Low (0-25)</option>
          </select>
        </div>
        <div className="filter-group">
          <label>Station</label>
          <select value={selectedStation} onChange={(e) => setSelectedStation(e.target.value)}>
            <option value="">All Stations</option>
            {filters?.stations?.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Summary KPIs */}
      <div className="kpi-grid stagger-in">
        <div className="kpi-card">
          <div className="kpi-label"><MapPin size={16} /> Total Hotspots</div>
          <div className="kpi-value" style={{ color: 'var(--primary-light)' }}>
            {dynamicSummary.total_hotspots}
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label"><Zap size={16} /> Avg CIS</div>
          <div className="kpi-value" style={{ color: 'var(--high-light)' }}>
            {dynamicSummary.avg_cis}
          </div>
        </div>
        <div className="kpi-card critical">
          <div className="kpi-label"><AlertTriangle size={16} /> Max CIS</div>
          <div className="kpi-value" style={{ color: 'var(--critical-light)' }}>
            {dynamicSummary.max_cis}
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label"><Filter size={16} /> Violations in Hotspots</div>
          <div className="kpi-value" style={{ color: 'var(--moderate-light)' }}>
            {dynamicSummary.total_violations.toLocaleString()}
          </div>
        </div>
      </div>

      {/* Map + Details */}
      <div className="map-section">
        <div className="map-container">
          {loading ? (
            <div className="loading-container" style={{ background: 'var(--bg-secondary)' }}>
              <div className="loading-spinner"></div>
            </div>
          ) : (
            <MapContainer center={[12.97, 77.59]} zoom={12} style={{ height: '100%', width: '100%' }}>
              <TileLayer
                url={theme === 'dark' ? "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" : "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"}
                attribution='&copy; CARTO'
              />
              {hotspots.map((h, i) => {
                const color = TIER_COLORS[h.cis_tier] || '#6b7280';
                return (
                  <CircleMarker
                    key={h.id || i}
                    center={[h.centroid_lat, h.centroid_lon]}
                    radius={Math.max(6, Math.min(20, h.violation_count / 50))}
                    pathOptions={{ fillColor: color, fillOpacity: 0.6, color, weight: 2, opacity: 0.8 }}
                    eventHandlers={{ click: () => setSelectedHotspot(h) }}
                  >
                    <Popup>
                      <div style={{ minWidth: 200 }}>
                        <h4 style={{ marginBottom: 6 }}>{h.location_label}</h4>
                        <span className={`cis-badge ${h.cis_tier}`}>CIS {h.congestion_impact_score}</span>
                        <p style={{ fontSize: 12, color: '#9ca3af', marginTop: 6 }}>
                          {h.violation_count} violations • {h.dominant_violation}
                        </p>
                      </div>
                    </Popup>
                  </CircleMarker>
                );
              })}
            </MapContainer>
          )}
        </div>

        {/* Selected Hotspot Detail */}
        <div className="card">
          <div className="card-title">
            {selectedHotspot ? 'Hotspot Detail' : 'Select a Hotspot'}
          </div>
          {selectedHotspot ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <h3 style={{ fontSize: '15px', fontWeight: 600 }}>{selectedHotspot.location_label}</h3>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <span className={`cis-badge ${selectedHotspot.cis_tier}`}>
                  CIS {selectedHotspot.congestion_impact_score}
                </span>
                <span className="cis-badge low">
                  Priority {selectedHotspot.priority_score}
                </span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '13px' }}>
                <div><span style={{ color: 'var(--text-muted)' }}>Violations:</span> {selectedHotspot.violation_count}</div>
                <div><span style={{ color: 'var(--text-muted)' }}>Radius:</span> {selectedHotspot.radius_meters}m</div>
                <div><span style={{ color: 'var(--text-muted)' }}>Peak Hour:</span> {selectedHotspot.peak_hour}:00</div>
                <div><span style={{ color: 'var(--text-muted)' }}>Days:</span> {selectedHotspot.unique_days}</div>
                <div style={{ gridColumn: '1/-1' }}><span style={{ color: 'var(--text-muted)' }}>Dominant:</span> {selectedHotspot.dominant_violation}</div>
                <div style={{ gridColumn: '1/-1' }}><span style={{ color: 'var(--text-muted)' }}>Vehicle:</span> {selectedHotspot.dominant_vehicle}</div>
                <div style={{ gridColumn: '1/-1' }}><span style={{ color: 'var(--text-muted)' }}>Station:</span> {selectedHotspot.police_station}</div>
              </div>

              {/* Hourly mini chart */}
              {selectedHotspot.hourly_distribution && (
                <div style={{ marginTop: '8px' }}>
                  <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>Hourly Pattern</p>
                  <ResponsiveContainer width="100%" height={100}>
                    <BarChart data={selectedHotspot.hourly_distribution.map((c, h) => ({ hour: h, count: c }))}>
                      <Bar dataKey="count" fill="var(--primary)" radius={[2, 2, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          ) : (
            <div className="empty-state" style={{ padding: '40px 20px' }}>
              <MapPin size={32} style={{ opacity: 0.3 }} />
              <p style={{ fontSize: '13px', marginTop: '12px' }}>Click a hotspot on the map to view details</p>
            </div>
          )}
        </div>
      </div>

      {/* Tier Breakdown & Table */}
      <div className="charts-grid">
        <div className="chart-card">
          <h3>CIS Tier Distribution</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={tierBreakdown}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(75,85,99,0.2)" />
              <XAxis dataKey="name" tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="value" name="Hotspots" radius={[4, 4, 0, 0]}>
                {tierBreakdown.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3>Hotspot Rankings</h3>
          <div style={{ maxHeight: '250px', overflowY: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Location</th>
                  <th>CIS</th>
                  <th>Violations</th>
                  <th>Tier</th>
                </tr>
              </thead>
              <tbody>
                {hotspots.slice(0, 20).map((h, i) => (
                  <tr key={h.id || i} onClick={() => setSelectedHotspot(h)} style={{ cursor: 'pointer' }}>
                    <td style={{ fontWeight: 700 }}>{i + 1}</td>
                    <td style={{ maxWidth: '160px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {h.location_label}
                    </td>
                    <td style={{ fontWeight: 600 }}>{h.congestion_impact_score}</td>
                    <td>{h.violation_count}</td>
                    <td><span className={`cis-badge ${h.cis_tier}`}>{h.cis_tier}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
