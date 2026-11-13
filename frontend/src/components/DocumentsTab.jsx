import { useCallback, useEffect, useState } from 'react'
import { FileIcon, FileText, FileSpreadsheet, FileJson, Globe, Trash2, RefreshCw, AlertCircle, X, Eye, Copy, Check } from 'lucide-react'
import { deleteAllDocuments, deleteDocument, getDocumentPreview, listDocuments } from '../api.js'
import styles from './DocumentsTab.module.css'

function getFileIcon(name = '') {
  const ext = name.split('.').pop().toLowerCase()
  if (['pdf'].includes(ext)) return <FileText size={22} color="#ef4444" />
  if (['docx', 'doc'].includes(ext)) return <FileText size={22} color="#3b82f6" />
  if (['xlsx', 'xls', 'csv'].includes(ext)) return <FileSpreadsheet size={22} color="#16a34a" />
  if (['pptx', 'ppt'].includes(ext)) return <FileText size={22} color="#f97316" />
  if (['json', 'xml'].includes(ext)) return <FileJson size={22} color="#ca8a04" />
  if (['html', 'htm'].includes(ext)) return <Globe size={22} color="#0284c7" />
  return <FileIcon size={22} color="#64748b" />
}

export default function DocumentsTab({ userId }) {
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [deletingId, setDeletingId] = useState(null)
  const [confirmId, setConfirmId] = useState(null)
  const [showDeleteAllModal, setShowDeleteAllModal] = useState(false)
  const [deleteAllInput, setDeleteAllInput] = useState('')
  const [deletingAll, setDeletingAll] = useState(false)
  const [previewDoc, setPreviewDoc] = useState(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewError, setPreviewError] = useState('')
  const [previewMode, setPreviewMode] = useState('text') // 'text' | 'chunks'
  const [copiedPreview, setCopiedPreview] = useState(false)

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

  function openDeleteAllModal() {
    setDeleteAllInput('')
    setShowDeleteAllModal(true)
  }

  function closeDeleteAllModal() {
    if (deletingAll) return
    setShowDeleteAllModal(false)
    setDeleteAllInput('')
  }

  async function handleDeleteAll(e) {
    if (e) e.preventDefault()
    if (deleteAllInput !== 'Delete' || deletingAll) return

    setDeletingAll(true)
    setError('')
    try {
      await deleteAllDocuments(userId)
      setDocuments([])
      setShowDeleteAllModal(false)
      setDeleteAllInput('')
    } catch (err) {
      setError(`Delete All failed: ${err.message}`)
    } finally {
      setDeletingAll(false)
    }
  }

  async function openPreview(doc) {
    setPreviewDoc({
      document_id: doc.document_id,
      filename: doc.filename,
      chunks: doc.chunks,
      entities: doc.entities,
      relationships: doc.relationships,
      characters: doc.characters,
      full_text: '',
      chunk_list: [],
    })
    setPreviewMode('text')
    setPreviewError('')
    setPreviewLoading(true)
    setCopiedPreview(false)
    try {
      const data = await getDocumentPreview(doc.document_id, userId)
      setPreviewDoc(data.document)
    } catch (err) {
      setPreviewError(`Preview failed: ${err.message}`)
    } finally {
      setPreviewLoading(false)
    }
  }

  function closePreview() {
    setPreviewDoc(null)
    setPreviewError('')
    setCopiedPreview(false)
  }

  async function handleCopyPreview() {
    if (!previewDoc?.full_text) return
    try {
      await navigator.clipboard.writeText(previewDoc.full_text)
      setCopiedPreview(true)
      setTimeout(() => setCopiedPreview(false), 1800)
    } catch {
      // Clipboard API unavailable in non-HTTPS contexts
    }
  }

  useEffect(() => {
    if (!previewDoc) return
    function onKeyDown(e) {
      if (e.key === 'Escape') closePreview()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [previewDoc])

  return (
    <div className={`${styles.wrap} fade-in`}>
      <div className={styles.headerRow}>
        <div>
          <h2 className={styles.title}>My Documents</h2>
          <p className={styles.sub}>
            {loading
              ? 'Loading…'
              : `${documents.length} document${documents.length !== 1 ? 's' : ''} indexed in Neon PostgreSQL & Neo4j`}
          </p>
        </div>
        <div className={styles.headerActions}>
          {documents.length > 0 && (
            <button
              className="btn btn-danger"
              onClick={openDeleteAllModal}
              disabled={loading || deletingAll}
              id="delete-all-docs-btn"
            >
              <Trash2 size={16} /> Delete All
            </button>
          )}
          <button
            className="btn btn-secondary"
            onClick={fetchDocuments}
            disabled={loading || deletingAll}
            id="refresh-docs-btn"
          >
            <RefreshCw size={16} className={loading ? 'spinner' : ''} /> Refresh
          </button>
        </div>
      </div>

      {showDeleteAllModal && (
        <div className={styles.modalBackdrop} onClick={closeDeleteAllModal}>
          <div
            className={`glass-card ${styles.modalCard}`}
            onClick={e => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-all-modal-title"
          >
            <div className={styles.modalHeader}>
              <h3 id="delete-all-modal-title" className={styles.modalTitle}>
                Delete All Documents
              </h3>
              <button
                type="button"
                className={styles.modalCloseBtn}
                onClick={closeDeleteAllModal}
                disabled={deletingAll}
                aria-label="Close"
              >
                <X size={18} />
              </button>
            </div>
            <p className={styles.modalDescription}>
              This will permanently delete all <strong>{documents.length}</strong> document{documents.length !== 1 ? 's' : ''} from Neon PostgreSQL and Neo4j. Type <code>Delete</code> below to confirm.
            </p>
            <form onSubmit={handleDeleteAll} className={styles.modalForm}>
              <input
                type="text"
                className="input"
                placeholder="Enter Delete"
                value={deleteAllInput}
                onChange={e => setDeleteAllInput(e.target.value)}
                disabled={deletingAll}
                autoFocus
                id="delete-all-confirm-input"
              />
              <div className={styles.modalActions}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={closeDeleteAllModal}
                  disabled={deletingAll}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-danger"
                  disabled={deleteAllInput !== 'Delete' || deletingAll}
                  id="confirm-delete-all-btn"
                >
                  {deletingAll ? <RefreshCw size={15} className="spinner" /> : <Trash2 size={15} />}
                  Delete All
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {error && (
        <div className="alert alert-error">
          <AlertCircle size={18} /> {error}
        </div>
      )}

      {!loading && documents.length === 0 && !error && (
        <div className="empty-state glass-card">
          <span className="empty-state-icon">
            <FileIcon size={48} strokeWidth={1.3} color="#22d3ee" />
          </span>
          <p style={{ fontWeight: 700, color: 'var(--text-primary)' }}>No documents yet</p>
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
                <button
                  type="button"
                  className={styles.docNameBtn}
                  onClick={() => openPreview(doc)}
                  title={`Preview ${doc.filename}`}
                >
                  {doc.filename}
                </button>
                <div className={styles.docMeta}>
                  <span className="badge badge-purple">{doc.chunks} chunks</span>
                  {doc.entities !== undefined && (
                    <span className="badge badge-teal">{doc.entities} entities</span>
                  )}
                  {doc.relationships !== undefined && (
                    <span className="badge badge-green">{doc.relationships} relations</span>
                  )}
                  <span className={styles.docId} title={doc.document_id}>
                    ID: {doc.document_id.slice(0, 12)}…
                  </span>
                </div>
              </div>

              {confirmId === doc.document_id ? (
                <div className={styles.confirmRow}>
                  <span className={styles.confirmText}>Delete from Postgres & Neo4j?</span>
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
                <div className={styles.docActions}>
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => openPreview(doc)}
                    disabled={!!deletingId}
                    id={`preview-${doc.document_id}`}
                    title="Preview extracted document content"
                  >
                    <Eye size={14} /> Preview
                  </button>
                  <button
                    className={`btn btn-danger btn-sm ${styles.deleteBtn}`}
                    onClick={() => setConfirmId(doc.document_id)}
                    disabled={!!deletingId}
                    id={`delete-${doc.document_id}`}
                  >
                    <Trash2 size={14} /> Delete
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {previewDoc && (
        <div className={styles.modalBackdrop} onClick={closePreview} id="document-preview-modal">
          <div
            className={`glass-card ${styles.previewModalCard}`}
            onClick={e => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="preview-modal-title"
          >
            <div className={styles.previewModalHeader}>
              <div className={styles.previewTitleWrap}>
                <div className={styles.docIconWrap}>
                  {getFileIcon(previewDoc.filename)}
                </div>
                <div className={styles.previewTitleInfo}>
                  <h3 id="preview-modal-title" className={styles.previewModalTitle}>
                    {previewDoc.filename}
                  </h3>
                  <div className={styles.docMeta}>
                    <span className="badge badge-purple">{previewDoc.chunks} chunks</span>
                    {previewDoc.entities !== undefined && (
                      <span className="badge badge-teal">{previewDoc.entities} entities</span>
                    )}
                    {previewDoc.relationships !== undefined && (
                      <span className="badge badge-green">{previewDoc.relationships} relations</span>
                    )}
                    {previewDoc.characters !== undefined && (
                      <span className={styles.docId}>
                        {previewDoc.characters.toLocaleString()} chars
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <button
                type="button"
                className={styles.modalCloseBtn}
                onClick={closePreview}
                aria-label="Close preview"
                id="close-preview-modal-btn"
              >
                <X size={18} />
              </button>
            </div>

            <div className={styles.previewToolbar}>
              <div className={styles.previewModeTabs}>
                <button
                  type="button"
                  className={`${styles.previewModeBtn} ${previewMode === 'text' ? styles.previewModeBtnActive : ''}`}
                  onClick={() => setPreviewMode('text')}
                  id="preview-mode-text-btn"
                >
                  Extracted Text
                </button>
                <button
                  type="button"
                  className={`${styles.previewModeBtn} ${previewMode === 'chunks' ? styles.previewModeBtnActive : ''}`}
                  onClick={() => setPreviewMode('chunks')}
                  id="preview-mode-chunks-btn"
                >
                  Indexed Chunks ({previewDoc.chunk_list?.length ?? previewDoc.chunks ?? 0})
                </button>
              </div>
              {previewDoc.full_text && (
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={handleCopyPreview}
                  id="copy-preview-text-btn"
                >
                  {copiedPreview ? <Check size={14} /> : <Copy size={14} />}
                  {copiedPreview ? 'Copied!' : 'Copy Text'}
                </button>
              )}
            </div>

            <div className={styles.previewBody}>
              {previewLoading && (
                <div className={styles.previewLoading}>
                  <RefreshCw size={22} className="spinner" />
                  <span>Loading document preview…</span>
                </div>
              )}

              {!previewLoading && previewError && (
                <div className="alert alert-error">
                  <AlertCircle size={18} /> {previewError}
                </div>
              )}

              {!previewLoading && !previewError && previewMode === 'text' && (
                <pre className={styles.previewTextContent}>
                  {previewDoc.full_text || 'No extracted text available for this document.'}
                </pre>
              )}

              {!previewLoading && !previewError && previewMode === 'chunks' && (
                <div className={styles.previewChunkList}>
                  {(previewDoc.chunk_list || []).map(chunk => (
                    <div key={chunk.chunk_index} className={styles.previewChunkCard}>
                      <div className={styles.previewChunkHeader}>
                        <span className="badge badge-purple">Chunk #{chunk.chunk_index + 1}</span>
                        <span className={styles.docId}>{chunk.char_count} chars</span>
                      </div>
                      <pre className={styles.previewChunkText}>{chunk.content}</pre>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
