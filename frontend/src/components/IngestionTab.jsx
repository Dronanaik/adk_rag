import { useCallback, useEffect, useState } from 'react'
import { Activity, Box, FileType, Zap, CheckCircle2, XCircle, AlertCircle, RefreshCw, BookOpen, Scissors, Cpu, Database, Check } from 'lucide-react'
import { getIngestStatus } from '../api.js'
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
    name: 'Text Normalization & Chunking',
    description: 'Normalizes whitespace and splits text into overlapping 1200-character chunks with 200-character overlap.',
    icon: Scissors,
    detail: 'chunk_size=1200, overlap=200',
  },
  {
    step: 3,
    name: 'Gemini Embedding Generation',
    description: 'Each chunk is embedded using Gemini embedding-001 model, producing a 768-dimensional vector.',
    icon: Cpu,
    detail: 'gemini-embedding-001, dimensionality=768',
  },
  {
    step: 4,
    name: 'Pinecone Vector Storage',
    description: 'Embeddings, text chunks, and metadata (user_id, document_id, filename, chunk_index) are stored in Pinecone DB.',
    icon: Database,
    detail: 'persistent Pinecone DB collection',
  },
]

const SUPPORTED_TYPES = [
  { ext: '.pdf',  parser: 'PyMuPDF',     note: 'Text PDFs only. Scanned PDFs need OCR.' },
  { ext: '.docx', parser: 'python-docx', note: 'Full paragraph extraction.' },
  { ext: '.xlsx', parser: 'openpyxl',    note: 'All sheets, row-by-row extraction.' },
  { ext: '.xls',  parser: 'openpyxl',    note: 'Legacy Excel format.' },
  { ext: '.pptx', parser: 'python-pptx', note: 'Slide-by-slide text extraction.' },
  { ext: '.txt',  parser: 'Plain reader', note: 'UTF-8 with error-ignore fallback.' },
  { ext: '.md',   parser: 'Plain reader', note: 'Markdown treated as plain text.' },
  { ext: '.csv',  parser: 'Plain reader', note: 'Raw CSV values extracted.' },
  { ext: '.json', parser: 'Plain reader', note: 'Raw JSON text.' },
  { ext: '.xml',  parser: 'Plain reader', note: 'Raw XML markup.' },
  { ext: '.html', parser: 'Plain reader', note: 'HTML tags included in extraction.' },
  { ext: '.htm',  parser: 'Plain reader', note: 'Same as HTML.' },
  { ext: '.log',  parser: 'Plain reader', note: 'Log files as plain text.' },
]

export default function IngestionTab({ uploadState }) {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

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

  useEffect(() => { fetchStatus() }, [fetchStatus])

  return (
    <div className={`${styles.wrap} fade-in`}>
      <div className={styles.sectionHeader}>
        <h2 className={styles.title}>Ingestion Pipeline</h2>
        <p className={styles.sub}>
          Documents go through a 4-step pipeline before becoming searchable. Monitor the pipeline status and explore supported file types below.
        </p>
      </div>

      {/* Upload State Overlay / Alerts */}
      {uploadState?.status === 'uploading' && (
        <div className="glass-card" style={{ padding: '20px', marginBottom: '24px', border: '1px solid var(--accent-teal)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Activity className="spinner" size={24} color="var(--accent-teal)" />
            <h3 style={{ margin: 0, color: 'var(--text-primary)' }}>Ingestion Pipeline is Running...</h3>
          </div>
          <p style={{ marginTop: '8px', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Processing document. This involves Text Extraction, Normalization & Chunking, Gemini Embedding Generation, and Pinecone Vector Storage.
          </p>
        </div>
      )}

      {uploadState?.status === 'error' && (
        <div className="alert alert-error" style={{ marginBottom: '24px' }}>
          <AlertCircle size={18} /> Failed to ingest document: {uploadState.error}
        </div>
      )}

      {uploadState?.status === 'success' && uploadState.result && (
        <div className="glass-card" style={{ padding: '20px', marginBottom: '24px', border: '1px solid var(--accent-teal)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <CheckCircle2 size={24} color="var(--accent-teal)" />
            <h3 style={{ margin: 0, color: 'var(--text-primary)' }}>Document Ingested Successfully</h3>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
            <ResultRow label="Document ID" value={uploadState.result.document_id} mono />
            <ResultRow label="Filename" value={uploadState.result.filename} />
            <ResultRow label="Chunks Created" value={uploadState.result.chunks_created} />
            <ResultRow label="Characters" value={uploadState.result.characters_extracted?.toLocaleString()} />
          </div>
        </div>
      )}

      {/* Stats bar */}
      <div className={styles.statsRow}>
        <StatCard
          label="Pipeline Status"
          value={loading ? '…' : (status?.status === 'ready' ? 'Ready' : 'Error')}
          icon={loading ? RefreshCw : (status?.status === 'ready' ? CheckCircle2 : XCircle)}
          accent={status?.status === 'ready' ? 'teal' : 'red'}
          loading={loading}
        />
        <StatCard
          label="Total Chunks Stored"
          value={loading ? '…' : (status?.total_chunks ?? '—')}
          icon={Box}
          accent="purple"
          loading={loading}
        />
        <StatCard
          label="Supported File Types"
          value={loading ? '…' : SUPPORTED_TYPES.length}
          icon={FileType}
          accent="purple"
          loading={loading}
        />
        <StatCard
          label="Embedding Dimensions"
          value="768"
          icon={Zap}
          accent="teal"
          loading={false}
        />
      </div>

      {error && (
        <div className="alert alert-error">
          <AlertCircle size={18} /> {error}
          <button className="btn btn-secondary btn-sm" onClick={fetchStatus} style={{ marginLeft: 'auto' }}>
            <RefreshCw size={14} /> Retry
          </button>
        </div>
      )}

      {/* Pipeline steps */}
      <div>
        <h3 className={styles.sectionTitle}>Pipeline Steps</h3>
        <div className={styles.pipeline}>
          {PIPELINE_STEPS.map((step, i) => (
            <div key={step.step} className={styles.pipelineStep}>
              <div className={styles.stepLeft}>
                <div className={styles.stepNumber}>{step.step}</div>
                {i < PIPELINE_STEPS.length - 1 && <div className={styles.connector} />}
              </div>
              <div className={`glass-card ${styles.stepCard}`}>
                <div className={styles.stepHeader}>
                  <div className={styles.stepIconWrap}>
                    {uploadState?.status === 'uploading' ? (
                      <Activity size={18} className="spinner" />
                    ) : (
                      <step.icon size={18} />
                    )}
                  </div>
                  <h4 className={styles.stepName}>{step.name}</h4>
                  {uploadState?.status === 'uploading' ? (
                    <span className="badge badge-teal">Processing</span>
                  ) : (
                    <span className="badge badge-teal">Active</span>
                  )}
                </div>
                <p className={styles.stepDesc}>{step.description}</p>
                <code className={styles.stepDetail}>{step.detail}</code>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* File type matrix */}
      <div>
        <h3 className={styles.sectionTitle}>Supported File Types</h3>
        <div className={`glass-card ${styles.tableWrap}`}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Extension</th>
                <th>Parser</th>
                <th>Notes</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {SUPPORTED_TYPES.map(row => (
                <tr key={row.ext}>
                  <td><code className={styles.codeExt}>{row.ext}</code></td>
                  <td style={{ color: 'var(--text-secondary)' }}>{row.parser}</td>
                  <td style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{row.note}</td>
                  <td><span className="badge badge-teal"><Check size={12} style={{ marginRight: '4px' }}/> Supported</span></td>
                </tr>
              ))}
            </tbody>
          </table>
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
        <div className={`${styles.statValue} ${accent === 'teal' ? styles.valueTeal : (accent === 'red' ? styles.valueRed : styles.valuePurple)}`}>
          {value}
        </div>
      </div>
    </div>
  )
}

function ResultRow({ label, value, mono = false }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.05em' }}>
        {label}
      </span>
      <span style={{ fontSize: '0.88rem', color: 'var(--text-primary)', fontFamily: mono ? 'var(--font-mono)' : undefined, wordBreak: 'break-all' }}>
        {value}
      </span>
    </div>
  )
}
