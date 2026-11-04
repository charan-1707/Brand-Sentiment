import React, { useEffect, useState } from 'react';
import api from '../api.js';

export default function Admin() {
  const [users, setUsers] = useState([]);
  const [model, setModel] = useState(null);
  const [sched, setSched] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);
  const [liveBrand, setLiveBrand] = useState('');
  const [liveLimit, setLiveLimit] = useState(25);

  const refresh = () => {
    api.get('/auth/users').then((r) => setUsers(r.data)).catch(() => {});
    api.get('/admin/model').then((r) => setModel(r.data)).catch(() => {});
    api.get('/admin/ingest/status').then((r) => setSched(r.data)).catch(() => {});
    api.get('/admin/ingest/jobs').then((r) => setJobs(r.data)).catch(() => {});
  };

  useEffect(() => {
    refresh();
  }, []);

  const act = async (fn, label) => {
    setBusy(true);
    setMsg('');
    try {
      const r = await fn();
      setMsg(`${label}: ${r.data.msg || JSON.stringify(r.data)}`);
    } catch (err) {
      setMsg(`${label} failed: ${err.response?.data?.detail || err.message}`);
    }
    setBusy(false);
    refresh();
  };

  const setRole = (id, role) =>
    act(() => api.patch(`/auth/users/${id}/role`, { role }), `Role updated to ${role}`);

  const setActive = (id, is_active) =>
    act(() => api.patch(`/auth/users/${id}/active`, { is_active }),
      is_active ? 'User activated' : 'User deactivated');

  const retrain = async (e) => {
    const file = e.target.files[0];
    const form = new FormData();
    if (file) form.append('file', file);
    await act(() => api.post('/admin/retrain', form), 'Retrain complete');
    e.target.value = '';
  };

  const pullLive = () =>
    act(
      () => api.post('/admin/ingest/real', null, {
        params: {
          ...(liveBrand.trim() ? { brand: liveBrand.trim() } : {}),
          limit_each: liveLimit,
        },
      }),
      'Live pull complete'
    );

  const wipeAll = async () => {
    if (!window.confirm('Wipe ALL mentions, jobs and reports?\nUsers and the trained model are kept. This cannot be undone.')) return;
    await act(() => api.post('/admin/reset'), 'Clean slate');
  };

  return (
    <div>
      <div className="page-head">
        <div>
          <h2>Admin Control Center</h2>
          <p className="page-sub">Users, the production model, ingestion scheduler and live pulls</p>
        </div>
      </div>
      {msg && <div className="success" style={{ overflowWrap: 'anywhere' }}>{msg}</div>}

      <div className="card">
        <h3>Users & roles</h3>
        <table className="table">
          <thead><tr><th>Username</th><th>Email</th><th>Role</th><th>Active</th><th>Actions</th></tr></thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.username}</td>
                <td>{u.email}</td>
                <td><span className={`role role-${u.role}`}>{u.role}</span></td>
                <td>{u.is_active ? 'yes' : 'no'}</td>
                <td>
                  <select value={u.role} onChange={(e) => setRole(u.id, e.target.value)} disabled={busy}>
                    <option value="viewer">viewer</option>
                    <option value="manager">manager</option>
                    <option value="admin">admin</option>
                  </select>{' '}
                  <button className="btn small ghost" disabled={busy} onClick={() => setActive(u.id, !u.is_active)}>
                    {u.is_active ? 'Deactivate' : 'Activate'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="grid2">
        <div className="card">
          <h3>Sentiment model <span className="card-chip">production</span></h3>
          {model ? (
            <div className="info-rows">
              <span className="k">Backend</span><span className="v"><b>{model.backend}</b></span>
              <span className="k">Loaded</span><span className="v">{model.loaded ? 'yes' : 'no (VADER fallback)'}</span>
              <span className="k">Accuracy</span><span className="v"><b>{model.accuracy != null ? `${Math.round(model.accuracy * 100)}%` : '—'}</b></span>
              <span className="k">Training data</span><span className="v">{model.source_file || '—'} ({Number(model.n_samples || 0).toLocaleString()} samples)</span>
              <span className="k">Trained at</span><span className="v">{model.trained_at || '—'}</span>
              <span className="k">Features</span><span className="v">{model.n_features ?? '—'}</span>
              <span className="k">Classes</span><span className="v">{(model.classes || []).join(', ')}</span>
              <span className="k">Neutral th.</span><span className="v">{model.neutral_threshold ?? '—'}</span>
            </div>
          ) : <p className="meta">Loading…</p>}
          <p className="meta" style={{ marginTop: 12 }}>Retrain on bundled data, or upload the Kaggle Twitter Sentiment CSV.</p>
          <input type="file" accept=".csv" onChange={retrain} disabled={busy} />
          <div style={{ marginTop: 10 }}>
            <button className="btn small" disabled={busy}
              onClick={() => act(() => api.post('/admin/retrain', new FormData()), 'Retrain complete')}>
              Retrain on bundled dataset
            </button>
          </div>
        </div>

        <div className="card">
          <h3>Scheduled ingestion <span className="card-chip">background job</span></h3>
          {sched ? (
            <>
              <div className="info-rows" style={{ marginBottom: 10 }}>
                <span className="k">State</span>
                <span className="v">
                  <span className={`status-pill ${sched.running ? 'live' : 'stopped'}`}>
                    <span className="sp-dot" /> {sched.running ? sched.state : 'stopped'}
                  </span>
                </span>
                <span className="k">Interval</span><span className="v">every {sched.interval_minutes} min</span>
                <span className="k">Batch size</span><span className="v">{sched.batch_size} mentions</span>
                <span className="k">Next run</span><span className="v">{sched.next_run || '—'}</span>
              </div>
            </>
          ) : <p className="meta">Loading…</p>}
          <div className="toolbar" style={{ marginTop: 8 }}>
            <button className="btn small" disabled={busy} onClick={() => act(() => api.post('/admin/ingest/trigger', null, { params: { batch: 8 } }), 'Ingestion triggered')}>Run now</button>
            <button className="btn small" disabled={busy} onClick={() => act(() => api.post('/admin/seed-demo'), 'Demo data seeded')}>Seed 150 demo mentions</button>
            <button className="btn small ghost" disabled={busy} onClick={() => act(() => api.post('/admin/ingest/pause'), 'Scheduler')}>Pause</button>
            <button className="btn small ghost" disabled={busy} onClick={() => act(() => api.post('/admin/ingest/resume'), 'Scheduler')}>Resume</button>
          </div>
        </div>
      </div>

      <div className="card">
        <h3>🌍 Pull REAL live mentions <span className="card-chip">5 public sources</span></h3>
        <p className="meta">
          Fetches live posts from HackerNews, Reddit, Mastodon, Bluesky and News, classifies them
          with the production model and stores them. Use a <b>real brand name</b> (e.g. Samsung, iPhone)
          — the fictional demo brand returns zero rows.
        </p>
        <div className="form-row">
          <input placeholder="Brand (blank = server default)" value={liveBrand} onChange={(e) => setLiveBrand(e.target.value)} />
          <select value={liveLimit} onChange={(e) => setLiveLimit(Number(e.target.value))}>
            <option value={10}>10 per source</option>
            <option value={25}>25 per source</option>
            <option value={50}>50 per source</option>
          </select>
          <button className="btn" disabled={busy} onClick={pullLive}>
            {busy ? 'Pulling…' : 'Pull live data'}
          </button>
        </div>
      </div>

      <div className="card">
        <h3>Recent ingestion jobs</h3>
        <table className="table">
          <thead><tr><th>ID</th><th>Started</th><th>Status</th><th>Added</th><th>Message</th></tr></thead>
          <tbody>
            {jobs.map((j) => (
              <tr key={j.id}>
                <td>{j.id}</td>
                <td>{new Date(j.started_at).toLocaleString()}</td>
                <td>{j.status}</td>
                <td>{j.mentions_added}</td>
                <td>{j.message}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="card danger-card">
        <h3>🧹 Demo reset (danger zone)</h3>
        <p className="meta">
          Wipes every mention, ingestion job and generated report for a clean slate
          before a demo. Logins/roles and the trained model are kept.
          Tip: <b>Pause</b> the scheduler first if you want the dashboard to stay empty.
        </p>
        <button className="btn small danger" disabled={busy} onClick={wipeAll}>
          Wipe all demo data
        </button>
      </div>
    </div>
  );
}
