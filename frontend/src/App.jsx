import React from 'react';
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import Navbar from './components/Navbar.jsx';
import { useAuth } from './auth.jsx';
import Login from './pages/Login.jsx';
import Register from './pages/Register.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Mentions from './pages/Mentions.jsx';
import Reports from './pages/Reports.jsx';
import Admin from './pages/Admin.jsx';

function Protected({ children, roles }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="center">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role))
    return <div className="center">403 — your role ({user.role}) cannot access this page.</div>;
  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <Shell />
    </BrowserRouter>
  );
}

function Shell() {
  const location = useLocation();
  return (
    <>
      <Navbar />
      <main className="container">
        <div className="page-anim" key={location.pathname}>
          <Routes location={location}>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/" element={<Protected><Dashboard /></Protected>} />
            <Route path="/mentions" element={<Protected><Mentions /></Protected>} />
            <Route path="/reports" element={<Protected><Reports /></Protected>} />
            <Route
              path="/admin"
              element={<Protected roles={['admin']}><Admin /></Protected>}
            />
          </Routes>
        </div>
      </main>
      <div className="footer">
        📊 Brand Sentiment Analyzer · Aggregation → Classification → Visualization → Reports
      </div>
    </>
  );
}
