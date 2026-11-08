/* ============================================================
   API utility layer — all calls to the FastAPI backend
   Base URL is proxied through Vite (/api → http://localhost:8000)
   ============================================================ */

const BASE_URL = import.meta.env.VITE_API_URL || '/api'
const TOKEN_STORAGE_KEY = 'adk_rag_auth_token'
const USER_STORAGE_KEY = 'adk_rag_user'

export function getStoredAuth() {
  try {
    const token = localStorage.getItem(TOKEN_STORAGE_KEY)
    const userRaw = localStorage.getItem(USER_STORAGE_KEY)
    const user = userRaw ? JSON.parse(userRaw) : null
    if (token && user && user.email) {
      return { token, user }
    }
  } catch (err) {
    // Ignore malformed localStorage state
    void err
  }
  return { token: null, user: null }
}

export function setStoredAuth(token, user) {
  try {
    localStorage.setItem(TOKEN_STORAGE_KEY, token)
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user))
  } catch (err) {
    // Ignore storage quota errors
    void err
  }
}

export function clearStoredAuth() {
  try {
    localStorage.removeItem(TOKEN_STORAGE_KEY)
    localStorage.removeItem(USER_STORAGE_KEY)
  } catch (err) {
    // Ignore storage errors
    void err
  }
}

/**
 * Shared fetch wrapper with Bearer JWT token + user-id header injection.
 */
async function apiFetch(path, options = {}, userId = null) {
  const { token } = getStoredAuth()
  const headers = {
    ...(options.headers || {}),
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  if (userId) {
    headers['x-user-id'] = userId
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    let detail = `HTTP ${response.status}`
    try {
      const body = await response.json()
      detail = body.detail || detail
    } catch (err) {
      // Fallback to HTTP status code when response body is not JSON
      void err
    }
    throw new Error(detail)
  }

  return response.json()
}

// ---------------------------------------------------------------------------
// Authentication (Neon PostgreSQL)
// ---------------------------------------------------------------------------

export async function signUp(fullName, email, password) {
  const data = await apiFetch('/auth/signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      full_name: fullName,
      email,
      password,
    }),
  })
  if (data.access_token && data.user) {
    setStoredAuth(data.access_token, data.user)
  }
  return data
}

export async function signIn(email, password) {
  const data = await apiFetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email,
      password,
    }),
  })
  if (data.access_token && data.user) {
    setStoredAuth(data.access_token, data.user)
  }
  return data
}

export async function fetchCurrentUser() {
  return apiFetch('/auth/me')
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export async function checkHealth() {
  return apiFetch('/health')
}

// ---------------------------------------------------------------------------
// Ingest status
// ---------------------------------------------------------------------------

export async function getIngestStatus() {
  return apiFetch('/ingest/status')
}

export async function getIngestProgress(userId) {
  return apiFetch('/ingest/progress', {}, userId)
}

// ---------------------------------------------------------------------------
// Documents
// ---------------------------------------------------------------------------

export async function listDocuments(userId) {
  return apiFetch('/documents', {}, userId)
}

export async function uploadDocument(file, userId, { docIndex = 1, totalDocs = 1 } = {}) {
  const formData = new FormData()
  formData.append('file', file)

  return apiFetch(
    `/documents/upload?doc_index=${encodeURIComponent(docIndex)}&total_docs=${encodeURIComponent(totalDocs)}`,
    {
      method: 'POST',
      body: formData,
    },
    userId
  )
}

export async function deleteDocument(documentId, userId) {
  return apiFetch(
    `/documents/${documentId}`,
    { method: 'DELETE' },
    userId
  )
}

// ---------------------------------------------------------------------------
// Knowledge Graph (Neo4j)
// ---------------------------------------------------------------------------

export async function getKnowledgeGraph(userId, query = '') {
  const qs = query ? `?q=${encodeURIComponent(query)}` : ''
  return apiFetch(`/graph${qs}`, {}, userId)
}

export async function getEntityRelationships(entityName, userId) {
  return apiFetch(`/graph/entity/${encodeURIComponent(entityName)}`, {}, userId)
}

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------

export async function sendMessage(query, userId, sessionId = null) {
  return apiFetch(
    '/chat',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, session_id: sessionId }),
    },
    userId
  )
}

// ---------------------------------------------------------------------------
// Environment & Connection Settings
// ---------------------------------------------------------------------------

export async function getEnvSettings() {
  return apiFetch('/settings/env')
}

export async function updateEnvSettings(values, persistToEnv = false) {
  return apiFetch('/settings/env', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      values,
      persist_to_env: Boolean(persistToEnv),
    }),
  })
}

export async function resetEnvSettings() {
  return apiFetch('/settings/env/reset', {
    method: 'POST',
  })
}
