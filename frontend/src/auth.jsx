import React, { createContext, useContext, useEffect, useState } from 'react';
import api from './api.js';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .get('/auth/me')
      .then((res) => setUser(res.data))
      .catch(() => localStorage.removeItem('token'))
      .finally(() => setLoading(false));
  }, []);

  const login = async (username, password) => {
    const params = new URLSearchParams();
    params.append('username', username);
    params.append('password', password);
    const res = await api.post('/auth/login', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    localStorage.setItem('token', res.data.access_token);
    setUser(res.data.user);
    return res.data.user;
  };

  const register = async (username, email, password) => {
    await api.post('/auth/register', { username, email, password });
    return login(username, password);
  };

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
  };

  const can = (...roles) => !!user && roles.includes(user.role);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, can }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
