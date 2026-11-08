import { useCallback, useEffect, useState } from 'react'
import {
  Activity,
  Box,
  CheckCircle2,
  XCircle,
  AlertCircle,
  RefreshCw,
  BookOpen,
  Scissors,
  Cpu,
  Database,
  Share2,
  Check,
  Clock,
} from 'lucide-react'
import { getIngestProgress, getIngestStatus } from '../api.js'
import styles from './IngestionTab.module.css'

const PIPELINE_STEPS = [
  {
    step: 1,
    name: 'Text Extraction',
    description: 'Reads the uploaded file and extracts raw text using format-specific parsers.',
    icon: BookOpen,
    detail: 'PyMuPDF, python-docx, openpyxl, python-pptx, plain reader',
  },
  {
    step: 2,
    name: 'Structure-Aware Semantic Chunking',
    description: 'Preserves headings and paragraphs while splitting text into 1200-character semantic chunks with 200-character overlap.',
    icon: Scissors,
    detail: 'chunk_size=1200, overlap=200 (paragraph & sentence aware)',
  },
  {
    step: 3,
    name: 'Gemini Embedding Generation',
    description: 'Each chunk is embedded in batches using Gemini embedding-001 model, producing 768-dimensional vectors.',
    icon: Cpu,
    detail: 'gemini-embedding-001, dimensionality=768',
  },
  {
    step: 4,
    name: 'Neon PostgreSQL Vector & Hybrid Storage',
    description: 'Chunks, 768-dim embeddings, and full-text search indexes are stored in Neon Console PostgreSQL (pgvector + tsvector).',
    icon: Database,
    detail: 'Neon PostgreSQL + pgvector HNSW + GIN Full-Text Search',
  },
  {
    step: 5,
    name: 'Neo4j Knowledge Graph Extraction',
    description: 'Gemini Structured Outputs extract domain entities and factual relationships and upsert them into your Neo4j Knowledge Graph.',
    icon: Share2,
    detail: 'gemini-2.5-flash structured output → Neo4j (:Entity)-[:RELATES_TO]->(:Entity)',
  },
]

export default function IngestionTab({ uploadState }) {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [liveProgress, setLiveProgress] = useState(null)

  const isUploading = uploadState?.status === 'uploading'
  const isCompleted = uploadState?.status === 'success'
  const isError = uploadState?.status === 'error'
  const totalDocs = uploadState?.totalDocs || liveProgress?.total_docs || 1
  const currentDocIndex = uploadState?.currentDocIndex || liveProgress?.doc_index || 1
  const currentFilename = uploadState?.currentFilename || liveProgress?.filename || ''

  const fetchStatus = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await getIngestStatus()
      setStatus(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStatus()
  }, [fetchStatus, uploadState?.status, uploadState?.currentDocIndex])

  // Reset per-document step progress when moving to the next document in a multi-file batch
  useEffect(() => {
    if (isUploading) {
      setLiveProgress(null)
    }
  }, [isUploading, uploadState?.currentDocIndex])

  // Poll live step-by-step progress while uploading
  useEffect(() => {
    if (!isUploading) {
      if (isCompleted) {
        getIngestProgress().then(setLiveProgress).catch((err) => { void err })
      }
      return
    }

    let cancelled = false
    const poll = async () => {
      try {
        const prog = await getIngestProgress()
        if (!cancelled) {
          setLiveProgress(prog)
        }
      } catch (err) {
        // Ignore transient polling errors while ingestion is in flight
        void err
      }
    }

    poll()
    const timer = setInterval(poll, 450)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [isUploading, isCompleted, uploadState?.currentDocIndex])

  const isMatchingDocProgress =
    !liveProgress?.doc_index || liveProgress.doc_index === currentDocIndex

  const activeProgress = isMatchingDocProgress ? liveProgress : null

  const activeStepNumber = isUploading
    ? activeProgress?.current_step || 1
    : isCompleted
    ? 6
    : 0

  const progressPercent = isUploading
    ? Math.min(95, Math.max(12, ((activeStepNumber - 1) / 5) * 100 + 15))
    : isCompleted
    ? 100
    : 0

  const ingestedCount =
    uploadState?.result?.documents_count || uploadState?.results?.length || 1

  return (
    <div className={`${styles.wrap} fade-in`}>
      <div className={styles.sectionHeader}>
        <h2 className={styles.title}>Hybrid Ingestion Pipeline</h2>
        <p className={styles.sub}>
          Documents pass through a 5-step Agentic RAG + Knowledge Graph pipeline into{' '}
          <strong>Neon PostgreSQL (pgvector)</strong> and <strong>Neo4j</strong>.
        </p>
      </div>

      {/* Live Step-by-Step Banner while Uploading */}
      {isUploading && (
        <div className={`glass-card ${styles.liveBanner}`}>
          <div className={styles.liveBannerTop}>
            <div className={styles.liveTitleRow}>
              <Activity className="spinner" size={20} color="#22d3ee" />
              <div>
                <div className={styles.liveStepBadge}>
                  {totalDocs > 1 && (
                    <>
                      Selected Document {currentDocIndex} of {totalDocs} &bull;{' '}
                    </>
                  )}
                  Step {activeStepNumber} of {PIPELINE_STEPS.length} &bull;{' '}
                  {activeProgress?.step_name || PIPELINE_STEPS[activeStepNumber - 1]?.name}
                </div>
                <h3 className={styles.liveMessage}>
                  {activeProgress?.message ||
                    (totalDocs > 1
                      ? `Starting document ingestion pipeline (${currentFilename}) — Document ${currentDocIndex} of ${totalDocs}…`
                      : 'Starting document ingestion pipeline…')}
                </h3>
              </div>
            </div>
            <div className={styles.liveRightMeta}>
              {totalDocs > 1 && (
                <span className="badge badge-teal">
                  Doc {currentDocIndex} / {totalDocs}
                </span>
              )}
              <span className="badge badge-purple">{Math.round(progressPercent)}%</span>
            </div>
          </div>

          <div className={styles.progressTrack}>
            <div
              className={styles.progressFill}
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      )}

      {isError && (
        <div className="alert alert-error">
          <AlertCircle size={18} /> Failed to ingest document: {uploadState.error}
        </div>
      )}

      {isCompleted && uploadState.result && (
        <div
          className="glass-card"
          style={{
            padding: '20px 24px',
            border: '1px solid rgba(52, 211, 153, 0.45)',
            background: 'rgba(10, 34, 27, 0.88)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <CheckCircle2 size={22} color="#34d399" />
            <h3 style={{ margin: 0, color: '#6ee7b7', fontSize: '1.05rem' }}>
              {ingestedCount > 1
                ? `All 5 Pipeline Steps Completed Successfully (${ingestedCount} Documents Ingested)`
                : 'All 5 Pipeline Steps Completed Successfully'}
            </h3>
          </div>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))',
              gap: '16px',
            }}
          >
            {ingestedCount > 1 && (
              <ResultRow label="Documents Ingested" value={ingestedCount} />
            )}
            <ResultRow
              label={ingestedCount > 1 ? 'Filenames' : 'Filename'}
              value={uploadState.result.filename}
            />
            <ResultRow label="Chunks (pgvector)" value={uploadState.result.chunks_created} />
            <ResultRow label="Entities (Neo4j)" value={uploadState.result.entities_extracted ?? 0} />
            <ResultRow
              label="Relationships (Neo4j)"
              value={uploadState.result.relationships_extracted ?? 0}
            />
            <ResultRow
              label="Characters"
              value={uploadState.result.characters_extracted?.toLocaleString()}
            />
          </div>

          {ingestedCount > 1 && uploadState.result.documents?.length > 1 && (
            <div className={styles.batchSummaryList}>
              {uploadState.result.documents.map((doc, idx) => (
                <div key={doc.document_id || `${doc.filename}-${idx}`} className={styles.batchDocItem}>
                  <span className={styles.batchDocName}>
                    <Check size={13} color="#34d399" /> {idx + 1}. {doc.filename}
                  </span>
                  <span className={styles.batchDocStats}>
                    {doc.chunks_created} chunks &bull; {doc.entities_extracted ?? 0} entities &bull;{' '}
                    {doc.relationships_extracted ?? 0} relationships
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Stats bar */}
      <div className={styles.statsRow}>
        <StatCard
          label="Neon Postgres Status"
          value={
            loading
              ? '…'
              : status?.postgres_status === 'ready'
              ? 'Ready'
              : 'Check .env'
          }
          icon={
            loading
              ? RefreshCw
              : status?.postgres_status === 'ready'
              ? CheckCircle2
              : XCircle
          }
          accent={status?.postgres_status === 'ready' ? 'teal' : 'red'}
          loading={loading}
        />
        <StatCard
          label="Vector Chunks Stored"
          value={loading ? '…' : status?.total_chunks ?? 0}
          icon={Box}
          accent="purple"
          loading={loading}
        />
        <StatCard
          label="Neo4j Entities"
          value={loading ? '…' : status?.total_entities ?? 0}
          icon={Share2}
          accent="purple"
          loading={loading}
        />
        <StatCard
          label="Neo4j Relationships"
          value={loading ? '…' : status?.total_relationships ?? 0}
          icon={Database}
          accent="teal"
          loading={loading}
        />
      </div>

      {error && (
        <div className="alert alert-error">
          <AlertCircle size={18} /> {error}
          <button
            className="btn btn-secondary btn-sm"
            onClick={fetchStatus}
            style={{ marginLeft: 'auto' }}
          >
            <RefreshCw size={14} /> Retry
          </button>
        </div>
      )}

      {/* Pipeline steps */}
      <div>
        <h3 className={styles.sectionTitle}>Pipeline Execution Steps</h3>
        <div className={styles.pipeline}>
          {PIPELINE_STEPS.map((step, i) => {
            const stepDone =
              isCompleted || (isUploading && step.step < activeStepNumber)
            const stepCurrent = isUploading && step.step === activeStepNumber
            const stepPending = isUploading && step.step > activeStepNumber
            const stepFailed =
              isError && activeProgress?.current_step === step.step
            const stepOutput = activeProgress?.step_outputs?.[String(step.step)]

            return (
              <div key={step.step} className={styles.pipelineStep}>
                <div className={styles.stepLeft}>
                  <div
                    className={`${styles.stepNumber} ${
                      stepDone
                        ? styles.stepNumberDone
                        : stepCurrent
                        ? styles.stepNumberCurrent
                        : stepPending
                        ? styles.stepNumberPending
                        : stepFailed
                        ? styles.stepNumberFailed
                        : ''
                    }`}
                  >
                    {stepDone ? <Check size={18} strokeWidth={2.6} /> : step.step}
                  </div>
                  {i < PIPELINE_STEPS.length - 1 && (
                    <div
                      className={`${styles.connector} ${
                        stepDone ? styles.connectorDone : ''
                      }`}
                    />
                  )}
                </div>

                <div
                  className={`glass-card ${styles.stepCard} ${
                    stepCurrent
                      ? styles.stepCardCurrent
                      : stepDone
                      ? styles.stepCardDone
                      : stepPending
                      ? styles.stepCardPending
                      : ''
                  }`}
                >
                  <div className={styles.stepHeader}>
                    <div
                      className={`${styles.stepIconWrap} ${
                        stepCurrent
                          ? styles.stepIconCurrent
                          : stepDone
                          ? styles.stepIconDone
                          : ''
                      }`}
                    >
                      {stepCurrent ? (
                        <Activity size={18} className="spinner" />
                      ) : stepDone ? (
                        <CheckCircle2 size={18} />
                      ) : (
                        <step.icon size={18} />
                      )}
                    </div>

                    <h4 className={styles.stepName}>{step.name}</h4>

                    {stepCurrent && (
                      <span className="badge badge-purple">
                        <Activity size={11} className="spinner" /> Running Now…
                      </span>
                    )}
                    {stepDone && (
                      <span className="badge badge-green">
                        <Check size={11} /> Completed
                      </span>
                    )}
                    {stepPending && (
                      <span className={styles.queuedBadge}>
                        <Clock size={11} /> Queued
                      </span>
                    )}
                    {stepFailed && (
                      <span className="badge badge-red">Failed</span>
                    )}
                    {!isUploading && !isCompleted && !stepFailed && (
                      <span className="badge badge-teal">Ready</span>
                    )}
                  </div>

                  <p className={styles.stepDesc}>
                    {stepCurrent && activeProgress?.message
                      ? activeProgress.message
                      : step.description}
                  </p>

                  {stepOutput ? (
                    <div className={styles.stepOutputBox}>
                      <Check size={13} />
                      <span>{stepOutput}</span>
                    </div>
                  ) : (
                    <code className={styles.stepDetail}>{step.detail}</code>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

function StatCard({ label, value, icon: Icon, accent, loading }) {
  return (
    <div className={`glass-card ${styles.statCard}`}>
      <div className={`${styles.statIconWrap} ${styles[accent]}`}>
        <Icon size={24} className={loading ? 'spinner' : ''} />
      </div>
      <div>
        <div className={styles.statLabel}>{label}</div>
        <div
          className={`${styles.statValue} ${
            accent === 'teal'
              ? styles.valueTeal
              : accent === 'red'
              ? styles.valueRed
              : styles.valuePurple
          }`}
        >
          {value}
        </div>
      </div>
    </div>
  )
}

function ResultRow({ label, value, mono = false }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
      <span
        style={{
          fontSize: '0.7rem',
          color: '#6ee7b7',
          textTransform: 'uppercase',
          fontWeight: 700,
          letterSpacing: '0.05em',
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontSize: '0.92rem',
          color: '#ecfdf5',
          fontWeight: 700,
          fontFamily: mono ? 'var(--font-mono)' : undefined,
          wordBreak: 'break-word',
        }}
      >
        {value}
      </span>
    </div>
  )
}
