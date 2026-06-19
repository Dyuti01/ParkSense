/**
 * ParkSense AI — Reports & Analytics Page
 */

import { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { FileText, Download, Lightbulb, TrendingUp, Building2, MapPin } from 'lucide-react';
import { fetchReportData, downloadCSVExport } from '../api';

const CHART_COLORS = ['#3b82f6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

export default function Reports() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    fetchReportData()
      .then((r) => setReport(r.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  async function handleDownload() {
    setDownloading(true);
    try {
      const response = await downloadCSVExport({});
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'parksense_violations_export.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download error:', err);
    } finally {
      setDownloading(false);
    }
  }

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p className="loading-text">Generating report...</p>
      </div>
    );
  }

  return (
    <div className="animate-in">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2>Reports & Analytics</h2>
          <p>Executive summary and data export</p>
        </div>
        <button className="btn btn-primary" onClick={handleDownload} disabled={downloading}>
          <Download size={16} />
          {downloading ? 'Exporting...' : 'Export CSV'}
        </button>
      </div>

      {/* KPIs */}
      <div className="kpi-grid stagger-in">
        <div className="kpi-card">
          <div className="kpi-label"><FileText size={16} /> Total Violations</div>
          <div className="kpi-value" style={{ color: 'var(--primary-light)' }}>
            {(report?.total_violations || 0).toLocaleString()}
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label"><Building2 size={16} /> Top Station</div>
          <div className="kpi-value" style={{ color: 'var(--high-light)', fontSize: '18px' }}>
            {report?.top_stations?.[0]?.name || '—'}
          </div>
          <div className="kpi-sub">{(report?.top_stations?.[0]?.count || 0).toLocaleString()} violations</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label"><MapPin size={16} /> Top Hotspot CIS</div>
          <div className="kpi-value" style={{ color: 'var(--critical-light)' }}>
            {report?.top_hotspots?.[0]?.cis || '—'}
          </div>
          <div className="kpi-sub" style={{ fontSize: '11px' }}>{report?.top_hotspots?.[0]?.location || ''}</div>
        </div>
      </div>

      {/* AI Insights */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div className="card-title"><Lightbulb size={14} style={{ marginRight: 6 }} />AI-Generated Insights</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {(report?.insights || []).map((insight, i) => (
            <div
              key={i}
              style={{
                background: 'var(--bg-surface)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-md)',
                padding: '14px 16px',
                fontSize: '13.5px',
                lineHeight: '1.6',
                display: 'flex',
                gap: '12px',
                alignItems: 'flex-start',
              }}
            >
              <span style={{ fontSize: '18px', flexShrink: 0 }}>💡</span>
              <span>{insight}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Charts */}
      <div className="charts-grid">
        {/* Top Stations */}
        <div className="chart-card">
          <h3>Top 5 Stations by Volume</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={report?.top_stations || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(75,85,99,0.2)" />
              <XAxis dataKey="name" tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                angle={-45} textAnchor="end" height={80} interval={0} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count" name="Violations" radius={[4, 4, 0, 0]}>
                {(report?.top_stations || []).map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Top Violation Types */}
        <div className="chart-card">
          <h3>Top Violation Types</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={(report?.violation_types || []).slice(0, 8)} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(75,85,99,0.2)" />
              <XAxis type="number" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
              <YAxis type="category" dataKey="type" width={160} tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                tickFormatter={(v) => v.length > 22 ? v.slice(0, 22) + '…' : v} />
              <Tooltip />
              <Bar dataKey="count" name="Count" radius={[0, 4, 4, 0]}>
                {(report?.violation_types || []).slice(0, 8).map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top Hotspots Table */}
      <div className="card">
        <div className="card-title">Top Congestion Impact Hotspots</div>
        <table className="data-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Location</th>
              <th>CIS Score</th>
              <th>Violations</th>
            </tr>
          </thead>
          <tbody>
            {(report?.top_hotspots || []).map((h, i) => (
              <tr key={i}>
                <td style={{ fontWeight: 700 }}>{i + 1}</td>
                <td>{h.location}</td>
                <td style={{ fontWeight: 600, color: h.cis >= 75 ? 'var(--critical-light)' : h.cis >= 50 ? 'var(--high-light)' : 'var(--primary-light)' }}>
                  {h.cis}
                </td>
                <td>{(h.count || 0).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
