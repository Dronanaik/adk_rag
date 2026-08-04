/* ============================================================
   API utility layer — all calls to the FastAPI backend
   Base URL is proxied through Vite (/api → http://localhost:8000)
   ============================================================ */

const BASE_URL = import.meta.env.VITE_API_URL || '/api'

/**
 * Shared fetch wrapper with user-id header injection.
 */
async function apiFetch(path, options = {}, userId = null) {
  const headers = {
    ...(options.headers || {}),
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
    } catch (_) {}
    throw new Error(detail)
  }

  return response.json()
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

// ---------------------------------------------------------------------------
// Documents
// ---------------------------------------------------------------------------

export async function listDocuments(userId) {
  return apiFetch('/documents', {}, userId)
}

export async function uploadDocument(file, userId) {
  const formData = new FormData()
  formData.append('file', file)

  return apiFetch(
    '/documents/upload',
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
