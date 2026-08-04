import { useCallback, useEffect, useState } from 'react'
import { deleteDocument, listDocuments } from '../api.js'
import styles from './DocumentsTab.module.css'

function getFileIcon(name = '') {
  const ext = name.split('.').pop().toLowerCase()
  const icons = {
    pdf: '📄', docx: '📝', doc: '📝', xlsx: '📊', xls: '📊',
    pptx: '📑', ppt: '📑', txt: '📃', md: '📃', csv: '📊',
    json: '🔧', xml: '🔧', html: '🌐', htm: '🌐', log: '📋',
  }
  return icons[ext] || '📁'
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
          {loading ? <span className="spinner" /> : '🔄'} Refresh
        </button>
      </div>

      {error && (
        <div className="alert alert-error">
          <span>⚠️</span> {error}
        </div>
      )}

      {!loading && documents.length === 0 && !error && (
        <div className="empty-state glass-card">
          <span className="empty-state-icon">📭</span>
          <p style={{ fontWeight: 600 }}>No documents yet</p>
          <p style={{ fontSize: '0.85rem' }}>Upload a document in the Upload tab to get started.</p>
        </div>
      )}

      {documents.length > 0 && (
        <div className={styles.docList}>
          {documents.map(doc => (
            <div key={doc.document_id} className={`glass-card ${styles.docCard}`}>
              <span className={styles.docIcon}>{getFileIcon(doc.filename)}</span>

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
                    {deletingId === doc.document_id ? <span className="spinner" /> : 'Yes, delete'}
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
                  className="btn btn-danger btn-sm"
                  onClick={() => setConfirmId(doc.document_id)}
                  disabled={!!deletingId}
                  id={`delete-${doc.document_id}`}
                >
                  🗑 Delete
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
