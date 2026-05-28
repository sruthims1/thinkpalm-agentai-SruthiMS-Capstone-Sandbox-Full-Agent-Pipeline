import { useState, useEffect } from 'react'
import type { PipelineResult } from '../App'

interface Props {
  result: PipelineResult | null
}

type OutTab = 'testcases' | 'gherkin' | 'playwright' | 'risk' | 'audit'

// ── Scenario types ─────────────────────────────────────────────────────────────
interface TestCase {
  id: string
  title: string
  tags: string[]
  priority: 'P1' | 'P2' | 'P3'
  regulations: string[]
  testType: string
  given: string[]
  when: string[]
  then: string[]
  isOutline: boolean
  deleted: boolean
}

// ── Gherkin parser ─────────────────────────────────────────────────────────────
function parseGherkin(text: string): TestCase[] {
  const lines  = text.split('\n')
  const cases: TestCase[] = []
  let currentTags: string[] = []
  let current: Partial<TestCase> | null = null
  let idx = 0

  const flush = () => {
    if (current?.title) {
      cases.push({
        id:         `TC-${String(cases.length + 1).padStart(3, '0')}`,
        title:      current.title,
        tags:       current.tags ?? [],
        priority:   current.priority ?? 'P3',
        regulations: current.regulations ?? [],
        testType:   current.testType ?? 'functional',
        given:      current.given ?? [],
        when:       current.when ?? [],
        then:       current.then ?? [],
        isOutline:  current.isOutline ?? false,
        deleted:    false,
      })
    }
    current = null
    currentTags = []
  }

  while (idx < lines.length) {
    const raw  = lines[idx]
    const line = raw.trim()
    idx++

    if (line.startsWith('@')) {
      currentTags = [...currentTags, ...line.split(/\s+/).filter(t => t.startsWith('@'))]
      continue
    }

    if (line.startsWith('Scenario Outline:') || line.startsWith('Scenario:')) {
      flush()
      const isOutline = line.startsWith('Scenario Outline:')
      const title = line.replace(/^Scenario Outline:|^Scenario:/, '').trim()

      const priority: 'P1' | 'P2' | 'P3' = currentTags.some(t =>
        t.includes('p1') || t.includes('safety-critical')
      ) ? 'P1' : currentTags.some(t => t.includes('p2') || t.includes('compliance')) ? 'P2' : 'P3'

      const REG_TAGS = ['@stcw','@mlc','@ism','@marpol','@fal','@solas','@isps','@bmp5']
      const regulations = currentTags.filter(t => REG_TAGS.includes(t.toLowerCase()))

      const typeTag = currentTags.find(t =>
        ['@happy-path','@negative','@boundary','@edge-case'].includes(t)
      )
      const testType = typeTag ? typeTag.slice(1) : 'functional'

      current = { title, tags: [...currentTags], priority, regulations, testType, isOutline, given: [], when: [], then: [] }
      currentTags = []
      continue
    }

    if (current) {
      if (line.startsWith('Given') || (line.startsWith('And') && (current.given?.length ?? 0) > 0 && (current.when?.length ?? 0) === 0 && (current.then?.length ?? 0) === 0)) {
        current.given!.push(line)
      } else if (line.startsWith('When') || (line.startsWith('And') && (current.when?.length ?? 0) > 0 && (current.then?.length ?? 0) === 0)) {
        current.when!.push(line)
      } else if (line.startsWith('Then') || (line.startsWith('And') && (current.then?.length ?? 0) > 0) || line.startsWith('But')) {
        current.then!.push(line)
      }
    }
  }
  flush()
  return cases
}

// ── Step cleaner (shared by display + CSV) ────────────────────────────────────
const LOGIN_RE = /logged in|am logged|login as|log in as/i

function cleanStep(raw: string): string {
  return raw
    .replace(/^(Given|When|Then|And|But)\s+/i, '')
    .replace(/^I\s+/i, '')
    .trim()
}

function cleanSteps(steps: string[]): string[] {
  return steps.map(cleanStep).filter(s => s && !LOGIN_RE.test(s))
}

// ── CSV export (QMetry-compatible) ─────────────────────────────────────────────
function exportQMetryCSV(cases: TestCase[], featureName: string) {
  const escape = (s: string) => `"${s.replace(/"/g, '""')}"`

  const header = [
    'Test Case ID', 'Summary', 'Priority', 'Status', 'Component',
    'Labels', 'Automation Type', 'Test Type',
    'Preconditions (Given)', 'Test Steps (When)', 'Expected Result (Then)',
    'BDD Tags',
  ].map(escape).join(',')

  const priorityLabel: Record<string, string> = { P1: 'Critical', P2: 'High', P3: 'Medium' }

  const rows = cases
    .filter(tc => !tc.deleted)
    .map(tc => [
      escape(tc.id),
      escape(tc.title),
      escape(priorityLabel[tc.priority] ?? 'Medium'),
      escape('New'),
      escape(featureName),
      escape(tc.regulations.join(', ')),
      escape('Automated-BDD'),
      escape(tc.testType),
      escape(cleanSteps(tc.given).join('\n')),
      escape(cleanSteps(tc.when).join('\n')),
      escape(cleanSteps(tc.then).join('\n')),
      escape(tc.tags.join(' ')),
    ].join(','))

  const csv  = [header, ...rows].join('\r\n')
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href = url
  a.download = `${featureName.toLowerCase().replace(/ /g,'_')}_qmetry.csv`
  a.click()
  URL.revokeObjectURL(url)
}

function downloadFile(content: string, filename: string, mime = 'application/octet-stream') {
  const blob = new Blob([content], { type: mime })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

// ── Edit modal ─────────────────────────────────────────────────────────────────
function EditModal({ tc, onSave, onClose }: {
  tc: TestCase
  onSave: (updated: TestCase) => void
  onClose: () => void
}) {
  const [title, setTitle]   = useState(tc.title)
  const [tags,  setTags]    = useState(tc.tags.join(' '))
  const [given, setGiven]   = useState(tc.given.join('\n'))
  const [when_,  setWhen]   = useState(tc.when.join('\n'))
  const [then_,  setThen]   = useState(tc.then.join('\n'))

  const save = () => {
    const newTags = tags.trim().split(/\s+/).filter(t => t.startsWith('@'))
    const priority: 'P1'|'P2'|'P3' = newTags.some(t => t.includes('p1')||t.includes('safety-critical'))
      ? 'P1' : newTags.some(t => t.includes('p2')||t.includes('compliance')) ? 'P2' : 'P3'
    const REG_TAGS = ['@stcw','@mlc','@ism','@marpol','@fal','@solas','@isps','@bmp5']
    const regulations = newTags.filter(t => REG_TAGS.includes(t.toLowerCase()))
    onSave({
      ...tc, title,
      tags: newTags, priority, regulations,
      given: given.split('\n').map(s => s.trim()).filter(Boolean),
      when:  when_.split('\n').map(s => s.trim()).filter(Boolean),
      then:  then_.split('\n').map(s => s.trim()).filter(Boolean),
    })
  }

  return (
    <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.7)', zIndex:1000, display:'flex', alignItems:'center', justifyContent:'center' }}>
      <div style={{ background:'#0d1117', border:'1px solid #1e3a5f', borderRadius:'10px', width:'640px', maxHeight:'85vh', overflow:'auto', padding:'1.5rem' }}>
        <div style={{ display:'flex', justifyContent:'space-between', marginBottom:'1rem' }}>
          <span style={{ fontWeight:700, color:'#7fb3d3' }}>Edit Test Case — {tc.id}</span>
          <button onClick={onClose} style={{ background:'none', border:'none', color:'#64748b', cursor:'pointer', fontSize:'1.2rem' }}>✕</button>
        </div>

        <label style={{ fontSize:'0.75rem', color:'#64748b' }}>Summary / Title</label>
        <input value={title} onChange={e => setTitle(e.target.value)}
          style={{ width:'100%', background:'#0a0f1a', border:'1px solid #1e3a5f', borderRadius:'5px', color:'#e2e8f0', padding:'0.5rem', marginBottom:'0.75rem', fontSize:'0.82rem', boxSizing:'border-box' }} />

        <label style={{ fontSize:'0.75rem', color:'#64748b' }}>Tags (space-separated @tags)</label>
        <input value={tags} onChange={e => setTags(e.target.value)}
          style={{ width:'100%', background:'#0a0f1a', border:'1px solid #1e3a5f', borderRadius:'5px', color:'#e2e8f0', padding:'0.5rem', marginBottom:'0.75rem', fontSize:'0.82rem', boxSizing:'border-box' }} />

        {[['Preconditions (Given)', given, setGiven], ['Test Steps (When)', when_, setWhen], ['Expected Result (Then)', then_, setThen]].map(([label, val, setter]: any) => (
          <div key={label as string}>
            <label style={{ fontSize:'0.75rem', color:'#64748b' }}>{label as string}</label>
            <textarea value={val as string} onChange={e => setter(e.target.value)} rows={3}
              style={{ width:'100%', background:'#0a0f1a', border:'1px solid #1e3a5f', borderRadius:'5px', color:'#e2e8f0', padding:'0.5rem', marginBottom:'0.75rem', fontSize:'0.78rem', resize:'vertical', boxSizing:'border-box' }} />
          </div>
        ))}

        <div style={{ display:'flex', gap:'0.75rem', justifyContent:'flex-end' }}>
          <button onClick={onClose} style={{ padding:'0.5rem 1rem', background:'#1e293b', border:'1px solid #334155', borderRadius:'5px', color:'#94a3b8', cursor:'pointer', fontSize:'0.82rem' }}>Cancel</button>
          <button onClick={save}    style={{ padding:'0.5rem 1rem', background:'#1e40af', border:'none', borderRadius:'5px', color:'white', cursor:'pointer', fontWeight:600, fontSize:'0.82rem' }}>Save Changes</button>
        </div>
      </div>
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────────────
export default function OutputPanel({ result }: Props) {
  const [tab,       setTab]       = useState<OutTab>('testcases')
  const [testCases, setTestCases] = useState<TestCase[]>([])
  const [editTc,    setEditTc]    = useState<TestCase | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  useEffect(() => {
    if (result?.gherkin_result?.gherkin_text) {
      setTestCases(parseGherkin(result.gherkin_result.gherkin_text))
      setTab('testcases')
    }
  }, [result])

  if (!result) {
    return (
      <div style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', height:'60vh', color:'#475569' }}>
        <div style={{ fontSize:'3rem', marginBottom:'1rem' }}>📄</div>
        <div style={{ fontSize:'1rem', fontWeight:600, marginBottom:'0.5rem' }}>No results yet</div>
        <div style={{ fontSize:'0.82rem' }}>Run the AI pipeline from the Pipeline tab to generate test artefacts</div>
      </div>
    )
  }

  if (result.success === false) {
    return (
      <div className="card" style={{ borderColor:'#7f1d1d' }}>
        <div className="card-title" style={{ color:'#f87171' }}>Pipeline Error</div>
        <div style={{ color:'#fca5a5', fontSize:'0.85rem' }}>{(result as any).error ?? 'An error occurred in the pipeline. Check the backend terminal for details.'}</div>
      </div>
    )
  }

  const { domain_enrichment: de, requirements: req, gherkin_result: gr, test_result: tr, audit_result: audit } = result
  const safe = result.feature_name.toLowerCase().replace(/ /g, '_')
  const cov  = tr?.coverage_report
  const rr   = tr?.risk_report
  const val  = gr?.validation

  const activeCases = testCases.filter(tc => !tc.deleted)

  const handleEdit   = (tc: TestCase) => setEditTc(tc)
  const handleSave   = (updated: TestCase) => { setTestCases(prev => prev.map(t => t.id === updated.id ? updated : t)); setEditTc(null) }
  const handleDelete = (id: string) => { setTestCases(prev => prev.map(t => t.id === id ? { ...t, deleted: true } : t)); setDeleteConfirm(null) }

  return (
    <div>
      {editTc && <EditModal tc={editTc} onSave={handleSave} onClose={() => setEditTc(null)} />}

      {deleteConfirm && (
        <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.7)', zIndex:1000, display:'flex', alignItems:'center', justifyContent:'center' }}>
          <div style={{ background:'#0d1117', border:'1px solid #7f1d1d', borderRadius:'10px', padding:'1.5rem', width:'380px' }}>
            <div style={{ color:'#f87171', fontWeight:700, marginBottom:'0.75rem' }}>Delete Test Case?</div>
            <div style={{ color:'#94a3b8', fontSize:'0.82rem', marginBottom:'1.25rem' }}>This will remove the test case from the local list. The original .feature file is unchanged.</div>
            <div style={{ display:'flex', gap:'0.75rem', justifyContent:'flex-end' }}>
              <button onClick={() => setDeleteConfirm(null)} style={{ padding:'0.4rem 0.9rem', background:'#1e293b', border:'1px solid #334155', borderRadius:'5px', color:'#94a3b8', cursor:'pointer', fontSize:'0.82rem' }}>Cancel</button>
              <button onClick={() => handleDelete(deleteConfirm)} style={{ padding:'0.4rem 0.9rem', background:'#7f1d1d', border:'none', borderRadius:'5px', color:'white', cursor:'pointer', fontWeight:600, fontSize:'0.82rem' }}>Delete</button>
            </div>
          </div>
        </div>
      )}

      <div className="page-title">{result.feature_name}</div>

      {/* ── 3 metric cards ── */}
      <div className="metrics-row" style={{ gridTemplateColumns:'repeat(3,1fr)' }}>
        <div className="metric-card">
          <div className="metric-value">{activeCases.length}</div>
          <div className="metric-label">Test Cases</div>
        </div>
        <div className="metric-card">
          <div className="metric-value red">{activeCases.filter(t => t.priority === 'P1').length}</div>
          <div className="metric-label">P1 Safety-Critical</div>
        </div>
        <div className="metric-card">
          <div className="metric-value green">{rr?.quality_score ?? 0}<span style={{ fontSize:'0.7rem', color:'#475569' }}>/100</span></div>
          <div className="metric-label">Quality Score</div>
        </div>
      </div>

      {/* ── Download bar ── */}
      <div className="download-bar">
        <button className="download-btn" style={{ background:'#1e40af', borderColor:'#3b82f6' }}
          onClick={() => exportQMetryCSV(testCases, result.feature_name)}>
          ⬇ Export QMetry CSV
        </button>
        <button className="download-btn" onClick={() => downloadFile(gr?.gherkin_text ?? '', `${safe}.feature`)}>
          ⬇ {safe}.feature
        </button>
        <button className="download-btn" onClick={() => downloadFile(tr?.spec_ts ?? '', `${safe}.spec.ts`)}>
          ⬇ {safe}.spec.ts
        </button>
      </div>

      {/* ── Tabs ── */}
      <div className="inner-tabs">
        {([
          ['testcases',  '✅ Test Cases'],
          ['gherkin',    '🥒 Gherkin'],
          ['playwright', '🎭 TypeScript'],
          ['risk',       '⚠️ Risk'],
          ['audit',      '🔬 Audit'],
        ] as [OutTab, string][]).map(([t, label]) => (
          <button key={t} className={`inner-tab ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
            {label}
            {t === 'testcases' && activeCases.length > 0 && (
              <span style={{ marginLeft:'0.4rem', background:'#1e40af', color:'white', borderRadius:'10px', padding:'0 5px', fontSize:'0.65rem' }}>{activeCases.length}</span>
            )}
          </button>
        ))}
      </div>

      {/* ── Test Cases tab ── */}
      {tab === 'testcases' && (
        <div>
          {activeCases.length === 0 ? (
            <div className="card">
              <div style={{ color:'#475569', fontSize:'0.82rem' }}>No test cases. Run the pipeline first.</div>
            </div>
          ) : activeCases.map(tc => (
            <div key={tc.id} className="card" style={{
              marginBottom:'0.75rem',
              borderLeft: `3px solid ${tc.priority === 'P1' ? '#f87171' : tc.priority === 'P2' ? '#fbbf24' : '#3b82f6'}`,
            }}>
              <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:'0.6rem' }}>
                <div style={{ display:'flex', alignItems:'center', gap:'0.5rem', flexWrap:'wrap' }}>
                  <span style={{ fontFamily:'Consolas,monospace', color:'#7fb3d3', fontSize:'0.72rem', fontWeight:700 }}>{tc.id}</span>
                  <span className={`badge ${tc.priority === 'P1' ? 'badge-p1' : tc.priority === 'P2' ? 'badge-p2' : 'badge-p3'}`}>{tc.priority}</span>
                  <span className="badge badge-warn" style={{ fontSize:'0.62rem' }}>{tc.testType}</span>
                  {tc.isOutline && <span className="badge" style={{ background:'#164e63', color:'#67e8f9', fontSize:'0.62rem' }}>Outline</span>}
                  {tc.regulations.map(r => (
                    <span key={r} style={{ fontSize:'0.62rem', color:'#64748b', background:'#0a0f1a', border:'1px solid #1e3a5f', borderRadius:'3px', padding:'0 5px' }}>{r}</span>
                  ))}
                </div>
                <div style={{ display:'flex', gap:'0.4rem', flexShrink:0 }}>
                  <button onClick={() => handleEdit(tc)}
                    style={{ padding:'0.25rem 0.55rem', background:'#1e3a5f', border:'1px solid #2980b9', borderRadius:'4px', color:'#7fb3d3', cursor:'pointer', fontSize:'0.7rem' }}>
                    ✏ Edit
                  </button>
                  <button onClick={() => setDeleteConfirm(tc.id)}
                    style={{ padding:'0.25rem 0.55rem', background:'#3b0000', border:'1px solid #7f1d1d', borderRadius:'4px', color:'#f87171', cursor:'pointer', fontSize:'0.7rem' }}>
                    🗑
                  </button>
                </div>
              </div>

              <div style={{ fontSize:'0.82rem', fontWeight:600, color:'#e2e8f0', marginBottom:'0.6rem' }}>{tc.title}</div>

              <ol style={{ margin:'0', paddingLeft:'1.25rem' }}>
                {cleanSteps([...tc.given, ...tc.when, ...tc.then]).map((s, i) => (
                  <li key={i} style={{ fontSize:'0.78rem', color:'#94a3b8', marginBottom:'0.25rem', lineHeight:'1.5' }}>{s}</li>
                ))}
              </ol>
            </div>
          ))}
        </div>
      )}

      {/* ── Gherkin tab ── */}
      {tab === 'gherkin' && (
        <div className="card">
          <div className="card-title" style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
            <span>{result.feature_name}</span>
            <span style={{ fontWeight:400, fontSize:'0.75rem', color:'#64748b' }}>
              {val?.scenario_count ?? 0} scenarios
              {(gr?.review_loops ?? 0) > 0 && <span style={{ color:'#4ade80', marginLeft:'0.5rem' }}>· {gr.review_loops} review loop</span>}
            </span>
          </div>
          {val?.warnings?.length > 0 && (
            <div style={{ marginBottom:'0.75rem' }}>
              {val.warnings.map((w: string, i: number) => (
                <div key={i} className="badge badge-warn" style={{ marginRight:'0.4rem', marginBottom:'0.3rem' }}>{w}</div>
              ))}
            </div>
          )}
          <pre className="code-block">{gr?.gherkin_text}</pre>
        </div>
      )}

      {/* ── TypeScript tab ── */}
      {tab === 'playwright' && (
        <div>
          <div style={{ background:'#0a0f1a', border:'1px solid #1e3a5f', borderRadius:'8px', padding:'0.75rem 1rem', marginBottom:'1rem', fontSize:'0.75rem', color:'#64748b' }}>
            Place spec + config in project root, page object in <code style={{ color:'#4ade80' }}>pages/</code> →
            run <code style={{ color:'#fbbf24' }}>npx playwright test {safe}.spec.ts</code>
          </div>

          {[
            { label: `${safe}.spec.ts`, content: tr?.spec_ts, filename: `${safe}.spec.ts` },
            { label: `pages/${safe.replace(/_/g,'')}Page.ts`, content: tr?.page_object_ts, filename: `${safe.replace(/_/g,'')}Page.ts` },
            { label: `playwright.config.ts`, content: tr?.playwright_config, filename: 'playwright.config.ts' },
          ].map(({ label, content, filename }) => content ? (
            <div key={filename} className="card">
              <div className="card-title" style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                <span style={{ fontFamily:'Consolas,monospace', fontSize:'0.82rem' }}>{label}</span>
                <div style={{ display:'flex', gap:'0.5rem' }}>
                  <button onClick={() => navigator.clipboard?.writeText(content)}
                    style={{ padding:'0.25rem 0.65rem', background:'#1e293b', border:'1px solid #334155', borderRadius:'4px', color:'#94a3b8', cursor:'pointer', fontSize:'0.7rem' }}>
                    Copy
                  </button>
                  <button onClick={() => downloadFile(content, filename)}
                    style={{ padding:'0.25rem 0.65rem', background:'#1e3a5f', border:'1px solid #2980b9', borderRadius:'4px', color:'#7fb3d3', cursor:'pointer', fontSize:'0.7rem' }}>
                    ⬇ Download
                  </button>
                </div>
              </div>
              <pre className="code-block" style={{ maxHeight:'420px', overflow:'auto' }}>{content}</pre>
            </div>
          ) : null)}
        </div>
      )}

      {/* ── Risk tab ── */}
      {tab === 'risk' && (
        <div>
          {/* Risk level badge */}
          <div className="card" style={{
            borderColor: de?.risk_level?.toUpperCase() === 'HIGH' ? '#7f1d1d' : de?.risk_level?.toUpperCase() === 'MEDIUM' ? '#78350f' : '#14532d',
            marginBottom:'0.75rem',
          }}>
            <div style={{ display:'flex', alignItems:'center', gap:'1rem' }}>
              <div>
                <div style={{ fontSize:'0.7rem', color:'#64748b', marginBottom:'0.25rem', textTransform:'uppercase', letterSpacing:'0.5px' }}>Domain Risk Level</div>
                <div style={{
                  fontSize:'1.4rem', fontWeight:700,
                  color: de?.risk_level?.toUpperCase() === 'HIGH' ? '#f87171' : de?.risk_level?.toUpperCase() === 'MEDIUM' ? '#fbbf24' : '#4ade80',
                }}>
                  {(de?.risk_level ?? 'UNKNOWN').toUpperCase()}
                </div>
              </div>
              <div style={{ fontSize:'0.78rem', color:'#64748b', lineHeight:'1.6' }}>
                {de?.risk_level?.toUpperCase() === 'HIGH'
                  ? 'Feature directly impacts crew safety or vessel seaworthiness. P1 failures must be resolved before departure.'
                  : de?.risk_level?.toUpperCase() === 'MEDIUM'
                  ? 'Feature has compliance implications. Failures should be scheduled for the next sprint.'
                  : 'Operational feature with low safety impact.'}
              </div>
            </div>
          </div>

          {rr && (
            <>
              {rr.dimensions && Object.keys(rr.dimensions).length > 0 && (
                <div className="card">
                  <div className="card-title">Quality Dimensions</div>
                  <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:'0.75rem' }}>
                    {Object.entries(rr.dimensions).map(([k, v]: [string, any]) => (
                      <div key={k} style={{ background:'#0a0f1a', borderRadius:'6px', padding:'0.75rem', textAlign:'center' }}>
                        <div style={{ fontSize:'1.4rem', fontWeight:700, color: v >= 80 ? '#4ade80' : v >= 60 ? '#fbbf24' : '#f87171' }}>{v}</div>
                        <div style={{ fontSize:'0.63rem', color:'#64748b', marginTop:'0.2rem', textTransform:'uppercase', letterSpacing:'0.5px' }}>{k.replace(/_/g,' ')}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {(rr.recommendations ?? []).length > 0 && (
                <div className="card">
                  <div className="card-title">Recommendations</div>
                  {rr.recommendations.map((r: string, i: number) => (
                    <div key={i} style={{ fontSize:'0.8rem', color:'#94a3b8', marginBottom:'0.4rem', paddingLeft:'0.75rem', borderLeft:'2px solid #1e3a5f' }}>{r}</div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Audit tab ── */}
      {tab === 'audit' && (
        <div>
          {!audit ? (
            <div style={{ color:'#475569', fontSize:'0.82rem', padding:'2rem 0', textAlign:'center' }}>
              Audit report will appear after the pipeline completes.
            </div>
          ) : (
            <>
              <div className="metrics-row" style={{ gridTemplateColumns:'repeat(3,1fr)' }}>
                <div className="metric-card">
                  <div className={`metric-value ${(audit.overall_score ?? 0) >= 80 ? 'green' : (audit.overall_score ?? 0) >= 60 ? 'yellow' : 'red'}`}>
                    {audit.overall_score ?? 0}
                  </div>
                  <div className="metric-label">Audit Score /100</div>
                </div>
                <div className="metric-card">
                  <div className={`metric-value ${(audit.p1_coverage_pct ?? 0) >= 100 ? 'green' : 'red'}`}>
                    {audit.p1_coverage_pct ?? 0}%
                  </div>
                  <div className="metric-label">P1 Safety Coverage</div>
                </div>
                <div className="metric-card">
                  <div className="metric-value red">
                    {(audit.coverage_gaps ?? []).filter((g: any) => g.priority === 'P1').length}
                  </div>
                  <div className="metric-label">Critical Gaps</div>
                </div>
              </div>

              {audit.executive_summary && (
                <div className="card">
                  <div className="card-title">Executive Summary</div>
                  <div style={{ fontSize:'0.82rem', color:'#94a3b8', lineHeight:'1.6' }}>{audit.executive_summary}</div>
                </div>
              )}

              {(audit.coverage_gaps ?? []).length > 0 && (
                <div className="card" style={{ borderColor:'#7f1d1d' }}>
                  <div className="card-title" style={{ color:'#f87171' }}>Coverage Gaps ({audit.coverage_gaps.length})</div>
                  <table className="data-table">
                    <thead>
                      <tr><th style={{ width:'70px' }}>Priority</th><th>Gap</th><th style={{ width:'90px' }}>Regulation</th><th>Recommendation</th></tr>
                    </thead>
                    <tbody>
                      {audit.coverage_gaps.map((g: any, i: number) => (
                        <tr key={i}>
                          <td><span className={`badge badge-${(g.priority ?? 'p3').toLowerCase()}`}>{g.priority}</span></td>
                          <td style={{ fontSize:'0.75rem' }}>{g.gap}</td>
                          <td style={{ fontSize:'0.68rem', color:'#64748b' }}>{g.regulation ?? '—'}</td>
                          <td style={{ fontSize:'0.72rem', color:'#7fb3d3' }}>{g.recommendation}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {(audit.traceability_matrix ?? []).length > 0 && (
                <div className="card">
                  <div className="card-title">Traceability Matrix</div>
                  <table className="data-table">
                    <thead>
                      <tr><th style={{ width:'50px' }}>ID</th><th>Requirement</th><th>Mapped Scenario</th><th style={{ width:'70px' }}>Reg</th><th style={{ width:'80px' }}>Status</th></tr>
                    </thead>
                    <tbody>
                      {audit.traceability_matrix.map((m: any, i: number) => (
                        <tr key={i}>
                          <td style={{ fontFamily:'Consolas,monospace', fontSize:'0.7rem', color:'#7fb3d3' }}>{m.req_id}</td>
                          <td style={{ fontSize:'0.75rem' }}>{m.requirement}</td>
                          <td style={{ fontSize:'0.72rem', color: m.scenario ? '#4ade80' : '#f87171' }}>
                            {m.scenario ?? '— NOT COVERED —'}
                          </td>
                          <td style={{ fontSize:'0.68rem', color:'#64748b' }}>{m.regulation ?? '—'}</td>
                          <td>
                            <span className={`badge ${m.status === 'covered' ? 'badge-p2' : m.status === 'partial' ? 'badge-warn' : 'badge-p1'}`}>
                              {m.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {(audit.recommendations ?? []).length > 0 && (
                <div className="card">
                  <div className="card-title">Recommendations</div>
                  {audit.recommendations.map((r: string, i: number) => (
                    <div key={i} style={{ fontSize:'0.8rem', color:'#94a3b8', marginBottom:'0.4rem', paddingLeft:'0.75rem', borderLeft:'2px solid #1e40af' }}>
                      {r}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
