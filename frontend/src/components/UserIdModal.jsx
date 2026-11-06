import { useState } from 'react'
import {
  Brain,
  Mail,
  Lock,
  User,
  Eye,
  EyeOff,
  ArrowRight,
  ShieldCheck,
  AlertCircle,
} from 'lucide-react'
import { signIn, signUp } from '../api.js'
import styles from './UserIdModal.module.css'

export default function UserIdModal({ onConfirm }) {
  const [mode, setMode] = useState('signin') // 'signin' | 'signup'
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function switchMode(nextMode) {
    setMode(nextMode)
    setError('')
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')

    const emailTrimmed = email.trim().toLowerCase()
    const nameTrimmed = fullName.trim()

    if (mode === 'signup' && nameTrimmed.length < 2) {
      setError('Please enter your full name (at least 2 characters).')
      return
    }
    if (!emailTrimmed || !emailTrimmed.includes('@')) {
      setError('Please enter a valid email address.')
      return
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters.')
      return
    }

    setLoading(true)
    try {
      const response =
        mode === 'signup'
          ? await signUp(nameTrimmed, emailTrimmed, password)
          : await signIn(emailTrimmed, password)

      if (response?.user) {
        onConfirm(response.user)
      }
    } catch (err) {
      setError(err.message || 'Authentication failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.overlay}>
      <div className={styles.blob1} />
      <div className={styles.blob2} />

      <div className={`${styles.modal} glass-card fade-in`}>
        {/* Brand Header */}
        <div className={styles.brandHeader}>
          <div className={styles.iconWrap}>
            <Brain size={28} strokeWidth={1.8} color="#22d3ee" />
          </div>
          <h1 className={styles.title}>ADK Agentic RAG</h1>
          <p className={styles.subtitle}>Hybrid Vector &amp; Knowledge Graph Platform</p>
        </div>

        {/* Mode Toggle Tabs */}
        <div className={styles.modeTabs} role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'signin'}
            className={`${styles.modeTab} ${mode === 'signin' ? styles.modeTabActive : ''}`}
            onClick={() => switchMode('signin')}
          >
            Sign In
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'signup'}
            className={`${styles.modeTab} ${mode === 'signup' ? styles.modeTabActive : ''}`}
            onClick={() => switchMode('signup')}
          >
            Create Account
          </button>
        </div>

        {error && (
          <div className="alert alert-error" style={{ padding: '11px 14px', fontSize: '0.83rem' }}>
            <AlertCircle size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
            <span>{error}</span>
          </div>
        )}

        <form className={styles.form} onSubmit={handleSubmit}>
          {mode === 'signup' && (
            <div className={styles.inputGroup}>
              <label className={styles.label} htmlFor="auth-fullname">
                Full Name
              </label>
              <div className={styles.inputWithIcon}>
                <User size={17} className={styles.fieldIcon} />
                <input
                  id="auth-fullname"
                  className={`input ${styles.paddedInput}`}
                  type="text"
                  placeholder="e.g. Drona Sharma"
                  value={fullName}
                  onChange={(e) => {
                    setFullName(e.target.value)
                    setError('')
                  }}
                  autoComplete="name"
                  disabled={loading}
                />
              </div>
            </div>
          )}

          <div className={styles.inputGroup}>
            <label className={styles.label} htmlFor="auth-email">
              Email Address
            </label>
            <div className={styles.inputWithIcon}>
              <Mail size={17} className={styles.fieldIcon} />
              <input
                id="auth-email"
                className={`input ${styles.paddedInput}`}
                type="email"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value)
                  setError('')
                }}
                autoFocus
                autoComplete="email"
                disabled={loading}
              />
            </div>
          </div>

          <div className={styles.inputGroup}>
            <label className={styles.label} htmlFor="auth-password">
              Password
            </label>
            <div className={styles.inputWithIcon}>
              <Lock size={17} className={styles.fieldIcon} />
              <input
                id="auth-password"
                className={`input ${styles.paddedInput} ${styles.passwordInput}`}
                type={showPassword ? 'text' : 'password'}
                placeholder={mode === 'signup' ? 'Create a password (min. 6 chars)' : 'Enter your password'}
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value)
                  setError('')
                }}
                autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
                disabled={loading}
              />
              <button
                type="button"
                className={styles.eyeBtn}
                onClick={() => setShowPassword(prev => !prev)}
                tabIndex={-1}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <button
            className="btn btn-primary btn-lg"
            type="submit"
            disabled={loading}
            style={{ width: '100%', justifyContent: 'center', marginTop: '6px' }}
            id="auth-submit-btn"
          >
            {loading ? (
              <>
                <span className="spinner" />
                <span>{mode === 'signup' ? 'Creating account…' : 'Signing in…'}</span>
              </>
            ) : (
              <>
                <span>{mode === 'signup' ? 'Create Account & Continue' : 'Sign In to Workspace'}</span>
                <ArrowRight size={17} />
              </>
            )}
          </button>
        </form>

        <div className={styles.securityFooter}>
          <ShieldCheck size={15} color="#34d399" />
          <span>Secured by Neon PostgreSQL Authentication &amp; Isolated Workspaces</span>
        </div>
      </div>
    </div>
  )
}
