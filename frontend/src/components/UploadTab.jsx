import { useRef, useState } from 'react'
import { UploadCloud, FileIcon, X, Upload, AlertTriangle, FileText, FileSpreadsheet, FileJson, Globe } from 'lucide-react'
import styles from './UploadTab.module.css'

const SUPPORTED_TYPES = [
  '.pdf', '.docx', '.xlsx', '.xls', '.pptx',
  '.txt', '.md', '.csv', '.json', '.xml', '.html', '.htm', '.log',
]

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
          Upload a document to your workspace. It will be semantically chunked, embedded into{' '}
          <strong>Neon PostgreSQL (pgvector)</strong>, and analyzed by Gemini to populate your{' '}
          <strong>Neo4j Knowledge Graph</strong>.
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
          <Upload size={18} /> Ingest into Neon Postgres & Neo4j
        </button>
      )}
    </div>
  )
}

function getFileIcon(name) {
  const ext = name.split('.').pop().toLowerCase()
  if (['pdf'].includes(ext)) return <FileText size={28} color="#ef4444" />
  if (['docx', 'doc'].includes(ext)) return <FileText size={28} color="#3b82f6" />
  if (['xlsx', 'xls', 'csv'].includes(ext)) return <FileSpreadsheet size={28} color="#16a34a" />
  if (['pptx', 'ppt'].includes(ext)) return <FileText size={28} color="#f97316" />
  if (['json', 'xml'].includes(ext)) return <FileJson size={28} color="#ca8a04" />
  if (['html', 'htm'].includes(ext)) return <Globe size={28} color="#0284c7" />
  return <FileIcon size={28} color="#64748b" />
}
