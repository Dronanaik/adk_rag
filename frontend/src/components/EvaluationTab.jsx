import { useEffect, useState } from 'react'
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  ClipboardCheck,
  ExternalLink,
  Loader2,
  Play,
  Plus,
  Sparkles,
  Trash2,
} from 'lucide-react'
import { generateEvalDataset, getEvalRuns, runEvaluation } from '../api.js'
import styles from './EvaluationTab.module.css'

const AVAILABLE_TOOLS = [
  'vector_search',
  'hybrid_search',
  'graph_search',
  'get_entity_relationships',
]

const METRIC_LABELS = {
  faithfulness: 'Faithfulness',
  context_relevance: 'Context Relevance',
  answer_correctness: 'Answer Correctness',
  tool_routing: 'Tool Routing',
  citation_compliance: 'Citations',
}

function scoreTone(score) {
  if (score >= 0.8) return { text: styles.scoreHigh, fill: styles.fillHigh }
  if (score >= 0.5) return { text: styles.scoreMid, fill: styles.fillMid }
  return { text: styles.scoreLow, fill: styles.fillLow }
}

function formatPct(score) {
  return `${Math.round((Number(score) || 0) * 100)}%`
}

export default function EvaluationTab({ userId }) {
  const [status, setStatus] = useState({
    langsmith_configured: false,
    tracing_enabled: false,
    project: 'adk-agentic-rag',
    judge_model: 'gemini-2.5-flash',
  })
  const [numQuestions, setNumQuestions] = useState(5)
  const [datasetName, setDatasetName] = useState('adk-rag-eval-dataset')
  const [examples, setExamples] = useState([])
  const [runs, setRuns] = useState([])
  const [selectedRunId, setSelectedRunId] = useState(null)
  const [expandedCases, setExpandedCases] = useState({})
  const [generating, setGenerating] = useState(false)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    getEvalRuns(userId)
      .then((res) => {
        if (!active || !res) return
        setStatus({
          langsmith_configured: Boolean(res.langsmith_configured),
          tracing_enabled: Boolean(res.tracing_enabled),
          project: res.project || 'adk-agentic-rag',
          judge_model: res.judge_model || 'gemini-2.5-flash',
        })
        if (Array.isArray(res.runs) && res.runs.length > 0) {
          setRuns(res.runs)
          setSelectedRunId(res.runs[0].run_id)
        }
      })
      .catch(() => {
        // Non-blocking on initial mount
      })
    return () => {
      active = false
    }
  }, [userId])

  async function handleGenerateDataset() {
    setError('')
    setGenerating(true)
    try {
      const res = await generateEvalDataset(userId, numQuestions)
      setExamples(Array.isArray(res?.examples) ? res.examples : [])
    } catch (err) {
      setError(err.message || 'Failed to generate evaluation dataset.')
    } finally {
      setGenerating(false)
    }
  }

  function handleAddCase() {
    const nextIdx = examples.length + 1
    setExamples((prev) => [
      ...prev,
      {
        id: `case-${nextIdx}`,
        question: '',
        expected_answer: '',
        expected_sources: [],
        expected_tools: ['hybrid_search'],
      },
    ])
  }

  function handleRemoveCase(index) {
    setExamples((prev) => prev.filter((_, idx) => idx !== index))
  }

  function handleUpdateCase(index, field, value) {
    setExamples((prev) =>
      prev.map((item, idx) => (idx === index ? { ...item, [field]: value } : item))
    )
  }

  function handleToggleTool(index, toolName) {
    setExamples((prev) =>
      prev.map((item, idx) => {
        if (idx !== index) return item
        const current = Array.isArray(item.expected_tools) ? item.expected_tools : []
        const exists = current.includes(toolName)
        return {
          ...item,
          expected_tools: exists
            ? current.filter((t) => t !== toolName)
            : [...current, toolName],
        }
      })
    )
  }

  async function handleRunEvaluation() {
    const validCases = examples.filter((ex) => ex.question && ex.question.trim())
    if (validCases.length === 0) {
      setError('Add or generate at least one non-empty question before running evaluation.')
      return
    }

    setError('')
    setRunning(true)
    try {
      const res = await runEvaluation(
        {
          dataset_name: datasetName.trim() || 'adk-rag-eval-dataset',
          experiment_prefix: 'adk-rag-eval',
          examples: validCases,
        },
        userId
      )
      if (res?.run) {
        setRuns((prev) => [res.run, ...prev])
        setSelectedRunId(res.run.run_id)
        const firstCase = res.run.cases?.[0]?.id
        if (firstCase) {
          setExpandedCases({ [firstCase]: true })
        }
      }
    } catch (err) {
      setError(err.message || 'Evaluation run failed.')
    } finally {
      setRunning(false)
    }
  }

  function toggleCaseExpand(caseId) {
    setExpandedCases((prev) => ({ ...prev, [caseId]: !prev[caseId] }))
  }

  const activeRun = runs.find((r) => r.run_id === selectedRunId) || runs[0] || null

  return (
    <div className={styles.wrap}>
      <div className={styles.headerRow}>
        <div>
          <h2 className={styles.title}>RAG Evaluation &amp; LangSmith</h2>
          <p className={styles.sub}>
            Generate grounded Golden Datasets from your indexed documents, run the ADK Agentic RAG
            pipeline, and score Faithfulness, Context Relevance, Correctness, Tool Routing, and Citations
            with <strong>{status.judge_model}</strong>.
          </p>
        </div>

        <div
          className={`${styles.statusPill} ${
            status.langsmith_configured ? styles.statusConnected : styles.statusLocal
          }`}
        >
          {status.langsmith_configured ? (
            <>
              <CheckCircle2 size={15} />
              <span>LangSmith Connected ({status.project})</span>
            </>
          ) : (
            <>
              <Activity size={15} />
              <span>Local Gemini 2.5 Flash Judge</span>
            </>
          )}
        </div>
      </div>

      {error && (
        <div className={styles.bannerError}>
          <AlertTriangle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Dataset Builder & Runner Controls */}
      <section className={styles.card}>
        <div className={styles.toolbar}>
          <div className={styles.toolbarGroup}>
            <select
              className={styles.select}
              aria-label="Number of questions to generate"
              value={numQuestions}
              onChange={(e) => setNumQuestions(Number(e.target.value))}
              disabled={generating || running}
            >
              <option value={3}>3 Questions</option>
              <option value={5}>5 Questions</option>
              <option value={8}>8 Questions</option>
            </select>

            <button
              type="button"
              className={styles.btnSecondary}
              onClick={handleGenerateDataset}
              disabled={generating || running}
            >
              {generating ? <Loader2 size={15} className={styles.spin} /> : <Sparkles size={15} />}
              <span>{generating ? 'Generating...' : 'Generate Golden Dataset'}</span>
            </button>

            <button
              type="button"
              className={styles.btnGhost}
              onClick={handleAddCase}
              disabled={generating || running}
            >
              <Plus size={15} />
              <span>Add Question</span>
            </button>
          </div>

          <div className={styles.toolbarGroup}>
            <input
              type="text"
              className={styles.input}
              aria-label="LangSmith dataset name"
              value={datasetName}
              onChange={(e) => setDatasetName(e.target.value)}
              placeholder="adk-rag-eval-dataset"
              disabled={running}
            />

            <button
              type="button"
              className={styles.btnPrimary}
              onClick={handleRunEvaluation}
              disabled={running || generating || examples.length === 0}
            >
              {running ? <Loader2 size={15} className={styles.spin} /> : <Play size={15} />}
              <span>{running ? 'Evaluating...' : 'Run Evaluation'}</span>
            </button>
          </div>
        </div>

        {examples.length === 0 ? (
          <div className={styles.emptyState}>
            <ClipboardCheck size={28} style={{ opacity: 0.5, marginBottom: 8 }} />
            <p>
              Click <strong>Generate Golden Dataset</strong> to synthesize grounded Q&amp;A test cases
              from your uploaded documents, or click <strong>Add Question</strong> to author custom cases.
            </p>
          </div>
        ) : (
          <div className={styles.caseList}>
            {examples.map((ex, idx) => (
              <div key={ex.id || idx} className={styles.caseItem}>
                <div className={styles.caseTop}>
                  <span className={styles.caseBadge}>{ex.id || `case-${idx + 1}`}</span>
                  <div className={styles.toolChips}>
                    {AVAILABLE_TOOLS.map((tool) => {
                      const active = (ex.expected_tools || []).includes(tool)
                      return (
                        <button
                          key={tool}
                          type="button"
                          className={`${styles.toolChip} ${active ? styles.toolChipActive : ''}`}
                          onClick={() => handleToggleTool(idx, tool)}
                        >
                          {tool}
                        </button>
                      )
                    })}
                  </div>
                  <button
                    type="button"
                    className={styles.iconBtnDanger}
                    aria-label="Remove test case"
                    onClick={() => handleRemoveCase(idx)}
                  >
                    <Trash2 size={15} />
                  </button>
                </div>

                <div className={styles.fieldGrid}>
                  <div>
                    <label className={styles.fieldLabel}>Question</label>
                    <textarea
                      className={styles.textarea}
                      value={ex.question}
                      onChange={(e) => handleUpdateCase(idx, 'question', e.target.value)}
                      placeholder="Enter a question for the ADK Agent..."
                    />
                  </div>
                  <div>
                    <label className={styles.fieldLabel}>Expected Answer (Ground Truth)</label>
                    <textarea
                      className={styles.textarea}
                      value={ex.expected_answer}
                      onChange={(e) => handleUpdateCase(idx, 'expected_answer', e.target.value)}
                      placeholder="Concise reference answer..."
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Evaluation Results */}
      {activeRun && (
        <section className={styles.card}>
          <div className={styles.resultsHeader}>
            <div className={styles.resultsTitle}>
              <ClipboardCheck size={18} style={{ color: 'var(--accent-primary)' }} />
              <span>Experiment Results</span>
              <span className={styles.caseBadge}>{activeRun.experiment_name}</span>
            </div>

            <div className={styles.toolbarGroup}>
              {runs.length > 1 && (
                <select
                  className={styles.select}
                  aria-label="Select evaluation run"
                  value={activeRun.run_id}
                  onChange={(e) => setSelectedRunId(e.target.value)}
                >
                  {runs.map((r) => (
                    <option key={r.run_id} value={r.run_id}>
                      {r.experiment_name} ({formatPct(r.summary?.overall_score)})
                    </option>
                  ))}
                </select>
              )}

              {activeRun.langsmith_url && (
                <a
                  href={activeRun.langsmith_url}
                  target="_blank"
                  rel="noreferrer"
                  className={styles.langsmithLink}
                >
                  <span>Open in LangSmith</span>
                  <ExternalLink size={14} />
                </a>
              )}
            </div>
          </div>

          {activeRun.langsmith_warning && (
            <div className={styles.bannerWarn} style={{ marginBottom: 14 }}>
              <AlertTriangle size={16} />
              <span>{activeRun.langsmith_warning}</span>
            </div>
          )}

          <div className={styles.metricsGrid}>
            {Object.entries(METRIC_LABELS).map(([key, label]) => {
              const score = activeRun.summary?.[key] ?? 0
              const tone = scoreTone(score)
              return (
                <div key={key} className={styles.metricCard}>
                  <span className={styles.metricLabel}>{label}</span>
                  <span className={`${styles.metricValue} ${tone.text}`}>{formatPct(score)}</span>
                  <div className={styles.progressTrack}>
                    <div
                      className={`${styles.progressFill} ${tone.fill}`}
                      style={{ width: `${Math.round(score * 100)}%` }}
                    />
                  </div>
                </div>
              )
            })}

            <div className={styles.metricCard}>
              <span className={styles.metricLabel}>Overall / Latency</span>
              <span
                className={`${styles.metricValue} ${
                  scoreTone(activeRun.summary?.overall_score ?? 0).text
                }`}
              >
                {formatPct(activeRun.summary?.overall_score ?? 0)}
              </span>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                Avg {activeRun.summary?.avg_latency_ms ?? 0} ms · {activeRun.summary?.total_cases ?? 0}{' '}
                cases
              </span>
            </div>
          </div>

          <div className={styles.breakdownList}>
            {(activeRun.cases || []).map((c) => {
              const isOpen = Boolean(expandedCases[c.id])
              const tone = scoreTone(c.overall_score)
              return (
                <div key={c.id} className={styles.breakdownCard}>
                  <button
                    type="button"
                    className={styles.breakdownSummary}
                    onClick={() => toggleCaseExpand(c.id)}
                  >
                    <span className={styles.breakdownQ}>
                      {isOpen ? (
                        <ChevronDown size={15} style={{ verticalAlign: 'middle', marginRight: 6 }} />
                      ) : (
                        <ChevronRight size={15} style={{ verticalAlign: 'middle', marginRight: 6 }} />
                      )}
                      {c.question}
                    </span>

                    <div className={styles.breakdownRight}>
                      <span className={styles.caseBadge}>
                        {(c.tools_used || []).join(', ') || 'no tools'}
                      </span>
                      <span className={`${styles.scorePill} ${tone.text}`}>
                        {formatPct(c.overall_score)}
                      </span>
                    </div>
                  </button>

                  {isOpen && (
                    <div className={styles.breakdownBody}>
                      <div className={styles.metaRow}>
                        <span>Latency: {c.latency_ms} ms</span>
                        <span>·</span>
                        <span>Retrieved Contexts: {c.contexts_count}</span>
                        {c.expected_sources?.length > 0 && (
                          <>
                            <span>·</span>
                            <span>Expected Sources: {c.expected_sources.join(', ')}</span>
                          </>
                        )}
                      </div>

                      <div>
                        <span className={styles.fieldLabel}>Agent Answer</span>
                        <div className={styles.answerBox}>{c.answer}</div>
                      </div>

                      <div className={styles.judgeList}>
                        {Object.entries(METRIC_LABELS).map(([key, label]) => {
                          const m = c.metrics?.[key] || { score: 0, comment: '' }
                          const mTone = scoreTone(m.score)
                          return (
                            <div key={key} className={styles.judgeItem}>
                              <div className={styles.judgeTop}>
                                <span>{label}</span>
                                <span className={mTone.text}>{formatPct(m.score)}</span>
                              </div>
                              <p className={styles.judgeComment}>{m.comment}</p>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </section>
      )}
    </div>
  )
}
