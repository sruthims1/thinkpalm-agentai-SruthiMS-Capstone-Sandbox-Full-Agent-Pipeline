import { useEffect, useRef } from 'react'
import type { PipelineResult } from '../App'

interface Props {
  agentProgress: Record<string, number>
  isRunning: boolean
  logs: string[]
  result: PipelineResult | null
}

const AGENTS = ['Maritime Domain Expert', 'Test Strategist', 'Automation Engineer', 'QA Auditor']

function logClass(msg: string): string {
  if (msg.includes('ERROR') || msg.includes('error')) return 'log-line error'
  if (msg.includes('complete') || msg.includes('complete') || msg.includes('===')) return 'log-line success'
  if (msg.includes('WARN') || msg.includes('review')) return 'log-line warn'
  return 'log-line'
}

export default function Sidebar({ agentProgress, isRunning, logs, result }: Props) {
  const logRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight
    }
  }, [logs])

  const ltmStats = result?.test_result ? {
    analyses: '1+',
    tests: result.gherkin_result?.validation?.scenario_count ?? 0,
  } : null

  return (
    <aside className="sidebar">

      {/* ── Agent Pipeline ── */}
      <div className="sidebar-section">
        <div className="sidebar-label">Agent Pipeline</div>
        {AGENTS.map((agent) => {
          const pct = agentProgress[agent] ?? 0
          const done = pct === 100
          return (
            <div key={agent} style={{ marginBottom: '0.6rem' }}>
              <div className="agent-row">
                <span className="agent-name">{agent}</span>
                <span className={`agent-badge ${done ? 'done' : ''}`}>
                  {done ? 'done' : isRunning && pct > 0 ? 'running' : pct === 0 && isRunning ? 'queued' : 'idle'}
                </span>
              </div>
              <div className="agent-row">
                <div className="progress-bar-bg">
                  <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
                </div>
                <span style={{ fontSize: '0.65rem', color: '#475569', marginLeft: '0.4rem', minWidth: '28px' }}>
                  {pct}%
                </span>
              </div>
            </div>
          )
        })}
      </div>

      {/* ── Live Logs ── */}
      <div className="sidebar-section">
        <div className="sidebar-label">
          Live Logs
          {isRunning && <span style={{ marginLeft: '0.5rem' }} className="spinner" />}
        </div>
        <div className="log-area" ref={logRef}>
          {logs.length === 0
            ? <span style={{ color: '#475569' }}>Waiting for pipeline…</span>
            : logs.map((l, i) => (
                <div key={i} className={logClass(l)}>
                  {l.length > 90 ? l.slice(0, 87) + '…' : l}
                </div>
              ))
          }
        </div>
      </div>

      {/* ── Pipeline Stats ── */}
      {result?.success && (
        <div className="sidebar-section">
          <div className="sidebar-label">Last Run</div>
          <div className="stat-row">
            <span className="stat-label">Feature</span>
            <span className="stat-value" style={{ fontSize: '0.7rem', maxWidth: '130px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {result.feature_name}
            </span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Risk Level</span>
            <span className="stat-value" style={{
              color: result.domain_enrichment?.risk_level === 'CRITICAL' ? '#f87171'
                   : result.domain_enrichment?.risk_level === 'HIGH' ? '#fbbf24' : '#4ade80'
            }}>
              {result.domain_enrichment?.risk_level ?? '—'}
            </span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Scenarios</span>
            <span className="stat-value">{result.gherkin_result?.validation?.scenario_count ?? 0}</span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Quality Score</span>
            <span className="stat-value" style={{ color: '#4ade80' }}>
              {result.test_result?.risk_report?.quality_score ?? 0}/100
            </span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Requirements</span>
            <span className="stat-value">{result.requirements?.total_requirements ?? 0}</span>
          </div>
          <div className="stat-row">
            <span className="stat-label">P1 Safety</span>
            <span className="stat-value" style={{ color: '#f87171' }}>
              {result.domain_enrichment?.p1_safety_requirements?.length ?? 0}
            </span>
          </div>
        </div>
      )}

      {/* ── Memory Stats ── */}
      <div className="sidebar-section">
        <div className="sidebar-label">Memory</div>
        <div className="stat-row">
          <span className="stat-label">STM Keys</span>
          <span className="stat-value">{result ? '8' : '0'}</span>
        </div>
        <div className="stat-row">
          <span className="stat-label">LTM Analyses</span>
          <span className="stat-value">{ltmStats ? ltmStats.analyses : '—'}</span>
        </div>
        <div className="stat-row">
          <span className="stat-label">LTM Tests</span>
          <span className="stat-value">{ltmStats ? ltmStats.tests : '—'}</span>
        </div>
        <div className="stat-row">
          <span className="stat-label">KB Regulations</span>
          <span className="stat-value" style={{ color: '#7fb3d3' }}>16</span>
        </div>
      </div>

    </aside>
  )
}
