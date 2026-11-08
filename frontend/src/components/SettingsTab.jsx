import { useCallback, useEffect, useState } from 'react'
import {
  Info,
  CheckCircle2,
  AlertCircle,
  Eye,
  EyeOff,
  ArrowRight,
} from 'lucide-react'
import { getEnvSettings, updateEnvSettings } from '../api.js'
import styles from './SettingsTab.module.css'

export default function SettingsTab({ onContinueToUpload }) {
  const [variables, setVariables] = useState([])
  const [formValues, setFormValues] = useState({})
  const [showSecrets, setShowSecrets] = useState({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [banner, setBanner] = useState(null)

  const loadSettings = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getEnvSettings()
      const vars = data.variables || []
      setVariables(vars)
      const initial = {}
      for (const item of vars) {
        initial[item.key] = item.custom_value || ''
      }
      setFormValues(initial)
    } catch (err) {
      setBanner({ type: 'error', text: `Failed to load settings: ${err.message}` })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadSettings()
  }, [loadSettings])

  const handleInputChange = (key, value) => {
    setFormValues((prev) => ({
      ...prev,
      [key]: value,
    }))
  }

  const toggleSecretVisibility = (key) => {
    setShowSecrets((prev) => ({
      ...prev,
      [key]: !prev[key],
    }))
  }

  const handleSave = async (e) => {
    e.preventDefault()
    setSaving(true)
    setBanner(null)
    try {
      await updateEnvSettings(formValues, false)
      setBanner({
        type: 'success',
        text: 'Configuration saved.',
      })
      if (onContinueToUpload) {
        setTimeout(() => onContinueToUpload(), 450)
      }
    } catch (err) {
      setBanner({ type: 'error', text: err.message })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className={`${styles.wrap} fade-in`}>
      <div className={`glass-card ${styles.card}`}>
        <div className={styles.header}>
          <h2 className={styles.title}>Environment Variables</h2>
          <p className={styles.sub}>
            Enter your connection variables below before uploading documents.
          </p>
        </div>

        {banner && (
          <div className={`alert ${banner.type === 'error' ? 'alert-error' : styles.alertSuccess}`}>
            {banner.type === 'error' ? <AlertCircle size={17} /> : <CheckCircle2 size={17} />}
            <span>{banner.text}</span>
          </div>
        )}

        {loading ? (
          <div className={styles.loadingState}>Loading environment variables…</div>
        ) : (
          <form onSubmit={handleSave} className={styles.form}>
            <div className={styles.fieldsGrid}>
              {variables.map((item) => {
                const val = formValues[item.key] ?? ''
                const isSecretVisible = Boolean(showSecrets[item.key])

                return (
                  <div key={item.key} className={styles.fieldItem}>
                    <div className={styles.labelRow}>
                      <label htmlFor={`env-input-${item.key}`} className={styles.envKey}>
                        {item.key}
                      </label>
                      <a
                        href={item.doc_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={styles.infoIcon}
                        title={`View documentation for ${item.key}`}
                        aria-label={`Documentation for ${item.key}`}
                      >
                        <Info size={15} />
                      </a>
                    </div>

                    <div className={styles.inputWrap}>
                      <input
                        id={`env-input-${item.key}`}
                        type={item.is_secret && !isSecretVisible ? 'password' : 'text'}
                        value={val}
                        onChange={(e) => handleInputChange(item.key, e.target.value)}
                        placeholder={`Enter ${item.key}`}
                        className={styles.input}
                        autoComplete="off"
                        spellCheck={false}
                      />
                      {item.is_secret && (
                        <button
                          type="button"
                          className={styles.eyeBtn}
                          onClick={() => toggleSecretVisibility(item.key)}
                          title={isSecretVisible ? 'Hide' : 'Show'}
                          tabIndex={-1}
                        >
                          {isSecretVisible ? <EyeOff size={15} /> : <Eye size={15} />}
                        </button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>

            <div className={styles.footer}>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={saving}
                id="save-env-settings-btn"
              >
                <span>{saving ? 'Saving…' : 'Save & Continue'}</span>
                <ArrowRight size={16} />
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
