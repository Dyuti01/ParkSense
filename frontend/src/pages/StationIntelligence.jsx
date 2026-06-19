/**
 * ParkSense AI — Station Intelligence Page
 */

import { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Cell, PieChart, Pie, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
} from 'recharts';
import { Building2, MapPin, TrendingUp, TrendingDown, Minus, ArrowRight, X } from 'lucide-react';
import { fetchStations, fetchStationDetail } from '../api';
import { useNavigate } from 'react-router-dom';

const CHART_COLORS = ['#3b82f6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

export default function StationIntelligence() {
  const [stations, setStations] = useState([]);
  const [selectedStation, setSelectedStation] = useState(null);
  const [stationDetail, setStationDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState('total_violations');
  const navigate = useNavigate();

  useEffect(() => {
    fetchStations(sortBy)
      .then((r) => setStations(r.data.stations || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [sortBy]);

  useEffect(() => {
    if (selectedStation) {
      fetchStationDetail(selectedStation)
        .then((r) => setStationDetail(r.data))
        .catch(console.error);
    }
  }, [selectedStation]);

  const trendIcon = (dir) => {
    if (dir === 'increasing') return <TrendingUp size={14} style={{ color: 'var(--critical-light)' }} />;
    if (dir === 'decreasing') return <TrendingDown size={14} style={{ color: 'var(--low-light)' }} />;
    return <Minus size={14} style={{ color: 'var(--text-muted)' }} />;
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p className="loading-text">Loading station data...</p>
      </div>
    );
  }

  return (
    <div className="animate-in">
      <div className="page-header">
        <h2>Station Intelligence</h2>
        <p>Performance analytics and violation patterns per police station</p>
      </div>

      {/* Modal Overlay for Station Detail */}
      {stationDetail?.station && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'var(--overlay-bg)', backdropFilter: 'blur(6px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
          padding: '24px'
        }}>
          <div className="card animate-in" style={{
            maxWidth: '900px', width: '100%', maxHeight: '90vh', overflowY: 'auto',
            position: 'relative', padding: '24px'
          }}>
            <button
              onClick={() => { setSelectedStation(null); setStationDetail(null); }}
              style={{
                position: 'absolute', top: '16px', right: '16px',
                background: 'none', border: 'none', color: 'var(--text-muted)',
                cursor: 'pointer', padding: '8px', borderRadius: '50%'
              }}
            >
              <X size={24} />
            </button>
            <h2 style={{ marginBottom: '4px' }}>{stationDetail.station.police_station} Station</h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginBottom: '24px' }}>
              Detailed violation breakdown and analytics
            </p>

            <div className="charts-grid">
              <div className="chart-card">
                <h3>Top Violation Types</h3>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart
                    data={Object.entries(stationDetail.station.violation_breakdown || {}).slice(0, 8).map(([type, count]) => ({ type, count }))}
                    layout="vertical"
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(75,85,99,0.2)" />
                    <XAxis type="number" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                    <YAxis type="category" dataKey="type" width={150} tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                      tickFormatter={(v) => v.length > 20 ? v.slice(0, 20) + '…' : v} />
                    <Tooltip  />
                    <Bar color='#525b68ff' dataKey="count" name="Count" radius={[0, 4, 4, 0]}>
                      {Object.entries(stationDetail.station.violation_breakdown || {}).slice(0, 8).map((_, i) => (
                        <Cell key={i} fill={CHART_COLORS[i%CHART_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="chart-card">
                <h3>Vehicle Distribution</h3>
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={Object.entries(stationDetail.station.vehicle_breakdown || {}).slice(0, 6).map(([type, count]) => ({ name: type, value: count }))}
                      cx="50%" cy="50%" innerRadius={50} outerRadius={90} dataKey="value"
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      labelLine={{ stroke: 'var(--text-muted)' }}
                    >
                      {Object.entries(stationDetail.station.vehicle_breakdown || {}).slice(0, 6).map((_, i) => (
                        <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Sort Control */}
      <div className="filter-panel">
        <div className="filter-group">
          <label>Sort By</label>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
            <option value="total_violations">Total Violations</option>
            <option value="cis_avg">Avg CIS</option>
            <option value="critical_hotspots">Critical Hotspots</option>
            <option value="enforcement_rate">Enforcement Rate</option>
          </select>
        </div>
      </div>

      {/* Station Ranking Table */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div className="card-title">Station Rankings</div>
        <div style={{ overflowX: 'auto', overflowY: 'auto', maxHeight: '500px' }}>
          <table className="data-table">
            <thead style={{ position: 'sticky', top: 0, zIndex: 10, backgroundColor: 'var(--bg-glass, rgba(17, 24, 39, 0.85))', backdropFilter: 'blur(8px)', WebkitBackdropFilter: 'blur(8px)', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}>
              <tr>
                <th>#</th>
                <th>Station</th>
                <th>Violations</th>
                <th>Hotspots</th>
                <th>Critical</th>
                <th>Avg CIS</th>
                <th>Enforcement</th>
                <th>Peak Hour</th>
                <th>Trend</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {stations.map((s, i) => (
                <tr
                  key={s.police_station}
                  onClick={() => setSelectedStation(s.police_station)}
                  style={{
                    cursor: 'pointer',
                    background: selectedStation === s.police_station ? 'rgba(59,130,246,0.08)' : undefined,
                  }}
                >
                  <td style={{ fontWeight: 700, color: 'var(--text-muted)' }}>{i + 1}</td>
                  <td style={{ fontWeight: 600 }}>{s.police_station}</td>
                  <td>{s.total_violations.toLocaleString()}</td>
                  <td>{s.hotspot_count}</td>
                  <td>
                    {s.critical_hotspots > 0 ? (
                      <span style={{ color: 'var(--critical-light)', fontWeight: 600 }}>{s.critical_hotspots}</span>
                    ) : '—'}
                  </td>
                  <td>
                    <span style={{
                      color: s.cis_avg >= 50 ? 'var(--critical-light)' : s.cis_avg >= 25 ? 'var(--high-light)' : 'var(--low-light)',
                      fontWeight: 600,
                    }}>
                      {s.cis_avg}
                    </span>
                  </td>
                  <td>{s.enforcement_rate}%</td>
                  <td>{s.peak_hour != null ? `${s.peak_hour}:00` : '—'}</td>
                  <td style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    {trendIcon(s.trend_direction)}
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      {s.trend_percentage > 0 ? '+' : ''}{s.trend_percentage}%
                    </span>
                  </td>
                  <td><ArrowRight size={14} style={{ color: 'var(--text-muted)' }} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>


    </div>
  );
}
