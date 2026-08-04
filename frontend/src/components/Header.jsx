import { useEffect, useState } from 'react'
import { checkHealth } from '../api.js'
import styles from './Header.module.css'

export default function Header({ userId, onChangeUser }) {
  const [backendStatus, setBackendStatus] = useState('loading') // 'loading' | 'online' | 'offline'

  useEffect(() => {
    checkHealth()
      .then(() => setBackendStatus('online'))
      .catch(() => setBackendStatus('offline'))
  }, [])

  return (
    <header className={styles.header}>
      <div className={`container ${styles.inner}`}>
        {/* Brand */}
        <div className={styles.brand}>
          <span className={styles.logo}>🧠</span>
          <div className={styles.brandText}>
            <h1 className={styles.appName}>ADK RAG</h1>
            <p className={styles.tagline}>Document Intelligence Platform</p>
          </div>
        </div>

        {/* Status + user */}
        <div className={styles.right}>
          {/* Backend status indicator */}
          <div className={styles.statusChip}>
            <span className={`status-dot ${backendStatus}`} />
            <span className={styles.statusLabel}>
              {backendStatus === 'loading' ? 'Checking…'
                : backendStatus === 'online' ? 'API Online'
                : 'API Offline'}
            </span>
          </div>

          {/* Divider */}
          <div className={styles.divider} />

          {/* User badge */}
          <div className={styles.userBadge}>
            <span className={styles.userAvatar}>
              {userId.charAt(0).toUpperCase()}
            </span>
            <div className={styles.userInfo}>
              <span className={styles.userLabel}>Active User</span>
              <span className={styles.userId}>{userId}</span>
            </div>
            <button
              className={`btn btn-secondary btn-sm ${styles.changeBtn}`}
              onClick={onChangeUser}
              title="Switch user"
            >
              Switch
            </button>
          </div>
        </div>
      </div>

      {/* Sub-header strip */}
      <div className={styles.subHeader}>
        <div className="container">
          <div className={styles.subInner}>
            <span className="badge badge-purple">Google ADK</span>
            <span className="badge badge-teal">Gemini Embeddings</span>
            <span className="badge badge-purple">ChromaDB</span>
            <span className={styles.poweredBy}>
              Powered by <strong>gemini-2.5-pro</strong> + <strong>gemini-embedding-001</strong>
            </span>
          </div>
        </div>
      </div>
    </header>
  )
}
