import React, { createContext, useContext, useState, useEffect } from 'react';
import { login, fetchMe } from '../api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is logged in
    const initAuth = async () => {
      const token = localStorage.getItem('parksense_token');
      if (token) {
        try {
          const res = await fetchMe();
          setUser(res.data);
        } catch (err) {
          localStorage.removeItem('parksense_token');
        }
      }
      setLoading(false);
    };
    initAuth();
  }, []);

  const handleLogin = async (username, password) => {
    const res = await login(username, password);
    const { access_token } = res.data;
    localStorage.setItem('parksense_token', access_token);
    const meRes = await fetchMe();
    setUser(meRes.data);
  };

  const handleLogout = () => {
    localStorage.removeItem('parksense_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login: handleLogin, logout: handleLogout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
