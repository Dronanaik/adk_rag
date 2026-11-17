const API_BASE = import.meta.env.VITE_API_URL || '/api'
const TOKEN_STORAGE_KEY = 'adk_rag_auth_token'

let _handlersInstalled = false

function getAuthToken() {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY) || null
  } catch {
    return null
  }
}

/**
 * Forward a structured client-side error or diagnostic event to POST /logs/client.
 * Never throws so error reporting cannot trigger secondary failures.
 */
export function reportClientError(source, message, detail = {}) {
  try {
    const token = getAuthToken()
    const payload = {
      level: detail.level || 'ERROR',
      source: String(source || 'frontend'),
      message: String(message || 'Unknown client error'),
      stack: detail.stack ? String(detail.stack).slice(0, 8000) : undefined,
      route: detail.route || (typeof window !== 'undefined' ? window.location.pathname : undefined),
      session_id: detail.sessionId || detail.session_id || undefined,
      request_id: detail.requestId || detail.request_id || undefined,
      extra: detail.extra || undefined,
    }

    const headers = { 'Content-Type': 'application/json' }
    if (token) {
      headers.Authorization = `Bearer ${token}`
    }

    fetch(`${API_BASE}/logs/client`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
      keepalive: true,
    }).catch(() => {
      // Silently ignore telemetry transport failures
    })
  } catch {
    // Never let logger throw
  }
}

/**
 * Install global window.onerror and unhandledrejection listeners once.
 */
export function installGlobalErrorHandlers() {
  if (_handlersInstalled || typeof window === 'undefined') return
  _handlersInstalled = true

  window.addEventListener('error', (event) => {
    reportClientError('window.onerror', event.message || 'Uncaught window error', {
      stack: event.error?.stack,
      extra: {
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
      },
    })
  })

  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason
    const message =
      reason instanceof Error
        ? reason.message
        : typeof reason === 'string'
          ? reason
          : 'Unhandled promise rejection'
    reportClientError('unhandledrejection', message, {
      stack: reason instanceof Error ? reason.stack : undefined,
    })
  })
}
