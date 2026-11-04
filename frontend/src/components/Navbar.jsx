import React, { useEffect, useState } from 'react';
import { NavLink, Link, useNavigate } from 'react-router-dom';
import api from '../api.js';
import { useAuth } from '../auth.jsx';

const linkCls = ({ isActive }) => (isActive ? 'active' : undefined);

export default function Navbar() {
  const { user, logout } = useAuth();
  const [cfg, setCfg] = useState({ brand: 'Brand' });
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');
  const navigate = useNavigate();

  useEffect(() => {
    api.get('/config').then((r) => setCfg(r.data)).catch(() => {});
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem('theme', theme);
  }, [theme]);

  return (
    <nav className="navbar">
      <Link to="/" className="brand">
        <span className="logo-dot" />
        📊 Brand Sentiment Analyzer
      </Link>
      {user && (
        <div className="links">
          <NavLink to="/" end className={linkCls}>Dashboard</NavLink>
          <NavLink to="/mentions" className={linkCls}>Mentions</NavLink>
          <NavLink to="/reports" className={linkCls}>Reports</NavLink>
          {user.role === 'admin' && <NavLink to="/admin" className={linkCls}>Admin</NavLink>}
        </div>
      )}
      {cfg.model_accuracy && (
        <span className="model-chip" title={`Trained on ${Number(cfg.model_samples || 0).toLocaleString()} real tweets (${cfg.model_source})`}>
          🤖 model {Math.round(cfg.model_accuracy * 100)}% acc
        </span>
      )}
      <div className="userbox">
        {user ? (
          <>
            <span className="muted" style={{ color: 'var(--muted)' }}>{user.username}</span>
            <span className={`role role-${user.role}`}>{user.role}</span>
            <button
              className="theme-toggle"
              title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            >
              {theme === 'dark' ? '🌙' : '☀️'}
            </button>
            <button className="btn small" onClick={() => { logout(); navigate('/login'); }}>
              Logout
            </button>
          </>
        ) : (
          <>
            <button
              className="theme-toggle"
              title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            >
              {theme === 'dark' ? '🌙' : '☀️'}
            </button>
            <Link to="/login">Login</Link>
            <Link to="/register">Register</Link>
          </>
        )}
      </div>
    </nav>
  );
}
