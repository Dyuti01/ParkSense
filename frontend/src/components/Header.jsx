/**
 * ParkSense AI — Header Component
 */

import { Menu, LogOut, Sun, Moon } from 'lucide-react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { useState, useEffect } from 'react';

const pageTitles = {
  '/': 'Command Center',
  '/hotspots': 'Hotspot Analysis',
  '/temporal': 'Temporal Patterns',
  '/stations': 'Station Intelligence',
  '/enforcement': 'Enforcement Priorities',
  '/reports': 'Reports & Analytics',
  '/data': 'Data Management',
};

export default function Header({ collapsed, onMobileToggle }) {
  const location = useLocation();
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const title = pageTitles[location.pathname] || 'ParkSense AI';

  const [isOnline, setIsOnline] = useState(navigator.onLine);

  useEffect(() => {
     const checkRealConnectivity = async () => {
      if (!navigator.onLine) {
        setIsOnline(false);
        return;
      }
     try {
        // Fetch a tiny asset with a cache-busting timestamp
        const response = await fetch(`https://google.com`, {
          method: 'HEAD', // HEAD requests download zero body content, saving data
          mode: 'no-cors', // Prevents CORS errors from blocking your status read
        });
        setIsOnline(true);
      } catch (error) {
        setIsOnline(false); // Fetch failed, meaning the network is down or captive
      }
    };

    // 2. Set up event listeners for instant local changes
    const handleOnline = () => checkRealConnectivity();
    const handleOffline = () => setIsOnline(false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // 3. Periodic polling (optional but recommended for silent drops)
    // const intervalId = setInterval(checkRealConnectivity, 10000); // Checks every 10 seconds

    // Initial check on component mount
    checkRealConnectivity();
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      // clearInterval(intervalId);
    };
  }, []);

  return (
    <header className={`app-header ${collapsed ? 'collapsed' : ''}`}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <button 
          className="mobile-menu-toggle" 
          onClick={onMobileToggle}
          style={{ background: 'none', border: 'none', color: 'var(--text-primary)', cursor: 'pointer', display: 'none' }}
        >
          <Menu size={24} />
        </button>
        <h1 className="header-title">{title}</h1>
      </div>
      <div className="header-right">
        <div className="pipeline-status" style={{ borderColor: isOnline ? 'var(--border-color)' : 'rgba(239, 68, 68, 0.3)' }}>
          <div className="status-dot" style={{ 
            background: isOnline ? 'var(--low)' : 'var(--critical)',
            animation: isOnline ? 'pulse-glow 2s infinite' : 'none',
            boxShadow: isOnline ? 'none' : '0 0 8px var(--critical-glow)'
          }}></div>
          <span style={{ color: isOnline ? 'var(--text-muted)' : 'var(--critical-light)' }}>
            {isOnline ? 'System Online' : 'System Offline'}
          </span>
        </div>
        <button 
          onClick={toggleTheme}
          title="Toggle Theme"
          style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            background: 'var(--bg-surface)', 
            border: '1px solid var(--border-color)', 
            color: 'var(--text-secondary)', 
            cursor: 'pointer', 
            width: '32px', 
            height: '32px', 
            borderRadius: '6px' 
          }}
        >
          {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
        </button>
        {user && (
          <button 
            onClick={logout}
            className="logout-button"
            title="Logout"
            style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'var(--bg-surface)', border: '1px solid var(--border-color)', color: 'var(--text-secondary)', cursor: 'pointer', padding: '6px 12px', borderRadius: '6px' }}
          >
            <LogOut size={14} />
            <span style={{ fontSize: '12px', fontWeight: '500' }}>Logout</span>
          </button>
        )}
      </div>
    </header>
  );
}
