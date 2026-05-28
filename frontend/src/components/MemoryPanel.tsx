import { useState, useEffect } from 'react'
import axios from 'axios'

interface SessionMemory {
  summary: Record<string, any>
  all_data: Record<string, any>
  history: Array<{ key: string; value: any; ts: string; op: string }>
}

interface LtmMemory {
  stats: Record<string, number>
  analyses: any[]
  testcases: any[]
  reports: any[]
}

type MemTab = 'session' | 'longterm'

export default function MemoryPanel() {
  const [tab, setTab]               = useState<MemTab>('session')
  const [session, setSession]       = useState<SessionMemory | null>(null)
  const [ltm, setLtm]               = useState<LtmMemory | null>(null)
  const [loading, setLoading]       = useState(false)
  const [error, setError]           = useState('')
  const [confirmClear, setConfirmClear] = useState<'session' | 'longterm' | null>(null)

  async function fetchSession() {
    setLoading(true); setError('')
    try {
      const r = await axios.get('/api/memory/session')
      setSession(r.data)
    } catch { setError('Could not fetch session memory — is the API running?') }
    finally { setLoading(false) }
  }

  async function fetchLtm() {
    setLoading(true); setError('')
    try {
      const r = await axios.get('/api/memory/longterm')
      setLtm(r.data)
    } catch { setError('Could not fetch long-term memory') }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchSession(); fetchLtm() }, [])

  async function clearMemory(type: 'session' | 'longterm') {
    try {
      await axios.delete(`/api/memory/${type}`)
      setConfirmClear(null)
      if (type === 'session') fetchSession()
      else fetchLtm()
    } catch { setError(`Failed to clear ${type} memory`) }
  }

  function renderValue(v: any): string {
    if (typeof v === 'string') return v.length > 120 ? v.slice(0, 117) + '…' : v
    if (typeof v === 'number' || typeof v === 'boolean') return String(v)
    if (Array.isArray(v)) return `[Array(${v.length})]`
    if (typeof v === 'object' && v !== null) return `{${Object.keys(v).join(', ')}}`
    return String(v)
  }

  return (
    <div>
      <div className="page-title">Memory Browser</div>
      <div className="page-sub">Inspect short-term session state and long-term ChromaDB vector memory</div>

      <div className="inner-tabs">
        <button className={`inner-tab ${tab === 'session' ? 'active' : ''}`} onClick={() => { setTab('session'); fetchSession() }}>
          🧠 Short-Term Memory
        </button>
        <button className={`inner-tab ${tab === 'longterm' ? 'active' : ''}`} onClick={() => { setTab('longterm'); fetchLtm() }}>
          💾 Long-Term Memory (ChromaDB)
        </button>
      </div>

      {loading && <div style={{ color: '#64748b', fontSize: '0.82rem', marginBottom: '1rem' }}>Loading…</div>}
      {error   && <div style={{ color: '#f87171', fontSize: '0.82rem', marginBottom: '1rem' }}>{error}</div>}

      {/* ── Session Memory ── */}
      {tab === 'session' && session && (
        <div>
          {/* Summary flags */}
          <div className="card">
            <div className="card-title" style={{ display: 'flex', justifyContent: 'space-between' }}>
              Pipeline Stage Flags
              <button className="btn btn-danger" style={{ fontSize: '0.72rem', padding: '0.25rem 0.6rem' }}
                onClick={() => setConfirmClear('session')}>
                Clear STM
              </button>
            </div>
            {session.summary && Object.keys(session.summary).length > 0 ? (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {Object.entries(session.summary).map(([k, v]) => (
                  <span key={k} className={`badge ${v ? 'badge-ok' : 'badge-p3'}`}>
                    {k.replace(/_/g, ' ')}: {v ? '✓' : '—'}
                  </span>
                ))}
              </div>
            ) : (
              <div style={{ color: '#475569', fontSize: '0.8rem' }}>No pipeline has been run yet.</div>
            )}
          </div>

          {/* All data */}
          {session.all_data && Object.keys(session.all_data).length > 0 && (
            <div className="card">
              <div className="card-title">Session Keys</div>
              <table className="data-table">
                <thead><tr><th>Key</th><th>Value Preview</th></tr></thead>
                <tbody>
                  {Object.entries(session.all_data).map(([k, v]) => (
                    <tr key={k}>
                      <td style={{ fontFamily: 'Consolas, monospace', color: '#7fb3d3', whiteSpace: 'nowrap' }}>{k}</td>
                      <td style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{renderValue(v)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Operation history */}
          {session.history?.length > 0 && (
            <div className="card">
              <div className="card-title">Recent Operations (last 20)</div>
              <div className="log-area" style={{ maxHeight: '280px' }}>
                {session.history.map((h, i) => (
                  <div key={i} style={{ marginBottom: '0.25rem', fontSize: '0.72rem' }}>
                    <span style={{ color: '#475569' }}>{h.ts?.slice(11, 19)}</span>
                    <span style={{ color: h.op === 'set' ? '#7fb3d3' : '#64748b', marginLeft: '0.5rem' }}>[{h.op}]</span>
                    <span style={{ color: '#94a3b8', marginLeft: '0.5rem' }}>{h.key}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Long-Term Memory ── */}
      {tab === 'longterm' && ltm && (
        <div>
          {/* Stats */}
          <div className="card">
            <div className="card-title" style={{ display: 'flex', justifyContent: 'space-between' }}>
              ChromaDB Collections
              <button className="btn btn-danger" style={{ fontSize: '0.72rem', padding: '0.25rem 0.6rem' }}
                onClick={() => setConfirmClear('longterm')}>
                Clear LTM
              </button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: '0.75rem' }}>
              {Object.entries(ltm.stats ?? {}).map(([k, v]) => (
                <div key={k} style={{ background: '#0a0f1a', borderRadius: '6px', padding: '0.75rem', textAlign: 'center' }}>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#7fb3d3' }}>{v}</div>
                  <div style={{ fontSize: '0.7rem', color: '#64748b', textTransform: 'capitalize', marginTop: '0.2rem' }}>
                    {k.replace(/_/g, ' ')}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Analyses */}
          {ltm.analyses?.length > 0 && (
            <div className="card">
              <div className="card-title">Stored Analyses</div>
              <table className="data-table">
                <thead><tr><th>Feature</th><th>Risk</th><th>P1 Reqs</th><th>Stored At</th></tr></thead>
                <tbody>
                  {ltm.analyses.map((a: any, i: number) => (
                    <tr key={i}>
                      <td>{a.feature_name ?? a.id ?? '—'}</td>
                      <td>
                        <span className={`badge ${a.risk_level === 'CRITICAL' ? 'badge-p1' : a.risk_level === 'HIGH' ? 'badge-p2' : 'badge-ok'}`}>
                          {a.risk_level ?? '—'}
                        </span>
                      </td>
                      <td>{a.req_count ?? '—'}</td>
                      <td style={{ fontSize: '0.72rem', color: '#475569' }}>{a.created_at?.slice(0, 16) ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Reports */}
          {ltm.reports?.length > 0 && (
            <div className="card">
              <div className="card-title">Quality Reports</div>
              <table className="data-table">
                <thead><tr><th>Feature</th><th>Quality Score</th><th>Scenarios</th><th>Stored At</th></tr></thead>
                <tbody>
                  {ltm.reports.map((r: any, i: number) => (
                    <tr key={i}>
                      <td>{r.feature_name ?? r.id ?? '—'}</td>
                      <td>
                        <span className={`badge ${(r.quality_score ?? 0) >= 80 ? 'badge-ok' : 'badge-warn'}`}>
                          {r.quality_score ?? '—'}/100
                        </span>
                      </td>
                      <td>{r.scenario_count ?? '—'}</td>
                      <td style={{ fontSize: '0.72rem', color: '#475569' }}>{r.created_at?.slice(0, 16) ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {(ltm.analyses?.length === 0 && ltm.reports?.length === 0) && (
            <div className="card">
              <div style={{ color: '#475569', fontSize: '0.82rem' }}>
                No long-term memories yet. Run the pipeline at least once to populate ChromaDB.
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Confirm clear dialog ── */}
      {confirmClear && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100,
        }}>
          <div className="card" style={{ maxWidth: '380px', width: '100%' }}>
            <div className="card-title" style={{ color: '#f87171' }}>Confirm Clear</div>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '1rem' }}>
              Are you sure you want to clear {confirmClear === 'session' ? 'short-term session' : 'long-term ChromaDB'} memory?
              This cannot be undone.
            </p>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button className="btn btn-danger" onClick={() => clearMemory(confirmClear)}>Yes, Clear</button>
              <button className="btn btn-outline" onClick={() => setConfirmClear(null)}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
