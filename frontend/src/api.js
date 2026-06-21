/**
 * ParkSense AI — API Client
 * Axios instance configured for the FastAPI backend.
 */

import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000`;

const api = axios.create({
  baseURL: `${API_BASE}/api`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: attach JWT token if available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('parksense_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: handle errors gracefully
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('parksense_token');
      localStorage.removeItem('parksense_user');
    }
    return Promise.reject(error);
  }
);

// ── API Functions ────────────────────────────────────────────

// Overview
export const fetchOverview = () => api.get('/overview');
export const fetchTrends = () => api.get('/overview/trends');

// Violations
export const fetchViolations = (params) => api.get('/violations', { params });
export const fetchHeatmapData = (timeSlice = 'all') => api.get('/violations/heatmap', { params: { time_slice: timeSlice } });
export const fetchSamplePoints = (params) => api.get('/violations/sample', { params });
export const fetchViolationTypes = (station) => api.get('/violations/types', { params: { station } });
export const fetchVehicleTypes = (station) => api.get('/violations/vehicles', { params: { station } });
export const fetchFilterOptions = () => api.get('/violations/filters');

// Hotspots
export const fetchHotspots = (params) => api.get('/hotspots', { params });
export const fetchTopHotspots = (n = 20, timeSlice = 'all') => api.get('/hotspots/top', { params: { n, time_slice: timeSlice } });
export const fetchHotspotSummary = (timeSlice = 'all') => api.get('/hotspots/summary', { params: { time_slice: timeSlice } });
export const fetchHotspotDetail = (id) => api.get(`/hotspots/${id}`);
export const fetchNearbyHotspots = (lat, lon, radius = 1000) => api.get('/hotspots/nearby', { params: { lat, lon, radius } });

// Temporal
export const fetchHourlyDistribution = (station) => api.get('/temporal/hourly', { params: { station } });
export const fetchDailyDistribution = (station) => api.get('/temporal/daily', { params: { station } });
export const fetchMonthlyTrend = (station) => api.get('/temporal/monthly', { params: { station } });
export const fetchHeatmapMatrix = (station) => api.get('/temporal/heatmap-matrix', { params: { station } });

// Stations
export const fetchStations = (sortBy = 'total_violations') => api.get('/stations', { params: { sort_by: sortBy } });
export const fetchStationDetail = (name) => api.get(`/stations/${encodeURIComponent(name)}`);
export const compareStations = (stations) => api.get('/stations/compare', { params: { stations } });

// Enforcement
export const fetchEnforcementPriorities = (params) => api.get('/enforcement/priorities', { params });
export const fetchEnforcementGaps = () => api.get('/enforcement/gaps');
export const fetchPatrolPlan = (station) => api.get(`/enforcement/patrol-plan/${encodeURIComponent(station)}`);
export const fetchResourceAllocation = () => api.get('/enforcement/resource-allocation');

// Ingestion
export const uploadCSV = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/ingest/csv', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
};
export const triggerRecompute = () => api.post('/ingest/recompute');
export const fetchIngestionHistory = () => api.get('/ingest/history');
export const deletePipelineRun = (id) => api.delete(`/ingest/history/${id}`);

// Export
export const fetchReportData = () => api.get('/export/report');
export const downloadCSVExport = (params) => api.get('/export/csv', { params, responseType: 'blob' });

// Auth
export const login = (username, password) => {
  const formData = new URLSearchParams();
  formData.append('username', username);
  formData.append('password', password);
  return api.post('/auth/login', formData, { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } });
};
export const register = (data) => api.post('/auth/register', data);
export const fetchMe = () => api.get('/auth/me');

export default api;
