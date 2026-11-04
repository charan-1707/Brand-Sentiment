import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { extractError } from '../api.js';
import { useAuth } from '../auth.jsx';

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: '', email: '', password: '' });
  const [error, setError] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    if (form.username.trim().length < 3) {
      setError('Username must be at least 3 characters.');
      return;
    }
    if (form.password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      setError('Please enter a valid email address.');
      return;
    }
    try {
      await register(form.username.trim(), form.email.trim(), form.password);
      navigate('/');
    } catch (err) {
      setError(extractError(err, 'Registration failed. Try a different username/email.'));
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-grid">
        <div className="auth-aside">
          <h1>📊 Brand Sentiment Analyzer</h1>
          <p className="aside-sub">
            Create an account to watch live sentiment analytics for any product.
          </p>
          <div className="feature"><span className="f-ico">👤</span> Viewer accounts can read everything</div>
          <div className="feature"><span className="f-ico">⭐</span> Admins can promote your role later</div>
          <div className="feature"><span className="f-ico">🔒</span> Passwords are hashed, tokens expire in 2h</div>
        </div>
        <div className="auth-wrap">
          <h2>Create account</h2>
          <p className="subtitle">You'll start with the <b>viewer</b> role — full read access.</p>
          {error && <div className="error">{error}</div>}
          <form onSubmit={submit}>
            <label className="lbl">Username</label>
            <input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} required />
            <br /><br />
            <label className="lbl">Email</label>
            <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
            <br /><br />
            <label className="lbl">Password</label>
            <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
            <br /><br />
            <button className="btn" type="submit" style={{ width: '100%' }}>Create account ⚡</button>
          </form>
          <p className="meta">Have an account? <Link to="/login">Login</Link></p>
        </div>
      </div>
    </div>
  );
}
