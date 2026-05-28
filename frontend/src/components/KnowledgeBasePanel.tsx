import { useState, useEffect } from 'react'
import axios from 'axios'

interface Regulation {
  id: string
  title: string
  convention: string
  category: string
  content: string
  applies_to?: string[]
  severity?: string
}

const SEVERITY_COLOR: Record<string, string> = {
  CRITICAL: 'badge-p1',
  HIGH:     'badge-p2',
  MEDIUM:   'badge-p3',
  LOW:      'badge-ok',
}

const CONVENTION_COLORS: Record<string, string> = {
  STCW:   '#7fb3d3',
  MLC:    '#4ade80',
  ISM:    '#fbbf24',
  MARPOL: '#f87171',
  SOLAS:  '#a78bfa',
  FAL:    '#22d3ee',
  BMP5:   '#fb923c',
  ISPS:   '#e879f9',
  IMO:    '#94a3b8',
}

export default function KnowledgeBasePanel() {
  const [regulations, setRegulations] = useState<Regulation[]>([])
  const [loading, setLoading]         = useState(false)
  const [error, setError]             = useState('')
  const [search, setSearch]           = useState('')
  const [results, setResults]         = useState<any[]>([])
  const [querying, setQuerying]       = useState(false)
  const [filterConv, setFilterConv]   = useState('')
  const [expanded, setExpanded]       = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    axios.get('/api/kb/regulations')
      .then(r => setRegulations(r.data.regulations ?? []))
      .catch(() => setError('Could not load knowledge base — is the API running?'))
      .finally(() => setLoading(false))
  }, [])

  async function doQuery() {
    if (!search.trim()) return
    setQuerying(true); setResults([])
    try {
      const r = await axios.get('/api/kb/query', { params: { topic: search.trim(), n: 6 } })
      setResults(r.data.results ?? [])
    } catch { setError('Query failed') }
    finally { setQuerying(false) }
  }

  const conventions = [...new Set(regulations.map(r => r.convention).filter(Boolean))]
  const filtered = regulations.filter(r =>
    (!filterConv || r.convention === filterConv) &&
    (!search || r.title?.toLowerCase().includes(search.toLowerCase()) || r.content?.toLowerCase().includes(search.toLowerCase()))
  )

  function convColor(conv: string) {
    return CONVENTION_COLORS[conv?.toUpperCase()] ?? '#94a3b8'
  }

  return (
    <div>
      <div className="page-title">Maritime Knowledge Base</div>
      <div className="page-sub">
        {regulations.length} IMO regulations indexed · STCW, MLC 2006, ISM, MARPOL, SOLAS, FAL, BMP5, ISPS
      </div>

      {/* ── Stats row ── */}
      <div className="metrics-row" style={{ gridTemplateColumns: 'repeat(4,1fr)' }}>
        {[
          { label: 'Total Regulations', val: regulations.length, color: '#7fb3d3' },
          { label: 'Safety Critical',   val: regulations.filter(r => r.severity === 'CRITICAL' || r.severity === 'HIGH').length, color: '#f87171' },
          { label: 'Conventions',        val: conventions.length, color: '#4ade80' },
          { label: 'PSC Categories',     val: 3, color: '#fbbf24' },
        ].map(s => (
          <div key={s.label} className="metric-card">
            <div className="metric-value" style={{ color: s.color, fontSize: '1.6rem' }}>{s.val}</div>
            <div className="metric-label">{s.label}</div>
          </div>
        ))}
      </div>

      {/* ── Search / Query ── */}
      <div className="card">
        <div className="card-title">Semantic Query</div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-end' }}>
          <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
            <input
              className="form-input"
              placeholder="e.g. crew rest hours, ECA sulphur limits, piracy high risk area…"
              value={search}
              onChange={e => setSearch(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && doQuery()}
            />
          </div>
          <button className="btn btn-primary" onClick={doQuery} disabled={querying}>
            {querying ? <span className="spinner" /> : 'Query KB'}
          </button>
        </div>

        {results.length > 0 && (
          <div style={{ marginTop: '1rem' }}>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '0.5rem' }}>
              Top {results.length} semantic matches:
            </div>
            {results.map((r: any, i: number) => (
              <div key={i} style={{
                background: '#0a0f1a',
                border: '1px solid #1e3a5f',
                borderRadius: '6px',
                padding: '0.75rem',
                marginBottom: '0.5rem',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                  <span style={{ fontSize: '0.82rem', fontWeight: 700, color: convColor(r.convention ?? '') }}>
                    {r.title ?? r.id}
                  </span>
                  <span style={{ fontSize: '0.7rem', color: '#475569' }}>
                    score: {typeof r.score === 'number' ? (1 - r.score).toFixed(3) : '—'}
                  </span>
                </div>
                <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{r.content?.slice(0, 180)}…</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Convention filter ── */}
      <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        <button
          className={`btn btn-outline ${filterConv === '' ? 'active' : ''}`}
          style={filterConv === '' ? { borderColor: '#2980b9', color: '#7fb3d3' } : {}}
          onClick={() => setFilterConv('')}
        >
          All
        </button>
        {conventions.map(c => (
          <button
            key={c}
            className={`btn btn-outline ${filterConv === c ? 'active' : ''}`}
            style={filterConv === c ? { borderColor: convColor(c), color: convColor(c) } : { color: convColor(c), borderColor: `${convColor(c)}44` }}
            onClick={() => setFilterConv(c)}
          >
            {c}
          </button>
        ))}
      </div>

      {loading && <div style={{ color: '#64748b', fontSize: '0.82rem' }}>Loading regulations…</div>}
      {error   && <div style={{ color: '#f87171', fontSize: '0.82rem', marginBottom: '1rem' }}>{error}</div>}

      {/* ── Regulations grid ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: '0.75rem' }}>
        {filtered.map(reg => (
          <div
            key={reg.id}
            className="card"
            style={{ marginBottom: 0, cursor: 'pointer', borderColor: expanded === reg.id ? convColor(reg.convention) : '#1e3a5f' }}
            onClick={() => setExpanded(expanded === reg.id ? null : reg.id)}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
              <div>
                <span style={{
                  fontSize: '0.65rem', fontWeight: 700, color: convColor(reg.convention),
                  background: `${convColor(reg.convention)}22`, padding: '1px 6px', borderRadius: '4px',
                  marginRight: '0.4rem',
                }}>
                  {reg.convention}
                </span>
                <span className={`badge ${SEVERITY_COLOR[reg.severity ?? 'MEDIUM'] ?? 'badge-p3'}`}>
                  {reg.severity ?? 'MEDIUM'}
                </span>
              </div>
              <span style={{ fontSize: '0.65rem', color: '#475569' }}>{expanded === reg.id ? '▲' : '▼'}</span>
            </div>
            <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#e2e8f0', marginBottom: '0.4rem' }}>
              {reg.title}
            </div>
            <div style={{ fontSize: '0.72rem', color: '#64748b', lineHeight: 1.5 }}>
              {expanded === reg.id
                ? reg.content
                : (reg.content?.slice(0, 100) + (reg.content?.length > 100 ? '…' : ''))
              }
            </div>
            {expanded === reg.id && reg.applies_to && reg.applies_to.length > 0 && (
              <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.3rem', flexWrap: 'wrap' }}>
                {reg.applies_to.map(t => (
                  <span key={t} className="badge badge-p3" style={{ fontSize: '0.6rem' }}>{t}</span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {filtered.length === 0 && !loading && (
        <div style={{ color: '#475569', fontSize: '0.82rem', textAlign: 'center', padding: '2rem' }}>
          No regulations match the current filter.
        </div>
      )}
    </div>
  )
}
