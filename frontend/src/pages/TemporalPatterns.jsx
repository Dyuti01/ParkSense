/**
 * ParkSense AI — Temporal Patterns Page
 */

import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area, Cell, LineChart, Line,
} from 'recharts';
import { Clock, Calendar, TrendingUp } from 'lucide-react';
import { fetchHourlyDistribution, fetchDailyDistribution, fetchMonthlyTrend, fetchHeatmapMatrix, fetchFilterOptions } from '../api';

const CHART_COLORS = ['#3b82f6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

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

export default function TemporalPatterns() {
  const [hourly, setHourly] = useState([]);
  const [daily, setDaily] = useState([]);
  const [monthly, setMonthly] = useState([]);
  const [heatmapMatrix, setHeatmapMatrix] = useState(null);
  const [station, setStation] = useState('');
  const [stations, setStations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCell, setSelectedCell] = useState(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  useEffect(() => {
    fetchFilterOptions().then(r => setStations(r.data.stations || [])).catch(() => {});
  }, []);

  useEffect(() => {
    loadData();
  }, [station]);

  async function loadData() {
    setLoading(true);
    try {
      const stationParam = station || undefined;
      const [hr, dy, mn, hm] = await Promise.all([
        fetchHourlyDistribution(stationParam),
        fetchDailyDistribution(stationParam),
        fetchMonthlyTrend(stationParam),
        fetchHeatmapMatrix(stationParam),
      ]);
      setHourly(hr.data.distribution || []);
      setDaily(dy.data.distribution || []);
      setMonthly(mn.data.trend || []);
      setHeatmapMatrix(hm.data);
    } catch (err) {
      console.error('Temporal load error:', err);
    } finally {
      setLoading(false);
    }
  }

  // Find the max value in the heatmap matrix for color scaling
  const matrixMax = heatmapMatrix?.matrix
    ? Math.max(...heatmapMatrix.matrix.flat())
    : 1;

  function getCellColor(value) {
    if (value === 0) return 'rgba(75, 85, 99, 0.1)';
    const intensity = Math.min(value / matrixMax, 1);
    if (intensity > 0.75) return `rgba(239, 68, 68, ${0.3 + intensity * 0.7})`;
    if (intensity > 0.5) return `rgba(245, 158, 11, ${0.3 + intensity * 0.7})`;
    if (intensity > 0.25) return `rgba(6, 182, 212, ${0.3 + intensity * 0.7})`;
    return `rgba(59, 130, 246, ${0.2 + intensity * 0.5})`;
  }

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p className="loading-text">Loading temporal patterns...</p>
      </div>
    );
  }

  return (
    <div className="animate-in">
      <div className="page-header">
        <h2>Temporal Patterns</h2>
        <p>When do parking violations peak? Hour × Day analysis across Bangalore</p>
      </div>

      {/* Station Filter */}
      <div className="filter-panel">
        <div className="filter-group">
          <label>Police Station</label>
          <select value={station} onChange={(e) => setStation(e.target.value)}>
            <option value="">All Stations</option>
            {stations.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Hourly & Daily */}
      <div className="charts-grid">
        <div className="chart-card">
          <h3><Clock size={16} style={{ marginRight: 6, verticalAlign: 'middle' }} />24-Hour Violation Profile</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={hourly}>
              <defs>
                <linearGradient id="hourGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(75,85,99,0.2)" />
              <XAxis dataKey="hour" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} tickFormatter={(h) => `${h}:00`} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="count" name="Violations" stroke="#3b82f6" fill="url(#hourGrad)" strokeWidth={2.5} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3><Calendar size={16} style={{ marginRight: 6, verticalAlign: 'middle' }} />Weekly Pattern</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={daily}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(75,85,99,0.2)" />
              <XAxis dataKey="name" tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="count" name="Violations" radius={[6, 6, 0, 0]}>
                {daily.map((entry, i) => (
                  <Cell key={i} fill={CHART_COLORS[i%CHART_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Hour × Day Heatmap */}
      {heatmapMatrix?.matrix && (
        <div className="chart-card" style={{ marginBottom: '24px' }}>
          <h3>Hour × Day Heatmap</h3>
          <div style={{ overflowX: 'auto', padding: '8px 0' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '80px repeat(24, 1fr)', gap: '2px', minWidth: '700px' }}>
              {/* Header row */}
              <div></div>
              {heatmapMatrix.hour_labels.map((h, i) => (
                <div key={i} style={{ fontSize: '10px', color: 'var(--text-muted)', textAlign: 'center', padding: '4px 0' }}>
                  {i % 3 === 0 ? h : ''}
                </div>
              ))}

              {/* Data rows */}
              {heatmapMatrix.day_labels.map((day, di) => (
                <>
                  <div key={`label-${di}`} style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', paddingRight: '8px' }}>
                    {day}
                  </div>
                  {heatmapMatrix.matrix[di].map((val, hi) => (
                    <div
                      key={`cell-${di}-${hi}`}
                      onMouseEnter={(e) => {
                        setSelectedCell({ day, hour: hi, count: val });
                        setTooltipPos({ x: e.clientX, y: e.clientY });
                      }}
                      onMouseMove={(e) => {
                        setTooltipPos({ x: e.clientX, y: e.clientY });
                      }}
                      onMouseLeave={() => setSelectedCell(null)}
                      style={{
                        background: getCellColor(val),
                        borderRadius: '3px',
                        minHeight: '28px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '9px',
                        color: val > matrixMax * 0.5 ? '#fff' : 'var(--text-primary)',
                        cursor: 'default',
                        transition: 'transform 0.15s ease, opacity 0.2s',
                        opacity: selectedCell ? (selectedCell.day === day && selectedCell.hour === hi ? 1 : 0.6) : 1,
                        border: selectedCell?.day === day && selectedCell?.hour === hi ? '1px solid #fff' : 'none',
                        transform: selectedCell?.day === day && selectedCell?.hour === hi ? 'scale(1.15)' : 'scale(1)',
                        zIndex: selectedCell?.day === day && selectedCell?.hour === hi ? 10 : 1
                      }}
                    >
                      {val > 0 ? val.toLocaleString() : ''}
                    </div>
                  ))}
                </>
              ))}
            </div>
          </div>
          <div style={{ display: 'flex', gap: '16px', marginTop: '12px', justifyContent: 'center', fontSize: '11px', color: 'var(--text-muted)' }}>
            <span>■ Low</span>
            <span style={{ color: '#3b82f6' }}>■ Moderate</span>
            <span style={{ color: '#06b6d4' }}>■ High</span>
            <span style={{ color: '#f59e0b' }}>■ Very High</span>
            <span style={{ color: '#ef4444' }}>■ Critical</span>
          </div>
        </div>
      )}

      {/* Floating Custom Tooltip */}
      {selectedCell && createPortal(
        <div className="recharts-default-tooltip" style={{
          position: 'fixed',
          top: tooltipPos.y + 15,
          left: tooltipPos.x + 15,
          padding: '10px 14px',
          pointerEvents: 'none',
          zIndex: 9999
        }}>
          <div className="recharts-tooltip-label">
            {selectedCell.day}s at {selectedCell.hour}:00 IST
          </div>
          <div className="recharts-tooltip-item" style={{ color: 'var(--primary-light)' }}>
            Violations: {selectedCell.count.toLocaleString()}
          </div>
        </div>,
        document.body
      )}

      {/* Monthly Trend */}
      <div className="chart-card">
        <h3><TrendingUp size={16} style={{ marginRight: 6, verticalAlign: 'middle' }} />Monthly Trend</h3>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={monthly}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(75,85,99,0.2)" />
            <XAxis dataKey="month" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
            <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
            <Tooltip content={<CustomTooltip />} />
            <Line
              type="monotone" dataKey="count" name="Violations"
              stroke="#06b6d4" strokeWidth={2.5}
              dot={{ fill: '#06b6d4', r: 5, strokeWidth: 2, stroke: 'var(--bg-surface)' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
