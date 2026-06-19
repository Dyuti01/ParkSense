/**
 * ParkSense AI — Sidebar Component
 */

import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, MapPin, BarChart3, Building2,
  Shield, FileText, Database, ChevronLeft, ChevronRight,
  TrendingUp
} from 'lucide-react';
import { useState } from 'react';

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/hotspots', label: 'Hotspot Analysis', icon: MapPin },
  { path: '/temporal', label: 'Temporal Patterns', icon: TrendingUp },
  { path: '/stations', label: 'Station Intel', icon: Building2 },
  { path: '/enforcement', label: 'Enforcement', icon: Shield },
  { path: '/reports', label: 'Reports', icon: BarChart3 },
  { path: '/data', label: 'Data Management', icon: Database },
];

export default function Sidebar({ collapsed, onToggle }) {
  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      {/* Brand */}
      <div className="sidebar-brand">
        <div className="brand-icon">🅿️</div>
        <div className="brand-text">
          <h1>ParkSense</h1>
          <span>Bangalore Traffic Intel</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            end={item.path === '/'}
          >
            <item.icon />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Toggle */}
      <div className="sidebar-toggle">
        <button onClick={onToggle} title={collapsed ? 'Expand' : 'Collapse'}>
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>
    </aside>
  );
}
