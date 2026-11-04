import React, { useEffect, useState } from 'react';
import api from '../api.js';
import { useAuth } from '../auth.jsx';

export default function Reports() {
  const { can } = useAuth();
  const manager = can('admin', 'manager');
  const [days, setDays] = useState(30);
  const [format, setFormat] = useState('pdf');
  const [list, setList] = useState([]);
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);

  const fetchList = () =>
    api.get('/reports').then((r) => setList(r.data)).catch(() => {});

  useEffect(() => {
    fetchList();
  }, []);

  const generate = async (e) => {
    e.preventDefault();
    setBusy(true);
    setMsg('');
    try {
      const r = await api.post('/reports', { days, format });
      setMsg(`Report generated: ${r.data.filename} (${r.data.mention_count} mentions).`);
      fetchList();
    } catch (err) {
      setMsg(err.response?.data?.detail || 'Report generation failed.');
    }
    setBusy(false);
  };

  const download = async (id, filename) => {
    const r = await api.get(`/reports/${id}/download`, { responseType: 'blob' });
    const url = window.URL.createObjectURL(new Blob([r.data]));
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const remove = async (id) => {
    if (!window.confirm('Delete this report?')) return;
    await api.delete(`/reports/${id}`);
    fetchList();
  };

  return (
    <div>
      <div className="page-head">
        <div>
          <h2>Reports &amp; Exports</h2>
          <p className="page-sub">Generate a branded summary (PDF) or raw mention dump (CSV) in one click</p>
        </div>
      </div>
      {msg && <div className="success">{msg}</div>}

      {manager && (
        <div className="card">
          <h3>Generate new report <span className="card-chip">manager</span></h3>
          <form onSubmit={generate} className="form-row">
            <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
            <select value={format} onChange={(e) => setFormat(e.target.value)}>
              <option value="pdf">PDF (summary)</option>
              <option value="csv">CSV (raw mentions)</option>
            </select>
            <button className="btn" type="submit" disabled={busy}>
              {busy ? 'Generating…' : '⚡ Generate report'}
            </button>
          </form>
        </div>
      )}

      <div className="card">
        <h3>{list.length} generated <span className="card-chip">newest first</span></h3>
        {list.length === 0 && <p className="meta">No reports yet.</p>}
        <table className="table">
          <thead>
            <tr><th>File</th><th>Format</th><th>Period</th><th>Mentions</th><th>Created</th><th></th></tr>
          </thead>
          <tbody>
            {list.map((r) => (
              <tr key={r.id}>
                <td>{r.filename}</td>
                <td><span className={`format-chip ${r.format}`}>{r.format}</span></td>
                <td>{r.days} days</td>
                <td>{r.mention_count}</td>
                <td>{new Date(r.created_at).toLocaleString()}</td>
                <td>
                  <button className="iconbtn" onClick={() => download(r.id, r.filename)}>⬇ Download</button>{' '}
                  {manager && <button className="iconbtn danger" onClick={() => remove(r.id)}>🗑</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
