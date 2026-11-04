import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { extractError } from '../api.js';
import { useAuth } from '../auth.jsx';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    try {
      await login(username, password);
      navigate('/');
    } catch (err) {
      setError(extractError(err, 'Login failed. Check your username and password.'));
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-grid">
        <div className="auth-aside">
          <h1>📊 Brand Sentiment Analyzer</h1>
          <p className="aside-sub">
            Collect, classify and visualize what the internet thinks about any product — automatically.
          </p>
          <div className="feature"><span className="f-ico">🤖</span> ML classified mentions (79.8% accuracy)</div>
          <div className="feature"><span className="f-ico">🌐</span> Live pulls from 5 public sources</div>
          <div className="feature"><span className="f-ico">📑</span> One-click PDF / CSV reports</div>
        </div>
        <div className="auth-wrap">
          <h2>Welcome back</h2>
          <p className="subtitle">Sign in to explore what people think about your product.</p>
          {error && <div className="error">{error}</div>}
          <form onSubmit={submit}>
            <label className="lbl">Username</label>
            <input value={username} onChange={(e) => setUsername(e.target.value)} required />
            <br /><br />
            <label className="lbl">Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            <br /><br />
            <button className="btn" type="submit" style={{ width: '100%' }}>Login →</button>
          </form>
          <p className="meta">No account? <Link to="/register">Register</Link></p>
        </div>
      </div>
    </div>
  );
}
