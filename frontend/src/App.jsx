/**
 * ParkSense AI — Main Application
 * React + Vite SPA with dark command center theme.
 */

import { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import Dashboard from './pages/Dashboard';
import HotspotAnalysis from './pages/HotspotAnalysis';
import TemporalPatterns from './pages/TemporalPatterns';
import StationIntelligence from './pages/StationIntelligence';
import EnforcementPriorities from './pages/EnforcementPriorities';
import Reports from './pages/Reports';
import DataManagement from './pages/DataManagement';
import Login from './pages/Login';
import { AuthProvider, useAuth } from './context/AuthContext';
import './App.css';

const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  
  if (loading) {
    return <div className="loading-screen" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', backgroundColor: 'var(--bg-dark)', color: 'white' }}>Authenticating...</div>;
  }
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  return children;
};

import { ThemeProvider } from './context/ThemeContext';

const AppLayout = () => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(window.innerWidth <= 768);

  return (
    <div className="app-layout">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      <div className={`app-main ${sidebarCollapsed ? 'collapsed' : ''}`}>
        <Header 
          collapsed={sidebarCollapsed} 
          onMobileToggle={() => setSidebarCollapsed(!sidebarCollapsed)} 
        />
        <main className="app-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/hotspots" element={<HotspotAnalysis />} />
            <Route path="/temporal" element={<TemporalPatterns />} />
            <Route path="/stations" element={<StationIntelligence />} />
            <Route path="/enforcement" element={<EnforcementPriorities />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/data" element={<DataManagement />} />
          </Routes>
        </main>
      </div>
    </div>
  );
};

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/*" element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            } />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
