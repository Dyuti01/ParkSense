/**
 * ParkSense AI — Enforcement Priorities Page
 */

import { useState, useEffect } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { Shield, Target, Clock, AlertTriangle, MapPin } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { fetchEnforcementPriorities, fetchResourceAllocation, fetchFilterOptions } from '../api';
import 'leaflet/dist/leaflet.css';

const TIER_COLORS = { critical: '#ef4444', high: '#f59e0b', moderate: '#06b6d4', low: '#10b981' };

export default function EnforcementPriorities() {
  const { theme } = useTheme();
  const [priorities, setPriorities] = useState([]);
  const [allocation, setAllocation] = useState(null);
  const [station, setStation] = useState('');
  const [stations, setStations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedPriority, setSelectedPriority] = useState(null);

  useEffect(() => {
    fetchFilterOptions().then(r => setStations(r.data.stations || [])).catch(() => {});
  }, []);

  useEffect(() => {
    loadData();
  }, [station]);

  async function loadData() {
    setLoading(true);
    try {
      const params = { n: 50 };
      if (station) params.station = station;
      const [pr, al] = await Promise.all([
        fetchEnforcementPriorities(params),
        fetchResourceAllocation(),
      ]);
      setPriorities(pr.data.priorities || []);
      setAllocation(al.data);
    } catch (err) {
      console.error('Enforcement load error:', err);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p className="loading-text">Computing enforcement priorities...</p>
      </div>
    );
  }

  return (
    <div className="animate-in">
      <div className="page-header">
        <h2>Enforcement Priorities</h2>
        <p>AI-ranked targets for patrol deployment based on CIS, recurrence, and enforcement gaps</p>
      </div>

      <div className="filter-panel">
        <div className="filter-group">
          <label>Station</label>
          <select value={station} onChange={(e) => setStation(e.target.value)}>
            <option value="">All Stations</option>
            {stations.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Map + Priority List */}
      <div className="map-section">
        <div className="map-container">
          <MapContainer center={[12.97, 77.59]} zoom={12} style={{ height: '100%', width: '100%' }}>
            <TileLayer
              url={theme === 'dark' ? "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" : "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"}
              attribution='&copy; CARTO'
            />
            {priorities.map((p, i) => {
              const color = TIER_COLORS[p.cis_tier] || '#6b7280';
              return (
                <CircleMarker
                  key={p.hotspot_id || i}
                  center={[p.centroid_lat, p.centroid_lon]}
                  radius={Math.max(8, 18 - i * 0.3)}
                  pathOptions={{ fillColor: color, fillOpacity: 0.7, color, weight: 2, opacity: 0.9 }}
                  eventHandlers={{ click: () => setSelectedPriority(p) }}
                >
                  <Popup>
                    <div style={{ minWidth: 220 }}>
                      <h4 style={{ marginBottom: 4 }}>#{p.rank} — {p.location}</h4>
                      <div style={{ display: 'flex', gap: 6, marginBottom: 6, flexWrap: 'wrap' }}>
                        <span className={`cis-badge ${p.cis_tier}`}>CIS {p.congestion_impact_score}</span>
                        <span className="cis-badge moderate">Priority {p.priority_score}</span>
                      </div>
                      <p style={{ fontSize: 12, color: '#9ca3af' }}>
                        🕐 Patrol: {p.recommended_patrol?.time_range}<br/>
                        📍 {p.dominant_violation}<br/>
                        🚗 Focus: {p.dominant_vehicle}
                      </p>
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}
          </MapContainer>
        </div>

        {/* Priority Ranking */}
        <div className="card">
          <div className="card-title">Priority Rankings</div>
          <div className="hotspot-panel">
            {priorities.slice(0, 15).map((p) => (
              <div
                key={p.rank}
                className="hotspot-card"
                onClick={() => setSelectedPriority(p)}
                style={selectedPriority?.rank === p.rank ? { borderColor: 'var(--primary)' } : {}}
              >
                <div
                  className="hotspot-rank"
                  style={{
                    background: p.rank <= 3 ? 'var(--critical-glow)' : p.rank <= 10 ? 'var(--high-glow)' : 'var(--bg-surface-hover)',
                    color: p.rank <= 3 ? 'var(--critical-light)' : p.rank <= 10 ? 'var(--high-light)' : 'var(--text-secondary)',
                  }}
                >
                  {p.rank}
                </div>
                <div className="hotspot-info">
                  <div className="location" title={p.location}>{p.location}</div>
                  <div className="meta">
                    <span className={`cis-badge ${p.cis_tier}`}>{p.cis_tier}</span>
                    <span>🕐 {p.recommended_patrol?.time_range?.split(' - ')[0]}</span>
                    <span>{p.violation_count} viols</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Selected Priority Detail */}
      {selectedPriority && (
        <div className="card" style={{ marginBottom: '24px' }}>
          <div className="card-title">Patrol Recommendation — #{selectedPriority.rank}</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
            <div>
              <p style={{ color: 'var(--text-muted)', fontSize: '12px', marginBottom: '4px' }}>Location</p>
              <p style={{ fontWeight: 600 }}>{selectedPriority.location}</p>
            </div>
            <div>
              <p style={{ color: 'var(--text-muted)', fontSize: '12px', marginBottom: '4px' }}>Patrol Window</p>
              <p style={{ fontWeight: 600, color: 'var(--primary-light)' }}>{selectedPriority.recommended_patrol?.time_range}</p>
            </div>
            <div>
              <p style={{ color: 'var(--text-muted)', fontSize: '12px', marginBottom: '4px' }}>What to Look For</p>
              <p style={{ fontWeight: 600 }}>{selectedPriority.recommended_patrol?.what_to_look_for}</p>
            </div>
            <div>
              <p style={{ color: 'var(--text-muted)', fontSize: '12px', marginBottom: '4px' }}>Vehicle Focus</p>
              <p style={{ fontWeight: 600 }}>{selectedPriority.recommended_patrol?.vehicle_focus}</p>
            </div>
            <div>
              <p style={{ color: 'var(--text-muted)', fontSize: '12px', marginBottom: '4px' }}>Enforcement Gap</p>
              <p style={{ fontWeight: 600, color: 'var(--critical-light)' }}>{selectedPriority.enforcement_gap}%</p>
            </div>
            <div>
              <p style={{ color: 'var(--text-muted)', fontSize: '12px', marginBottom: '4px' }}>Station</p>
              <p style={{ fontWeight: 600 }}>{selectedPriority.police_station}</p>
            </div>
          </div>
        </div>
      )}

      {/* Resource Allocation */}
      {allocation?.allocations && (
        <div className="chart-card">
          <h3>Recommended Resource Allocation</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={allocation.allocations.slice(0, 15)}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(75,85,99,0.2)" />
              <XAxis dataKey="station" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} angle={-35} textAnchor="end" height={80}
                tickFormatter={(v) => v.length > 12 ? v.slice(0, 12) + '…' : v} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="recommended_units" name="Units" radius={[4, 4, 0, 0]}>
                {allocation.allocations.slice(0, 15).map((_, i) => (
                  <Cell key={i} fill={i < 3 ? '#ef4444' : i < 7 ? '#f59e0b' : '#3b82f6'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
