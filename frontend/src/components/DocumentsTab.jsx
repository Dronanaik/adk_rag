import { useCallback, useEffect, useState } from 'react'
import { FileIcon, FileText, FileSpreadsheet, FileJson, Globe, Trash2, RefreshCw, AlertCircle } from 'lucide-react'
import { deleteDocument, listDocuments } from '../api.js'
import styles from './DocumentsTab.module.css'

function getFileIcon(name = '') {
  const ext = name.split('.').pop().toLowerCase()
  if (['pdf'].includes(ext)) return <FileText size={22} color="#ef4444" />
  if (['docx', 'doc'].includes(ext)) return <FileText size={22} color="#3b82f6" />
  if (['xlsx', 'xls', 'csv'].includes(ext)) return <FileSpreadsheet size={22} color="#22c55e" />
  if (['pptx', 'ppt'].includes(ext)) return <FileText size={22} color="#f97316" />
  if (['json', 'xml'].includes(ext)) return <FileJson size={22} color="#eab308" />
  if (['html', 'htm'].includes(ext)) return <Globe size={22} color="#0ea5e9" />
  return <FileIcon size={22} color="#94a3b8" />
}

export default function DocumentsTab({ userId }) {
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [deletingId, setDeletingId] = useState(null)
  const [confirmId, setConfirmId] = useState(null)

  const fetchDocuments = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await listDocuments(userId)
      setDocuments(data.documents || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [userId])

  useEffect(() => {
    fetchDocuments()
  }, [fetchDocuments])

  async function handleDelete(documentId) {
    setDeletingId(documentId)
    setConfirmId(null)
    try {
      await deleteDocument(documentId, userId)
      setDocuments(prev => prev.filter(d => d.document_id !== documentId))
    } catch (err) {
      setError(`Delete failed: ${err.message}`)
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className={`${styles.wrap} fade-in`}>
      <div className={styles.headerRow}>
        <div>
          <h2 className={styles.title}>My Documents</h2>
          <p className={styles.sub}>
            {loading ? 'Loading…' : `${documents.length} document${documents.length !== 1 ? 's' : ''} in your workspace`}
          </p>
        </div>
        <button
          className="btn btn-secondary"
          onClick={fetchDocuments}
          disabled={loading}
          id="refresh-docs-btn"
        >
          <RefreshCw size={16} className={loading ? 'spinner' : ''} /> Refresh
        </button>
      </div>

      {error && (
        <div className="alert alert-error">
          <AlertCircle size={18} /> {error}
        </div>
      )}

      {!loading && documents.length === 0 && !error && (
        <div className="empty-state glass-card">
          <span className="empty-state-icon">
            <FileIcon size={48} strokeWidth={1} color="rgba(124, 108, 255, 0.4)" />
          </span>
          <p style={{ fontWeight: 600 }}>No documents yet</p>
          <p style={{ fontSize: '0.85rem' }}>Upload a document in the Upload tab to get started.</p>
        </div>
      )}

      {documents.length > 0 && (
        <div className={styles.docList}>
          {documents.map(doc => (
            <div key={doc.document_id} className={`glass-card ${styles.docCard}`}>
              <div className={styles.docIconWrap}>
                {getFileIcon(doc.filename)}
              </div>

              <div className={styles.docInfo}>
                <span className={styles.docName} title={doc.filename}>
                  {doc.filename}
                </span>
                <div className={styles.docMeta}>
                  <span className="badge badge-purple">{doc.chunks} chunks</span>
                  <span className={styles.docId} title={doc.document_id}>
                    ID: {doc.document_id.slice(0, 12)}…
                  </span>
                </div>
              </div>

              {confirmId === doc.document_id ? (
                <div className={styles.confirmRow}>
                  <span className={styles.confirmText}>Delete?</span>
                  <button
                    className="btn btn-danger btn-sm"
                    onClick={() => handleDelete(doc.document_id)}
                    disabled={deletingId === doc.document_id}
                    id={`confirm-delete-${doc.document_id}`}
                  >
                    {deletingId === doc.document_id ? <RefreshCw size={14} className="spinner" /> : 'Yes, delete'}
                  </button>
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => setConfirmId(null)}
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  className={`btn btn-danger btn-sm ${styles.deleteBtn}`}
                  onClick={() => setConfirmId(doc.document_id)}
                  disabled={!!deletingId}
                  id={`delete-${doc.document_id}`}
                >
                  <Trash2 size={14} /> Delete
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
