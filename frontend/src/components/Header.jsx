import { useEffect, useState } from 'react'
import { Wifi, WifiOff, Loader2, LogOut, Brain, Settings, ClipboardCheck } from 'lucide-react'
import { checkHealth } from '../api.js'
import styles from './Header.module.css'

export default function Header({ user, userId, activeTab, onSelectTab, onChangeUser }) {
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

  const displayName = user?.name || user?.full_name || userId || 'User'
  const displayEmail = user?.email || userId || ''

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

          {/* Platform utility views (separate from core workflow tabs) */}
          <div className={styles.utilGroup} role="navigation" aria-label="Platform tools">
            <button
              type="button"
              id="nav-evaluation"
              className={`${styles.utilBtn} ${activeTab === 'evaluation' ? styles.utilBtnActive : ''}`}
              onClick={() => onSelectTab?.('evaluation')}
              title="RAG Evaluation & LangSmith"
            >
              <ClipboardCheck size={15} />
              <span>Evaluation</span>
            </button>
            <button
              type="button"
              id="nav-settings"
              className={`${styles.utilBtn} ${activeTab === 'settings' ? styles.utilBtnActive : ''}`}
              onClick={() => onSelectTab?.('settings')}
              title="Environment Settings"
            >
              <Settings size={15} />
              <span>Settings</span>
            </button>
          </div>

          <div className={styles.sep} />

          {/* Status chip */}
          <div className={`${styles.statusChip} ${styles[backendStatus]}`}>
            {statusIcon}
            <span className={styles.statusLabel}>{statusLabel}</span>
          </div>

          <div className={styles.sep} />

          {/* User badge */}
          <div className={styles.userBadge}>
            <div className={styles.userAvatar}>
              {displayName.charAt(0).toUpperCase()}
            </div>
            <div className={styles.userInfo}>
              <span className={styles.userId} title={displayName}>
                {displayName}
              </span>
              {displayEmail && (
                <span className={styles.userLabel} style={{ textTransform: 'none', letterSpacing: 0 }}>
                  {displayEmail}
                </span>
              )}
            </div>
            <button
              className={`btn btn-ghost btn-sm ${styles.switchBtn}`}
              onClick={onChangeUser}
              title="Sign out"
              id="switch-user-btn"
            >
              <LogOut size={14} />
              <span>Sign Out</span>
            </button>
          </div>
        </div>
      </div>

    </header>
  )
}
