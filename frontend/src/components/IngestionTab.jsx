import { useCallback, useEffect, useState } from 'react'
import { getIngestStatus } from '../api.js'
import styles from './IngestionTab.module.css'

const PIPELINE_STEPS = [
  {
    step: 1,
    name: 'Text Extraction',
    description: 'Reads the uploaded file and extracts raw text using format-specific parsers.',
    icon: '📖',
    detail: 'parsers.py — PyMuPDF, python-docx, openpyxl, python-pptx, plain reader',
  },
  {
    step: 2,
    name: 'Text Normalization & Chunking',
    description: 'Normalizes whitespace and splits text into overlapping 1200-character chunks with 200-character overlap.',
    icon: '✂️',
    detail: 'chunking.py — chunk_size=1200, overlap=200',
  },
  {
    step: 3,
    name: 'Gemini Embedding Generation',
    description: 'Each chunk is embedded using Gemini embedding-001 model, producing a 768-dimensional vector.',
    icon: '🔮',
    detail: 'embeddings.py — gemini-embedding-001, dimensionality=768',
  },
  {
    step: 4,
    name: 'ChromaDB Vector Storage',
    description: 'Embeddings, text chunks, and metadata (user_id, document_id, filename, chunk_index) are stored in ChromaDB.',
    icon: '🗄️',
    detail: 'rag_store.py — persistent ChromaDB collection',
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

export default function IngestionTab() {
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

      {/* Stats bar */}
      <div className={styles.statsRow}>
        <StatCard
          label="Pipeline Status"
          value={loading ? '…' : (status?.status === 'ready' ? 'Ready' : 'Error')}
          icon={loading ? '⏳' : (status?.status === 'ready' ? '✅' : '❌')}
          accent={status?.status === 'ready' ? 'teal' : 'red'}
          loading={loading}
        />
        <StatCard
          label="Total Chunks Stored"
          value={loading ? '…' : (status?.total_chunks ?? '—')}
          icon="📦"
          accent="purple"
          loading={loading}
        />
        <StatCard
          label="Supported File Types"
          value={loading ? '…' : SUPPORTED_TYPES.length}
          icon="📑"
          accent="purple"
          loading={loading}
        />
        <StatCard
          label="Embedding Dimensions"
          value="768"
          icon="🔮"
          accent="teal"
          loading={false}
        />
      </div>

      {error && (
        <div className="alert alert-error">
          <span>⚠️</span> {error}
          <button className="btn btn-secondary btn-sm" onClick={fetchStatus} style={{ marginLeft: 'auto' }}>
            Retry
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
                  <span className={styles.stepIcon}>{step.icon}</span>
                  <h4 className={styles.stepName}>{step.name}</h4>
                  <span className="badge badge-teal">Active</span>
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
                  <td><code>{row.ext}</code></td>
                  <td style={{ color: 'var(--text-secondary)' }}>{row.parser}</td>
                  <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{row.note}</td>
                  <td><span className="badge badge-teal">✓ Supported</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function StatCard({ label, value, icon, accent, loading }) {
  return (
    <div className={`glass-card ${styles.statCard}`}>
      <span className={styles.statIcon}>{icon}</span>
      <div>
        <div className={styles.statLabel}>{label}</div>
        <div className={`${styles.statValue} ${accent === 'teal' ? styles.valueTeal : styles.valuePurple}`}>
          {loading ? <span className="spinner" /> : value}
        </div>
      </div>
    </div>
  )
}
