/**
 * ParkSense AI — Data Management Page
 */

import { useState, useEffect, useRef } from 'react';
import { Database, Upload, RefreshCw, Clock, CheckCircle, XCircle, AlertCircle, Trash2 } from 'lucide-react';
import { uploadCSV, triggerRecompute, fetchIngestionHistory, deletePipelineRun } from '../api';

const STATUS_ICONS = {
  completed: <CheckCircle size={16} style={{ color: 'var(--low-light)' }} />,
  failed: <XCircle size={16} style={{ color: 'var(--critical-light)' }} />,
  running: <RefreshCw size={16} style={{ color: 'var(--high-light)', animation: 'spin 1s linear infinite' }} />,
  queued: <Clock size={16} style={{ color: 'var(--text-muted)' }} />,
};

export default function DataManagement() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [recomputing, setRecomputing] = useState(false);
  const [uploadMessage, setUploadMessage] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    loadHistory();
  }, []);

  async function loadHistory() {
    try {
      const r = await fetchIngestionHistory();
      setHistory(r.data.runs || []);
    } catch (err) {
      console.error('History load error:', err);
    } finally {
      setLoading(false);
    }
  }

  async function handleUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadMessage(null);
    try {
      const r = await uploadCSV(file);
      setUploadMessage({ type: 'success', text: `✅ ${r.data.message} (Run ID: ${r.data.run_id})` });
      loadHistory();
    } catch (err) {
      setUploadMessage({ type: 'error', text: `❌ Upload failed: ${err.response?.data?.detail || err.message}` });
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }

  async function handleRecompute() {
    setRecomputing(true);
    try {
      const r = await triggerRecompute();
      setUploadMessage({ type: 'success', text: `✅ ${r.data.message} (Run ID: ${r.data.run_id})` });
      loadHistory();
    } catch (err) {
      setUploadMessage({ type: 'error', text: `❌ Recompute failed: ${err.response?.data?.detail || err.message}` });
    } finally {
      setRecomputing(false);
    }
  }

  async function handleDelete(id) {
    if (!window.confirm(`Are you sure you want to delete pipeline run ${id}?`)) return;
    try {
      await deletePipelineRun(id);
      loadHistory();
    } catch (err) {
      alert(`Failed to delete run: ${err.response?.data?.detail || err.message}`);
    }
  }

  return (
    <div className="animate-in">
      <div className="page-header">
        <h2>Data Management</h2>
        <p>Upload new violation data, trigger ML pipeline, and view run history</p>
      </div>

      {/* Action Cards */}
      <div className="kpi-grid" style={{ marginBottom: '24px' }}>
        <div className="card" style={{ cursor: 'pointer' }} onClick={() => fileInputRef.current?.click()}>
          <div style={{ textAlign: 'center', padding: '20px' }}>
            <Upload size={32} style={{ color: 'var(--primary-light)', marginBottom: '12px' }} />
            <h3 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '4px' }}>Upload CSV</h3>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              {uploading ? 'Uploading...' : 'Ingest new violation records'}
            </p>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            style={{ display: 'none' }}
            onChange={handleUpload}
          />
        </div>

        <div
          className="card"
          style={{ cursor: 'pointer', opacity: recomputing ? 0.6 : 1 }}
          onClick={!recomputing ? handleRecompute : undefined}
        >
          <div style={{ textAlign: 'center', padding: '20px' }}>
            <RefreshCw
              size={32}
              style={{
                color: 'var(--moderate-light)',
                marginBottom: '12px',
                animation: recomputing ? 'spin 1s linear infinite' : 'none',
              }}
            />
            <h3 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '4px' }}>Recompute</h3>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              {recomputing ? 'Processing...' : 'Re-run hotspot detection & scoring'}
            </p>
          </div>
        </div>

        <div className="card">
          <div style={{ textAlign: 'center', padding: '20px' }}>
            <Database size={32} style={{ color: 'var(--low-light)', marginBottom: '12px' }} />
            <h3 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '4px' }}>Pipeline Runs</h3>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              {history.length} total runs
            </p>
          </div>
        </div>
      </div>

      {/* Upload Message */}
      {uploadMessage && (
        <div
          className="card"
          style={{
            marginBottom: '24px',
            borderColor: uploadMessage.type === 'success' ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)',
            background: uploadMessage.type === 'success' ? 'rgba(16,185,129,0.05)' : 'rgba(239,68,68,0.05)',
          }}
        >
          <p style={{ fontSize: '14px' }}>{uploadMessage.text}</p>
        </div>
      )}

      {/* Pipeline Run History */}
      <div className="card">
        <div className="card-title">Pipeline Run History</div>
        {loading ? (
          <div className="loading-container" style={{ minHeight: '150px' }}>
            <div className="loading-spinner"></div>
          </div>
        ) : history.length === 0 ? (
          <div className="empty-state">
            <Database size={48} />
            <h3>No pipeline runs yet</h3>
            <p>Upload a CSV or run the initial load script to populate data.</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Records</th>
                  <th>Inserted</th>
                  <th>Hotspots</th>
                  <th>Started</th>
                  <th>Duration</th>
                  <th>Error</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {history.map((run) => {
                  const duration = run.started_at && run.completed_at
                    ? Math.round((new Date(run.completed_at) - new Date(run.started_at)) / 1000)
                    : null;
                  return (
                    <tr key={run.id}>
                      <td style={{ fontWeight: 600 }}>{run.id}</td>
                      <td>
                        <span style={{
                          padding: '2px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: 600,
                          background: run.run_type === 'full' ? 'rgba(59,130,246,0.1)' : 'rgba(6,182,212,0.1)',
                          color: run.run_type === 'full' ? 'var(--primary-light)' : 'var(--moderate-light)',
                        }}>
                          {run.run_type}
                        </span>
                      </td>
                      <td style={{ display: 'flex', alignItems: 'center', gap: '6px', height: '93px' }}>
                        {STATUS_ICONS[run.status]}
                        {run.status}
                      </td>
                      <td>{(run.records_processed || 0).toLocaleString()}</td>
                      <td>{(run.records_inserted || 0).toLocaleString()}</td>
                      <td>{run.hotspots_found || 0}</td>
                      <td style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                        {run.started_at ? new Date(run.started_at).toLocaleString() : '—'}
                      </td>
                      <td>{duration != null ? `${duration}s` : '—'}</td>
                      <td style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', color: 'var(--critical-light)' }}>
                        {run.error_message?.length > 50 ? run.error_message.substring(0, 100) + ' ...' : run.error_message || '—'}
                      </td>
                      <td>
                        <button
                          onClick={() => handleDelete(run.id)}
                          style={{
                            background: 'none', border: 'none', color: 'var(--text-muted)',
                            cursor: 'pointer', padding: '4px'
                          }}
                          title="Delete Run"
                        >
                          <Trash2 size={16} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
