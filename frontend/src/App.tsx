import { useState, useCallback } from 'react'
import Sidebar from './components/Sidebar'
import PipelinePanel from './components/PipelinePanel'
import OutputPanel from './components/OutputPanel'
import MemoryPanel from './components/MemoryPanel'
import KnowledgeBasePanel from './components/KnowledgeBasePanel'
import './App.css'

export type Tab = 'pipeline' | 'output' | 'memory' | 'knowledge'

export interface PipelineResult {
  success: boolean
  feature_name: string
  domain_enrichment?: any
  requirements?: any
  gherkin_result?: any
  test_result?: any
  audit_result?: any
}

function App() {
  const [activeTab, setActiveTab]     = useState<Tab>('pipeline')
  const [result, setResult]           = useState<PipelineResult | null>(null)
  const [isRunning, setIsRunning]     = useState(false)
  const [logs, setLogs]               = useState<string[]>([])
  const [agentProgress, setAgentProgress] = useState<Record<string, number>>({
    'Maritime Domain Expert': 0,
    'Test Strategist': 0,
    'Automation Engineer': 0,
    'QA Auditor': 0,
  })

  const appendLog = useCallback((msg: string) => {
    setLogs(prev => [...prev.slice(-200), msg])
    const lower = msg.toLowerCase()
    if (lower.includes('maritime domain expert') || lower.includes('domain expert')) {
      setAgentProgress(p => ({ ...p, 'Maritime Domain Expert': lower.includes('complete') ? 100 : 50 }))
    } else if (lower.includes('test strategist')) {
      setAgentProgress(p => ({ ...p, 'Test Strategist': lower.includes('complete') ? 100 : 50 }))
    } else if (lower.includes('automation engineer')) {
      setAgentProgress(p => ({ ...p, 'Automation Engineer': lower.includes('complete') ? 100 : 50 }))
    } else if (lower.includes('qa auditor')) {
      setAgentProgress(p => ({ ...p, 'QA Auditor': lower.includes('complete') ? 100 : 50 }))
    }
  }, [])

  const onPipelineProgress = useCallback((partial: PipelineResult) => {
    setResult(partial)
  }, [])

  const onPipelineComplete = useCallback((res: PipelineResult) => {
    setResult(res)
    setIsRunning(false)
    setAgentProgress({
      'Maritime Domain Expert': 100,
      'Test Strategist': 100,
      'Automation Engineer': 100,
      'QA Auditor': 100,
    })
    if (res.success) setActiveTab('output')
  }, [])

  const onPipelineStart = useCallback(() => {
    setIsRunning(true)
    setLogs([])
    setResult(null)
    setAgentProgress({
      'Maritime Domain Expert': 0,
      'Test Strategist': 0,
      'Automation Engineer': 0,
      'QA Auditor': 0,
    })
  }, [])

  return (
    <div className="app-shell">
      <header className="top-bar">
        <div className="brand">
          <span className="brand-icon">🚢</span>
          <span className="brand-name">MarineQA Pilot</span>
          <span className="brand-sub">AI-Powered Maritime Test Automation</span>
        </div>
        <div className="nav-tabs">
          {(['pipeline', 'output', 'memory', 'knowledge'] as Tab[]).map(tab => (
            <button
              key={tab}
              className={`nav-tab ${activeTab === tab ? 'active' : ''}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab === 'pipeline'   && '⚙️ Pipeline'}
              {tab === 'output'     && '📄 Output'}
              {tab === 'memory'     && '🧠 Memory'}
              {tab === 'knowledge'  && '📚 KB'}
              {tab === 'output' && result?.success && <span className="dot-green" />}
            </button>
          ))}
        </div>
      </header>

      <div className="main-layout">
        <Sidebar
          agentProgress={agentProgress}
          isRunning={isRunning}
          logs={logs}
          result={result}
        />
        <main className="content-area">
          {activeTab === 'pipeline'  && (
            <PipelinePanel
              onStart={onPipelineStart}
              onComplete={onPipelineComplete}
              onProgress={onPipelineProgress}
              onLog={appendLog}
              isRunning={isRunning}
            />
          )}
          {activeTab === 'output'    && <OutputPanel result={result} />}
          {activeTab === 'memory'    && <MemoryPanel />}
          {activeTab === 'knowledge' && <KnowledgeBasePanel />}
        </main>
      </div>
    </div>
  )
}

export default App
