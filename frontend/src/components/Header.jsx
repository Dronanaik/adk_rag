import { useEffect, useState } from 'react'
import { Wifi, WifiOff, Loader2, ChevronRight, LogOut, Brain } from 'lucide-react'
import { checkHealth } from '../api.js'
import styles from './Header.module.css'

export default function Header({ userId, onChangeUser }) {
  const [backendStatus, setBackendStatus] = useState('loading')

  useEffect(() => {
    checkHealth()
      .then(() => setBackendStatus('online'))
      .catch(() => setBackendStatus('offline'))
  }, [])

  const statusIcon = {
    loading: <Loader2 size={13} className={styles.spinIcon} />,
    online:  <Wifi size={13} />,
    offline: <WifiOff size={13} />,
  }[backendStatus]

  const statusLabel = {
    loading: 'Checking…',
    online:  'API Online',
    offline: 'API Offline',
  }[backendStatus]

  return (
    <header className={styles.header}>
      <div className={`container ${styles.inner}`}>

        {/* Brand */}
        <div className={styles.brand}>
          <div className={styles.logoWrap}>
            <Brain size={22} strokeWidth={1.8} className={styles.logoIcon} />
          </div>
          <div className={styles.brandText}>
            <h1 className={styles.appName}>ADK RAG</h1>
            <p className={styles.tagline}>Document Intelligence Platform</p>
          </div>
        </div>

        {/* Right side */}
        <div className={styles.right}>

          {/* Status chip */}
          <div className={`${styles.statusChip} ${styles[backendStatus]}`}>
            {statusIcon}
            <span className={styles.statusLabel}>{statusLabel}</span>
          </div>

          <div className={styles.sep} />

          {/* User badge */}
          <div className={styles.userBadge}>
            <div className={styles.userAvatar}>
              {userId.charAt(0).toUpperCase()}
            </div>
            <div className={styles.userInfo}>
              <span className={styles.userLabel}>Signed in as</span>
              <span className={styles.userId}>{userId}</span>
            </div>
            <button
              className={`btn btn-ghost btn-sm ${styles.switchBtn}`}
              onClick={onChangeUser}
              title="Switch user"
              id="switch-user-btn"
            >
              <LogOut size={14} />
              <span>Switch</span>
            </button>
          </div>
        </div>
      </div>

      {/* Sub-header */}
      <div className={styles.subHeader}>
        <div className="container">
          <div className={styles.subInner}>
            <div className={styles.techBadges}>
              <span className={`badge badge-purple ${styles.techBadge}`}>Google ADK</span>
              <span className={`badge badge-teal ${styles.techBadge}`}>ChromaDB</span>
              <span className={`badge badge-purple ${styles.techBadge}`}>FastAPI</span>
            </div>
            <div className={styles.modelInfo}>
              <ChevronRight size={12} className={styles.chevron} />
              <span>gemini-2.5-pro</span>
              <span className={styles.modelSep}>·</span>
              <span>gemini-embedding-001</span>
              <span className={styles.modelSep}>·</span>
              <span>768 dims</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}
