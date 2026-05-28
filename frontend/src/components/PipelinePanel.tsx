import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import type { PipelineResult } from '../App'

interface Props {
  onStart:    () => void
  onComplete: (result: PipelineResult) => void
  onProgress: (partial: PipelineResult) => void
  onLog:      (msg: string) => void
  isRunning:  boolean
}

type InputSource = 'manual' | 'jira'

interface JiraIssue {
  issue_key:           string
  summary:             string
  description:         string
  acceptance_criteria: string
  priority:            string
  labels:              string[]
  issue_type:          string
  status:              string
  assignee:            string
  url:                 string
  feature_name:        string
  feature_description: string
}

const SAMPLE_FEATURES = [
  'crew_certification',
  'fatigue_management',
  'incident_reporting',
  'voyage_planning',
]

const SAMPLE_TEXTS: Record<string, string> = {
  crew_certification: `Feature: Crew Certification Management
As a ship master, I need to manage crew certifications so the vessel complies with STCW regulations.

The app shows a certification register table (Name, Rank, Certificate, Expiry Date, Days Remaining, Status).
Expired certificates trigger a red VESSEL DEPARTURE BLOCKED banner at the top of the page.
Certificates within 30 days of expiry trigger a yellow EXPIRY ALERT warning banner.
The table can be filtered by status: All / Expired / Expiring Soon / Valid using a dropdown.
Each row shows a status badge: Expired (red), Expiring Soon (yellow), or Valid (green).

To renew a certificate: click the Renew button on any row, fill in New Expiry Date and Certificate Number in the modal, then click Update Certificate. A green success flash message confirms the update and the status badge changes to Valid.

Test with: expired crew causing departure block, filter to see only expired certs, renew a cert and verify the departure block disappears.`,

  fatigue_management: `Feature: Fatigue Management and Rest Hour Monitoring
As a safety officer, I need to monitor crew rest hours to comply with MLC 2006 Regulation 2.3 (minimum 10 hours rest per 24-hour period, 77 hours per 7-day period).

The app shows a list of all officers with their fatigue status (Compliant / Violation).
Officers with rest-hour violations show a red departure-block banner and a violation badge.
Compliant officers show a green compliant badge.

To log rest hours: select an officer from the dropdown, enter Rest Start and Rest End datetime values, then click Log Rest Hours. A success flash message confirms the entry.

Officers in violation have a Reassign button to move them off watch duty.

Test with: verifying violation banners appear for non-compliant officers, logging rest hours for an officer, verifying the success message.`,

  incident_reporting: `Feature: Maritime Incident Reporting and ISM Compliance
As a safety officer, I need to report and review maritime incidents per ISM Code Section 9.

The app shows an incident list with severity (High/Medium/Low), status (Pending Review / Approved), and deadline. Incidents with overdue review deadlines show a red departure-block banner.

To report a new incident: click Report Incident, select type (Near Miss / Collision / Injury / Fire / Pollution) and severity (High / Medium / Low), enter vessel name, location, and description, then click Submit. A success flash message confirms and the incident appears in the list with Pending Review status.

To review an incident: find it in the list, click Review, enter officer review comments, optionally check Notify Maritime Authority, then click Submit Review. The status changes to Approved.

Test with: verifying overdue incidents show departure block, reporting a Near Miss, reviewing and approving an incident with authority notification.`,

  voyage_planning: `Feature: Voyage Planning
As a navigator, I need to plan voyages and manage route safety compliance.

The app shows a voyage register table (Voyage ID, Vessel, Route, Departure Date, ETA, Distance nm, Bunker MT, ECA Zones, Status).
Active voyages through piracy high-risk areas show a red PIRACY ALERT departure-block banner.
ECA zone compliance is shown as a badge per voyage (yellow ECA count badge or green None).

To plan a new voyage: click Plan New Voyage, select vessel (MV Oceanic Pioneer / MV Star Nour) and fuel type (VLSFO / MGO / LNG), enter departure port, arrival port, departure date, speed in knots, bunker quantity in MT, and distance in nautical miles, then click Create Voyage Plan. A success flash message confirms.

Voyage details (click Details button) show fuel planning table, ECA zone compliance status, and a weather deviation alert. When a deviation is recommended, click Confirm Route Deviation to acknowledge.

Test with: viewing piracy alert for existing voyage, planning a new voyage and verifying it appears in the table, confirming a route deviation.`,
}

const PRIORITY_COLOR: Record<string, string> = {
  Highest: '#f87171',
  High:    '#fb923c',
  Medium:  '#fbbf24',
  Low:     '#4ade80',
  Lowest:  '#94a3b8',
}

export default function PipelinePanel({ onStart, onComplete, onProgress, onLog, isRunning }: Props) {
  const [source,          setSource]          = useState<InputSource>('manual')
  const [featureName,     setFeatureName]     = useState('')
  const [featureText,     setFeatureText]     = useState('')
  const [selectedSample,  setSelectedSample]  = useState('')
  const [error,           setError]           = useState('')

  // JIRA state
  const [jiraKey,         setJiraKey]         = useState('')
  const [jiraIssue,       setJiraIssue]       = useState<JiraIssue | null>(null)
  const [jiraLoading,     setJiraLoading]     = useState(false)
  const [jiraError,       setJiraError]       = useState('')

  const evtRef = useRef<EventSource | null>(null)

  useEffect(() => {
    return () => { evtRef.current?.close() }
  }, [])

  function loadSample(name: string) {
    setSelectedSample(name)
    setFeatureName(name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()))
    setFeatureText(SAMPLE_TEXTS[name] ?? '')
    setError('')
  }

  async function fetchFromJira() {
    const key = jiraKey.trim().toUpperCase()
    if (!key) { setJiraError('Enter a JIRA issue key, e.g. MARINE-42'); return }
    setJiraLoading(true)
    setJiraError('')
    setJiraIssue(null)
    try {
      const resp = await axios.get<JiraIssue>(`/api/jira/fetch?issue_key=${encodeURIComponent(key)}`)
      setJiraIssue(resp.data)
      setFeatureName(resp.data.feature_name)
      setFeatureText(resp.data.feature_description)
      setError('')
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? err.message ?? 'Failed to fetch JIRA issue'
      setJiraError(detail)
    } finally {
      setJiraLoading(false)
    }
  }

  function handleJiraKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') fetchFromJira()
  }

  async function runPipeline() {
    if (!featureName.trim() || !featureText.trim()) {
      setError(source === 'jira'
        ? 'Fetch a JIRA issue first, then click Run AI Pipeline.'
        : 'Please enter a feature name and description.')
      return
    }
    setError('')
    const runId = `run_${Date.now()}`

    try {
      onStart()
      await axios.post('/api/pipeline/run', {
        feature_name: featureName.trim(),
        feature_text: featureText.trim(),
        run_id: runId,
      })

      const es = new EventSource(`/api/pipeline/stream/${runId}`)
      evtRef.current = es

      es.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data)
          if (data.type === 'log') {
            onLog(data.message)
          } else if (data.type === 'progress') {
            const nodeMap: Record<string, string> = {
              maritime_domain:    'Maritime Domain Expert',
              test_strategist:    'Test Strategist',
              automation_engineer:'Automation Engineer',
              qa_auditor:         'QA Auditor',
            }
            if (data.agent && nodeMap[data.agent]) {
              onLog(`[${nodeMap[data.agent]}] complete`)
            }
            onProgress(data.partial)
          } else if (data.type === 'done') {
            es.close()
            if (data.result?.success) {
              onComplete(data.result)
            } else {
              const errMsg = data.result?.error ?? 'Pipeline failed'
              setError(errMsg)
              onLog(`ERROR: ${errMsg}`)
              onComplete({ success: false, feature_name: featureName, error: errMsg } as any)
            }
          }
        } catch { /* ignore parse errors */ }
      }

      es.onerror = () => {
        es.close()
        setError('Connection to pipeline lost. Check the backend is running.')
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? err.message ?? 'Failed to start pipeline')
    }
  }

  return (
    <div>
      <div className="page-title">QA Pipeline</div>
      <div className="page-sub">The 4-agent AI pipeline generates Gherkin BDD scenarios, TypeScript Playwright tests, and a QA audit report</div>

      {/* ── Input Source Toggle ── */}
      <div className="card" style={{ padding:'0.75rem 1rem' }}>
        <div style={{ display:'flex', gap:'0.5rem', alignItems:'center' }}>
          <span style={{ fontSize:'0.72rem', color:'#64748b', marginRight:'0.25rem' }}>Input source:</span>
          {(['manual', 'jira'] as InputSource[]).map(s => (
            <button
              key={s}
              onClick={() => { setSource(s); setError(''); setJiraError('') }}
              style={{
                padding:'0.35rem 0.9rem',
                borderRadius:'5px',
                border:`1px solid ${source === s ? '#2980b9' : '#1e3a5f'}`,
                background: source === s ? '#1e3a5f' : 'transparent',
                color: source === s ? '#7fb3d3' : '#475569',
                cursor:'pointer',
                fontSize:'0.78rem',
                fontWeight: source === s ? 700 : 400,
              }}
            >
              {s === 'manual' ? '✏️ Manual Input' : '🔗 Fetch from JIRA'}
            </button>
          ))}
        </div>
      </div>

      {/* ── JIRA fetch panel ── */}
      {source === 'jira' && (
        <div className="card">
          <div className="card-title">JIRA Cloud — Fetch Issue</div>

          <div style={{ display:'flex', gap:'0.75rem', alignItems:'flex-start', marginBottom:'0.75rem' }}>
            <div style={{ flex:1 }}>
              <label className="form-label">Issue Key</label>
              <input
                className="form-input"
                placeholder="e.g. MARINE-42 or FLEET-101"
                value={jiraKey}
                onChange={e => setJiraKey(e.target.value)}
                onKeyDown={handleJiraKeyDown}
                style={{ fontFamily:'Consolas,monospace', letterSpacing:'0.5px' }}
              />
            </div>
            <div style={{ paddingTop:'1.55rem' }}>
              <button
                className="btn btn-primary"
                onClick={fetchFromJira}
                disabled={jiraLoading}
                style={{ minWidth:'110px' }}
              >
                {jiraLoading ? <><span className="spinner" style={{ marginRight:'0.4rem' }}/>Fetching…</> : '🔍 Fetch Issue'}
              </button>
            </div>
          </div>

          {jiraError && (
            <div style={{ color:'#f87171', fontSize:'0.82rem', marginBottom:'0.75rem', padding:'0.5rem 0.75rem', background:'#3b0000', borderRadius:'5px', border:'1px solid #7f1d1d' }}>
              {jiraError}
            </div>
          )}

          {jiraIssue && (
            <div style={{ background:'#0a0f1a', border:'1px solid #1e3a5f', borderRadius:'8px', padding:'1rem', marginTop:'0.25rem' }}>
              {/* Issue header */}
              <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:'0.75rem' }}>
                <div style={{ display:'flex', alignItems:'center', gap:'0.6rem', flexWrap:'wrap' }}>
                  <span style={{ fontFamily:'Consolas,monospace', fontSize:'0.75rem', color:'#2980b9', fontWeight:700 }}>
                    {jiraIssue.issue_key}
                  </span>
                  <span style={{ fontSize:'0.68rem', padding:'0.1rem 0.5rem', background:'#1e293b', border:'1px solid #334155', borderRadius:'3px', color:'#94a3b8' }}>
                    {jiraIssue.issue_type}
                  </span>
                  <span style={{ fontSize:'0.68rem', padding:'0.1rem 0.5rem', background:'#1e293b', border:'1px solid #334155', borderRadius:'3px', color:'#94a3b8' }}>
                    {jiraIssue.status}
                  </span>
                  <span style={{
                    fontSize:'0.68rem', padding:'0.1rem 0.5rem', borderRadius:'3px', fontWeight:700,
                    background: `${(PRIORITY_COLOR[jiraIssue.priority] ?? '#94a3b8')}22`,
                    color: PRIORITY_COLOR[jiraIssue.priority] ?? '#94a3b8',
                    border: `1px solid ${(PRIORITY_COLOR[jiraIssue.priority] ?? '#94a3b8')}55`,
                  }}>
                    {jiraIssue.priority}
                  </span>
                  {jiraIssue.labels.map(l => (
                    <span key={l} style={{ fontSize:'0.63rem', padding:'0.1rem 0.45rem', background:'#0f2027', border:'1px solid #1e3a5f', borderRadius:'3px', color:'#64748b' }}>
                      {l}
                    </span>
                  ))}
                </div>
                <a
                  href={jiraIssue.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ fontSize:'0.7rem', color:'#2980b9', textDecoration:'none', flexShrink:0 }}
                >
                  Open in JIRA ↗
                </a>
              </div>

              {/* Summary */}
              <div style={{ fontSize:'0.9rem', fontWeight:700, color:'#e2e8f0', marginBottom:'0.6rem' }}>
                {jiraIssue.summary}
              </div>

              {/* Assignee */}
              <div style={{ fontSize:'0.72rem', color:'#64748b', marginBottom:'0.75rem' }}>
                Assigned to: {jiraIssue.assignee}
              </div>

              {/* Description preview */}
              {jiraIssue.description && (
                <div style={{ marginBottom:'0.6rem' }}>
                  <div style={{ fontSize:'0.68rem', color:'#475569', textTransform:'uppercase', letterSpacing:'0.5px', marginBottom:'0.3rem' }}>Description</div>
                  <div style={{ fontSize:'0.78rem', color:'#94a3b8', lineHeight:1.6, whiteSpace:'pre-wrap', maxHeight:'120px', overflow:'auto' }}>
                    {jiraIssue.description}
                  </div>
                </div>
              )}

              {/* Acceptance criteria */}
              {jiraIssue.acceptance_criteria && (
                <div>
                  <div style={{ fontSize:'0.68rem', color:'#475569', textTransform:'uppercase', letterSpacing:'0.5px', marginBottom:'0.3rem' }}>Acceptance Criteria</div>
                  <div style={{ fontSize:'0.78rem', color:'#4ade80', lineHeight:1.6, whiteSpace:'pre-wrap', maxHeight:'100px', overflow:'auto' }}>
                    {jiraIssue.acceptance_criteria}
                  </div>
                </div>
              )}

              <div style={{ marginTop:'0.75rem', fontSize:'0.72rem', color:'#4ade80' }}>
                ✓ Feature name and description populated below — ready to run
              </div>
            </div>
          )}

          {!jiraIssue && !jiraLoading && !jiraError && (
            <div style={{ fontSize:'0.75rem', color:'#475569', marginTop:'0.25rem' }}>
              Make sure <code style={{ color:'#fbbf24' }}>JIRA_URL</code>, <code style={{ color:'#fbbf24' }}>JIRA_EMAIL</code>, and <code style={{ color:'#fbbf24' }}>JIRA_API_TOKEN</code> are set in your <code>.env</code> file.
            </div>
          )}
        </div>
      )}

      {/* ── Sample loader (manual mode only) ── */}
      {source === 'manual' && (
        <div className="card">
          <div className="card-title">Load Sample Maritime Feature</div>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {SAMPLE_FEATURES.map(name => (
              <button
                key={name}
                className={`btn btn-outline ${selectedSample === name ? 'active' : ''}`}
                style={selectedSample === name ? { borderColor: '#2980b9', color: '#7fb3d3' } : {}}
                onClick={() => loadSample(name)}
              >
                {name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Feature input (both modes) ── */}
      <div className="card">
        <div className="card-title">
          {source === 'jira' ? 'Fetched Feature Details' : 'Feature Description'}
          {source === 'jira' && jiraIssue && (
            <span style={{ fontSize:'0.7rem', fontWeight:400, color:'#64748b', marginLeft:'0.75rem' }}>
              from {jiraIssue.issue_key} — edit if needed
            </span>
          )}
        </div>

        <div className="form-group">
          <label className="form-label">Feature Name</label>
          <input
            className="form-input"
            placeholder="e.g. Crew Certification Management"
            value={featureName}
            onChange={e => setFeatureName(e.target.value)}
          />
        </div>
        <div className="form-group">
          <label className="form-label">
            {source === 'jira' ? 'Requirements (from JIRA — edit freely)' : 'Requirements (plain text or pasted from Jira)'}
          </label>
          <textarea
            className="form-textarea"
            rows={10}
            placeholder="Paste your requirements here — bullet points, user stories, or plain text. The pipeline will look up relevant maritime regulations automatically."
            value={featureText}
            onChange={e => setFeatureText(e.target.value)}
          />
        </div>

        {error && (
          <div style={{ color: '#f87171', fontSize: '0.82rem', marginBottom: '1rem' }}>
            {error}
          </div>
        )}

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <button
            className="btn btn-primary"
            disabled={isRunning}
            onClick={runPipeline}
          >
            {isRunning ? (
              <><span className="spinner" style={{ marginRight: '0.5rem' }} /> Running Pipeline…</>
            ) : (
              '▶ Run AI Pipeline'
            )}
          </button>
          {isRunning && (
            <span style={{ fontSize: '0.78rem', color: '#64748b' }}>
              4 agents processing — results stream in real-time to the sidebar (~90 sec)
            </span>
          )}
        </div>
      </div>

      {/* ── Pipeline Architecture ── */}
      <div className="card">
        <div className="card-title">Pipeline Architecture</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: '0.75rem' }}>
          {[
            { num: 1, name: 'Maritime Domain Expert', desc: 'Analyses STCW/MLC/ISM/MARPOL/SOLAS risks, PSC triggers, and boundary values using Groq 70B', color: '#f87171' },
            { num: 2, name: 'Test Strategist',        desc: 'Generates Gherkin BDD scenarios — Two-Deadline, Block-Override-Audit, Role-Escalation patterns', color: '#7fb3d3' },
            { num: 3, name: 'Automation Engineer',    desc: 'Converts Gherkin into TypeScript Playwright tests with real HTML locators from the mock app', color: '#4ade80' },
            { num: 4, name: 'QA Auditor',             desc: 'Builds traceability matrix, calculates P1/P2 coverage, scores the test suite 0–100', color: '#a78bfa' },
          ].map(a => (
            <div key={a.num} style={{
              background: '#0a0f1a',
              border: `1px solid ${a.color}33`,
              borderRadius: '8px',
              padding: '1rem',
            }}>
              <div style={{ fontSize: '0.65rem', color: a.color, fontWeight: 700, marginBottom: '0.3rem', textTransform: 'uppercase' }}>
                Agent {a.num}
              </div>
              <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#e2e8f0', marginBottom: '0.4rem' }}>{a.name}</div>
              <div style={{ fontSize: '0.72rem', color: '#64748b', lineHeight: 1.5 }}>{a.desc}</div>
            </div>
          ))}
        </div>
        <div style={{ marginTop: '0.75rem', fontSize: '0.75rem', color: '#475569' }}>
          Memory: Short-term (session cache) + Long-term (ChromaDB vector DB) · KB: IMO STCW, MLC 2006, ISM, MARPOL, SOLAS, FAL, BMP5 (16 regulations)
        </div>
      </div>
    </div>
  )
}
