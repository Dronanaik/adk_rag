import { useRef, useState } from 'react'
import { UploadCloud, FileIcon, X, Upload, CheckCircle2, Loader2, AlertTriangle, FileText, FileSpreadsheet, FileJson, Globe } from 'lucide-react'
import styles from './UploadTab.module.css'

const SUPPORTED_TYPES = [
  '.pdf', '.docx', '.xlsx', '.xls', '.pptx',
  '.txt', '.md', '.csv', '.json', '.xml', '.html', '.htm', '.log',
]

const MIME_MAP = {
  'application/pdf': '.pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
  'application/vnd.ms-excel': '.xls',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
  'text/plain': '.txt',
  'text/markdown': '.md',
  'text/csv': '.csv',
  'application/json': '.json',
  'application/xml': '.xml',
  'text/xml': '.xml',
  'text/html': '.html',
}

function isFileSupported(file) {
  const name = file.name.toLowerCase()
  return SUPPORTED_TYPES.some(ext => name.endsWith(ext))
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function UploadTab({ userId, onStartUpload }) {
  const [dragOver, setDragOver] = useState(false)
  const [selectedFile, setSelectedFile] = useState(null)
  const [errorMsg, setErrorMsg] = useState('')
  const inputRef = useRef(null)

  function handleFile(file) {
    if (!isFileSupported(file)) {
      setErrorMsg(`"${file.name}" is not a supported file type.\nSupported: ${SUPPORTED_TYPES.join(', ')}`)
      setSelectedFile(null)
      return
    }
    setErrorMsg('')
    setSelectedFile(file)
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  function handleInputChange(e) {
    const file = e.target.files[0]
    if (file) handleFile(file)
  }

  async function handleUpload() {
    if (!selectedFile) return
    setErrorMsg('')

    if (onStartUpload) {
      onStartUpload(selectedFile)
      setSelectedFile(null)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  function handleClear() {
    setSelectedFile(null)
    setErrorMsg('')
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <div className={`${styles.wrap} fade-in`}>
      <div className={styles.sectionHeader}>
        <h2 className={styles.title}>Upload Document</h2>
        <p className={styles.sub}>
          Upload a document to your workspace. It will be extracted, chunked, embedded, and stored in ChromaDB automatically.
        </p>
      </div>

      {/* Drop zone */}
      <div
        className={`glass-card ${styles.dropZone} ${dragOver ? styles.dragOver : ''} ${selectedFile ? styles.hasFile : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => !selectedFile && inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && !selectedFile && inputRef.current?.click()}
        aria-label="File upload drop zone"
      >
        <input
          ref={inputRef}
          type="file"
          accept={SUPPORTED_TYPES.join(',')}
          onChange={handleInputChange}
          className={styles.hiddenInput}
          id="file-upload-input"
        />

        {selectedFile ? (
          <div className={styles.filePreview}>
            <span className={styles.fileIconWrap}>{getFileIcon(selectedFile.name)}</span>
            <div className={styles.fileMeta}>
              <span className={styles.fileName}>{selectedFile.name}</span>
              <span className={styles.fileSize}>{formatBytes(selectedFile.size)}</span>
            </div>
            <button
              className="btn btn-secondary btn-sm"
              onClick={(e) => { e.stopPropagation(); handleClear() }}
            >
              <X size={14} style={{ marginRight: '4px' }} /> Remove
            </button>
          </div>
        ) : (
          <div className={styles.dropContent}>
            <div className={styles.dropIconWrap}>
              <UploadCloud size={32} />
            </div>
            <p className={styles.dropTitle}>
              {dragOver ? 'Drop it here!' : 'Drag & drop your file here'}
            </p>
            <p className={styles.dropSub}>or <span className={styles.browseLink}>click to browse</span></p>
          </div>
        )}
      </div>

      {/* Supported formats */}
      <div className={styles.formatsRow}>
        {SUPPORTED_TYPES.map(ext => (
          <span key={ext} className="badge badge-purple">{ext}</span>
        ))}
      </div>

      {/* Error */}
      {errorMsg && (
        <div className="alert alert-error">
          <AlertTriangle size={18} />
          <span style={{ whiteSpace: 'pre-line' }}>{errorMsg}</span>
        </div>
      )}

      {/* Upload button */}
      {selectedFile && (
        <button
          className="btn btn-primary btn-lg"
          onClick={handleUpload}
          style={{ width: '100%', justifyContent: 'center' }}
          id="upload-btn"
        >
          <Upload size={18} /> Ingest Document
        </button>
      )}
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

function getFileIcon(name) {
  const ext = name.split('.').pop().toLowerCase()
  if (['pdf'].includes(ext)) return <FileText size={28} color="#ef4444" />
  if (['docx', 'doc'].includes(ext)) return <FileText size={28} color="#3b82f6" />
  if (['xlsx', 'xls', 'csv'].includes(ext)) return <FileSpreadsheet size={28} color="#22c55e" />
  if (['pptx', 'ppt'].includes(ext)) return <FileText size={28} color="#f97316" />
  if (['json', 'xml'].includes(ext)) return <FileJson size={28} color="#eab308" />
  if (['html', 'htm'].includes(ext)) return <Globe size={28} color="#0ea5e9" />
  return <FileIcon size={28} color="#94a3b8" />
}
