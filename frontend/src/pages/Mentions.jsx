import React, { useEffect, useState } from 'react';
import api from '../api.js';
import { useAuth } from '../auth.jsx';

const PAGE_SIZE = 15;

export default function Mentions() {
  const { can } = useAuth();
  const manager = can('admin', 'manager');
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [sentiment, setSentiment] = useState('');
  const [topic, setTopic] = useState('');
  const [q, setQ] = useState('');
  const [days, setDays] = useState(365);
  const [msg, setMsg] = useState('');
  const [newText, setNewText] = useState('');

  const fetchData = (p = page) => {
    api
      .get('/mentions', {
        params: {
          page: p, page_size: PAGE_SIZE, days,
          ...(sentiment ? { sentiment } : {}),
          ...(topic ? { topic } : {}),
          ...(q ? { q } : {}),
        },
      })
      .then((r) => {
        setItems(r.data.items);
        setTotal(r.data.total);
      })
      .catch(() => {});
  };

  useEffect(() => {
    setPage(1);
    fetchData(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sentiment, days]);

  const search = (e) => {
    e.preventDefault();
    setPage(1);
    fetchData(1);
  };

  const addMention = async (e) => {
    e.preventDefault();
    if (!newText.trim()) return;
    try {
      await api.post('/mentions', { text: newText });
      setNewText('');
      setMsg('Mention added and classified.');
      fetchData(1);
    } catch (err) {
      setMsg(err.response?.data?.detail || 'Failed to add mention.');
    }
  };

  const uploadCsv = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const form = new FormData();
    form.append('file', file);
    try {
      const r = await api.post('/mentions/upload-csv', form);
      setMsg(`CSV imported: ${r.data.added} mentions (${r.data.auto_classified} auto-classified).`);
      fetchData(1);
    } catch (err) {
      setMsg(err.response?.data?.detail || 'CSV upload failed.');
    }
    e.target.value = '';
  };

  const remove = async (id) => {
    if (!window.confirm('Delete this mention?')) return;
    await api.delete(`/mentions/${id}`);
    fetchData();
  };

  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      <div className="page-head">
        <div>
          <h2>Mentions Inbox</h2>
          <p className="page-sub">Every collected mention with its model-assigned sentiment and topics</p>
        </div>
      </div>
      {msg && <div className="success">{msg}</div>}

      <form onSubmit={search} className="card filters-card">
        <h3>Filter &amp; search</h3>
        <div className="filters-row">
          <select value={sentiment} onChange={(e) => setSentiment(e.target.value)}>
            <option value="">All sentiments</option>
            <option value="positive">Positive</option>
            <option value="neutral">Neutral</option>
            <option value="negative">Negative</option>
          </select>
          <input placeholder="Topic (e.g. delivery)" value={topic} onChange={(e) => setTopic(e.target.value)} />
          <input placeholder="Search text or author…" value={q} onChange={(e) => setQ(e.target.value)} />
          <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={365}>Last year</option>
          </select>
          <button className="btn" type="submit">Search</button>
        </div>
      </form>

      {manager && (
        <div className="card">
          <h3>Add / import mentions <span className="card-chip">manager</span></h3>
          <form onSubmit={addMention} className="form-row">
            <input
              style={{ flex: 4 }}
              placeholder="Type a brand mention — it will be auto-classified…"
              value={newText}
              onChange={(e) => setNewText(e.target.value)}
            />
            <button className="btn" type="submit">Add mention</button>
          </form>
          <label className="lbl">Bulk import CSV (columns: text, sentiment?, author?, source?, posted_at?)</label>
          <input type="file" accept=".csv" onChange={uploadCsv} />
        </div>
      )}

      <div className="card">
        <h3>{total} mentions <span className="card-chip">page {page}/{pages}</span></h3>
        {items.length === 0 && <div className="empty">No mentions match these filters. Try widening the date range.</div>}
        {items.map((m) => {
          const ico = m.sentiment === 'positive' ? '😊' : m.sentiment === 'negative' ? '😡' : '😐';
          return (
            <div key={m.id} className="mention-item">
              <span className={`senti-ico ${m.sentiment}`}>{ico}</span>
              <div className="m-body">
                <div className="m-head">
                  <span className={`badge ${m.sentiment}`}>{m.sentiment}</span>
                  <span className={`source ${m.source}`}>{m.source}</span>
                  <span className="meta">conf {(m.confidence ?? 0).toFixed(2)} · @{m.author} · {new Date(m.posted_at).toLocaleString()}</span>
                </div>
                <div className="mention-text">{m.text}</div>
                <div>
                  {(m.topics || '').split(',').filter(Boolean).map((t) => (
                    <span key={t} className="tag">{t}</span>
                  ))}
                  {manager && (
                    <button className="iconbtn danger" style={{ marginLeft: 6 }} onClick={() => remove(m.id)}>
                      🗑 Delete
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
        <div className="pager">
          <button className="btn small ghost" disabled={page <= 1} onClick={() => { setPage(page - 1); fetchData(page - 1); }}>‹ Prev</button>
          <button className="btn small ghost" disabled={page >= pages} onClick={() => { setPage(page + 1); fetchData(page + 1); }}>Next ›</button>
          <span className="pageinfo">Page {page} of {pages}</span>
        </div>
      </div>
    </div>
  );
}
