import { useRef, useState } from 'react'
import {
  UploadCloud,
  FileIcon,
  X,
  Upload,
  AlertTriangle,
  FileText,
  FileSpreadsheet,
  FileJson,
  Globe,
  Plus,
  Trash2,
} from 'lucide-react'
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
  const [selectedFiles, setSelectedFiles] = useState([])
  const [errorMsg, setErrorMsg] = useState('')
  const inputRef = useRef(null)

  function handleFiles(fileList) {
    const incoming = Array.from(fileList || [])
    if (!incoming.length) return

    const validFiles = []
    const invalidNames = []

    incoming.forEach(file => {
      if (isFileSupported(file)) {
        validFiles.push(file)
      } else {
        invalidNames.push(file.name)
      }
    })

    if (invalidNames.length > 0) {
      setErrorMsg(
        `Unsupported file(s) skipped: ${invalidNames.join(', ')}.\nSupported: ${SUPPORTED_TYPES.join(', ')}`
      )
    } else {
      setErrorMsg('')
    }

    if (validFiles.length > 0) {
      setSelectedFiles(prev => {
        const existingKeys = new Set(prev.map(f => `${f.name}::${f.size}`))
        const merged = [...prev]
        validFiles.forEach(f => {
          const key = `${f.name}::${f.size}`
          if (!existingKeys.has(key)) {
            existingKeys.add(key)
            merged.push(f)
          }
        })
        return merged
      })
    }
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragOver(false)
    if (e.dataTransfer.files?.length) {
      handleFiles(e.dataTransfer.files)
    }
  }

  function handleInputChange(e) {
    if (e.target.files?.length) {
      handleFiles(e.target.files)
    }
    if (inputRef.current) inputRef.current.value = ''
  }

  function handleRemoveFile(indexToRemove) {
    setSelectedFiles(prev => prev.filter((_, idx) => idx !== indexToRemove))
  }

  async function handleUpload() {
    if (!selectedFiles.length) return
    setErrorMsg('')

    if (onStartUpload) {
      onStartUpload(selectedFiles)
      setSelectedFiles([])
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  function handleClear() {
    setSelectedFiles([])
    setErrorMsg('')
    if (inputRef.current) inputRef.current.value = ''
  }

  const totalBytes = selectedFiles.reduce((sum, f) => sum + (f.size || 0), 0)
  const hasFiles = selectedFiles.length > 0

  return (
    <div className={`${styles.wrap} fade-in`}>
      <div className={styles.sectionHeader}>
        <h2 className={styles.title}>Upload Documents</h2>
        <p className={styles.sub}>
          Upload one or more documents to your workspace. Each document is semantically chunked,
          embedded into <strong>Neon PostgreSQL (pgvector)</strong>, and analyzed by Gemini to
          populate your <strong>Neo4j Knowledge Graph</strong>.
        </p>
      </div>

      {/* Drop zone */}
      <div
        className={`glass-card ${styles.dropZone} ${dragOver ? styles.dragOver : ''} ${hasFiles ? styles.hasFile : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => !hasFiles && inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && !hasFiles && inputRef.current?.click()}
        aria-label="File upload drop zone"
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={SUPPORTED_TYPES.join(',')}
          onChange={handleInputChange}
          className={styles.hiddenInput}
          id="file-upload-input"
        />

        {hasFiles ? (
          <div className={styles.filesQueueWrap} onClick={(e) => e.stopPropagation()}>
            <div className={styles.queueHeader}>
              <div className={styles.queueSummary}>
                <span className="badge badge-teal">
                  {selectedFiles.length}{' '}
                  {selectedFiles.length === 1 ? 'Document Selected' : 'Documents Selected'}
                </span>
                <span className={styles.queueTotalSize}>
                  Total: {formatBytes(totalBytes)}
                </span>
              </div>
              <div className={styles.queueActions}>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => inputRef.current?.click()}
                >
                  <Plus size={14} /> Add More Files
                </button>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={handleClear}
                >
                  <Trash2 size={14} /> Clear All
                </button>
              </div>
            </div>

            <div className={styles.filesList}>
              {selectedFiles.map((file, idx) => (
                <div key={`${file.name}-${file.size}-${idx}`} className={styles.filePreview}>
                  <span className={styles.fileIndexBadge}>{idx + 1}</span>
                  <span className={styles.fileIconWrap}>{getFileIcon(file.name)}</span>
                  <div className={styles.fileMeta}>
                    <span className={styles.fileName}>{file.name}</span>
                    <span className={styles.fileSize}>{formatBytes(file.size)}</span>
                  </div>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => handleRemoveFile(idx)}
                  >
                    <X size={14} style={{ marginRight: '4px' }} /> Remove
                  </button>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className={styles.dropContent}>
            <div className={styles.dropIconWrap}>
              <UploadCloud size={32} />
            </div>
            <p className={styles.dropTitle}>
              {dragOver ? 'Drop your files here!' : 'Drag & drop one or multiple files here'}
            </p>
            <p className={styles.dropSub}>
              or <span className={styles.browseLink}>click to browse multiple files</span>
            </p>
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
      {hasFiles && (
        <button
          className="btn btn-primary btn-lg"
          onClick={handleUpload}
          style={{ width: '100%', justifyContent: 'center' }}
          id="upload-btn"
        >
          <Upload size={18} />{' '}
          {selectedFiles.length === 1
            ? 'Ingest into Neon Postgres & Neo4j'
            : `Ingest ${selectedFiles.length} Documents into Neon Postgres & Neo4j`}
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
