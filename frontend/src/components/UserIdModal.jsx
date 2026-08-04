import { useState } from 'react'
import styles from './UserIdModal.module.css'

export default function UserIdModal({ onConfirm }) {
  const [value, setValue] = useState('')
  const [error, setError] = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    const trimmed = value.trim()
    if (!trimmed) {
      setError('Please enter a User ID to continue.')
      return
    }
    if (trimmed.length < 3) {
      setError('User ID must be at least 3 characters.')
      return
    }
    onConfirm(trimmed)
  }

  return (
    <div className={styles.overlay}>
      {/* Animated background blobs */}
      <div className={styles.blob1} />
      <div className={styles.blob2} />

      <form className={`${styles.modal} glass-card fade-in`} onSubmit={handleSubmit}>
        {/* Logo / icon */}
        <div className={styles.iconWrap}>
          <span className={styles.icon}>🧠</span>
          <div className={styles.iconRing} />
        </div>

        <h1 className={styles.title}>ADK RAG</h1>
        <p className={styles.subtitle}>Document Intelligence Platform</p>

        <hr className="divider" style={{ margin: '20px 0' }} />

        <p className={styles.prompt}>
          Enter your <strong>User ID</strong> to access your personal document workspace.
          Each user has their own isolated document collection.
        </p>

        <div className={styles.inputGroup}>
          <label className={styles.label} htmlFor="user-id-input">
            User ID
          </label>
          <input
            id="user-id-input"
            className={`input ${error ? styles.inputError : ''}`}
            type="text"
            placeholder="e.g. drona, user_42, alice@corp"
            value={value}
            onChange={(e) => { setValue(e.target.value); setError('') }}
            autoFocus
            autoComplete="username"
          />
          {error && <span className={styles.errorMsg}>{error}</span>}
        </div>

        <button className="btn btn-primary btn-lg" type="submit" style={{ width: '100%' }}>
          <span>Enter Workspace</span>
          <span>→</span>
        </button>

        <p className={styles.hint}>
          💡 This is a local development system. For production, replace this with real authentication.
        </p>
      </form>
    </div>
  )
}
