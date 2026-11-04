import React, { useEffect, useState } from 'react';
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import api from '../api.js';

const COLORS = { Positive: '#34d399', Neutral: '#94a3b8', Negative: '#f87171' };
const TOOLTIP = {
  backgroundColor: '#0e1530ee', border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: 12, color: '#e7ecf7', boxShadow: '0 10px 30px rgba(2,6,23,.45)',
};

const kpiDelays = [0, 0.05, 0.1, 0.15, 0.2, 0.25];

function useCountUp(target, ms = 700) {
  const [v, setV] = useState(0);
  useEffect(() => {
    if (typeof target !== 'number' || Number.isNaN(target)) return setV(target);
    let raf;
    const t0 = performance.now();
    const tick = (t) => {
      const p = Math.min(1, (t - t0) / ms);
      setV(Math.round(target * (1 - Math.pow(1 - p, 3))));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, ms]);
  return v;
}

function Skeletons() {
  return (
    <div>
      <div className="kpis">
        {Array.from({ length: 6 }).map((_, i) => <div key={i} className="skeleton kpi-like" />)}
      </div>
      <div className="card" style={{ marginTop: 18 }}><div className="skeleton chart-like" /></div>
      <div className="grid2">
        <div className="card"><div className="skeleton chart-like" /></div>
        <div className="card"><div className="skeleton chart-like" /></div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [days, setDays] = useState(30);
  const [summary, setSummary] = useState(null);
  const [trends, setTrends] = useState([]);
  const [dist, setDist] = useState([]);
  const [topics, setTopics] = useState([]);
  const [complaints, setComplaints] = useState([]);
  const [sources, setSources] = useState([]);
  const [cfg, setCfg] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/config').then((r) => setCfg(r.data)).catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.get('/dashboard/summary', { params: { days } }),
      api.get('/dashboard/trends', { params: { days } }),
      api.get('/dashboard/distribution', { params: { days } }),
      api.get('/dashboard/topics', { params: { days } }),
      api.get('/dashboard/complaints', { params: { limit: 8, days } }),
      api.get('/dashboard/sources', { params: { days } }),
    ])
      .then(([s, t, d, top, c, src]) => {
        setSummary(s.data);
        setTrends(t.data);
        setDist(d.data);
        setTopics(top.data);
        setComplaints(c.data);
        setSources(src.data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [days]);

  const cTotal = useCountUp(summary?.total_mentions || 0);
  const cPos = useCountUp(summary?.positive_pct || 0);
  const cNeg = useCountUp(summary?.negative_pct || 0);
  const cNeu = useCountUp(summary?.neutral || 0);
  const cToday = useCountUp(summary?.today_count || 0);

  if (loading) return <Skeletons />;
  if (!summary) return <div className="center empty">No data yet — ask an admin to run ingestion, then refresh.</div>;

  const maxSrc = Math.max(1, ...sources.map((s) => s.count));

  return (
    <div>
      <div className="page-head">
        <div>
          <h2>Analytics Overview</h2>
          <p className="page-sub">
            Every mention classified by the production model
            {cfg ? ` · tracked brand: ${cfg.brand}` : ''} · refreshes as ingestors run
          </p>
        </div>
        <div className="head-actions">
          <div className="seg">
            {[7, 30, 90].map((d) => (
              <button key={d} className={days === d ? 'active' : ''} onClick={() => setDays(d)}>
                {d}d
              </button>
            ))}
          </div>
        </div>
      </div>

      {cfg && (
        <div className="banner">
          <span className="banner-emoji">🤖</span>
          <div>
            Every mention is classified by a <b>TF-IDF + Logistic Regression model</b> trained on{' '}
            <b>{Number(cfg.model_samples || 0).toLocaleString()} real tweets</b>
            ({cfg.model_source}, accuracy <b>{Math.round((cfg.model_accuracy || 0) * 100)}%</b>).
            Live sources: <b>HackerNews · Reddit · Mastodon · Bluesky · News</b> + uploads.
            Set <b>BRAND_NAME</b> to a real brand to pull live data.
          </div>
        </div>
      )}

      <div className="kpis stagger">
        <div className="kpi" style={{ animationDelay: kpiDelays[0] }}>
          <div className="kpi-top"><span className="kpi-ico">📦</span><span className="label">Total mentions</span></div>
          <div className="value">{cTotal}</div>
          <div className="foot">last {days} days</div>
        </div>
        <div className="kpi pos" style={{ animationDelay: kpiDelays[1] }}>
          <div className="kpi-top"><span className="kpi-ico">😊</span><span className="label">Positive</span></div>
          <div className="value">{cPos}%</div>
          <div className="foot">{summary.positive} mentions</div>
        </div>
        <div className="kpi neg" style={{ animationDelay: kpiDelays[2] }}>
          <div className="kpi-top"><span className="kpi-ico">😡</span><span className="label">Negative</span></div>
          <div className="value">{cNeg}%</div>
          <div className="foot">{summary.negative} mentions</div>
        </div>
        <div className="kpi neu" style={{ animationDelay: kpiDelays[3] }}>
          <div className="kpi-top"><span className="kpi-ico">😐</span><span className="label">Neutral</span></div>
          <div className="value">{cNeu}</div>
          <div className="foot">no strong signal</div>
        </div>
        <div className="kpi" style={{ animationDelay: kpiDelays[4] }}>
          <div className="kpi-top"><span className="kpi-ico">📅</span><span className="label">Today</span></div>
          <div className="value">{cToday}</div>
          <div className="foot">new since midnight</div>
        </div>
        <div className="kpi" style={{ animationDelay: kpiDelays[5] }}>
          <div className="kpi-top"><span className="kpi-ico">🔍</span><span className="label">Top topic</span></div>
          <div className="value" style={{ fontSize: 20 }}>{summary.top_topic || '—'}</div>
          <div className="foot">most discussed</div>
        </div>
      </div>

      <div className="card">
        <h3>Sentiment trend over time <span className="card-chip">stacked area</span></h3>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={trends}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={20} />
            <YAxis allowDecimals={false} />
            <Tooltip contentStyle={TOOLTIP} cursor={{ stroke: 'rgba(139,147,169,0.4)' }} />
            <Legend />
            <Area type="monotone" dataKey="positive" name="Positive" stackId="1" stroke={COLORS.Positive} fill={COLORS.Positive} fillOpacity={0.4} />
            <Area type="monotone" dataKey="neutral" name="Neutral" stackId="1" stroke={COLORS.Neutral} fill={COLORS.Neutral} fillOpacity={0.4} />
            <Area type="monotone" dataKey="negative" name="Negative" stackId="1" stroke={COLORS.Negative} fill={COLORS.Negative} fillOpacity={0.4} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="grid2">
        <div className="card">
          <h3>Trending topics <span className="card-chip">by sentiment</span></h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={topics} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" allowDecimals={false} />
              <YAxis type="category" dataKey="topic" width={90} tick={{ fontSize: 12 }} />
              <Tooltip contentStyle={TOOLTIP} cursor={{ fill: 'rgba(99,102,241,0.08)' }} />
              <Legend />
              <Bar dataKey="positive" name="Positive" stackId="a" fill={COLORS.Positive} />
              <Bar dataKey="neutral" name="Neutral" stackId="a" fill={COLORS.Neutral} />
              <Bar dataKey="negative" name="Negative" stackId="a" fill={COLORS.Negative} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div>
          <div className="card">
            <h3>Sentiment share <span className="card-chip">donut</span></h3>
            <ResponsiveContainer width="100%" height={230}>
              <PieChart>
                <Pie data={dist} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85} paddingAngle={3} label>
                  {dist.map((d) => (
                    <Cell key={d.name} fill={COLORS[d.name]} stroke="rgba(11,16,32,0.9)" />
                  ))}
                </Pie>
                <Tooltip contentStyle={TOOLTIP} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="card">
            <h3>Data sources <span className="card-chip">volume</span></h3>
            {sources.length === 0 && <div className="empty">No data.</div>}
            {sources.map((s, i) => (
              <div key={s.source} className="bar-row" style={{ animationDelay: `${i * 0.06}s` }}>
                <span className="name">{s.source}</span>
                <div className="bar-track">
                  <div className="bar-fill" style={{ width: `${Math.round((s.count / maxSrc) * 100)}%` }} />
                </div>
                <span className="count">{s.count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="card">
        <h3>Latest complaints <span className="card-chip">newest first</span></h3>
        {complaints.length === 0 && <div className="empty">No complaints in this period. 🎉</div>}
        <div className="stagger">
          {complaints.map((c) => (
            <div key={c.id} className="card complaint">
              <div className="mention-text">{c.text}</div>
              <div className="meta">
                @{c.author} · <span className={`source ${c.source}`}>{c.source}</span> · {new Date(c.posted_at).toLocaleString()} ·{' '}
                {(c.topics || '').split(',').filter(Boolean).map((t) => (
                  <span key={t} className="tag">{t}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
