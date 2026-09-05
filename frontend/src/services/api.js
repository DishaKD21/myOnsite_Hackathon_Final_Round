const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    })
  } catch {
    throw new Error(`Backend unavailable at ${API_BASE_URL}. Please start FastAPI and try again.`)
  }

  let body = null
  try {
    body = await response.json()
  } catch {
    body = null
  }

  if (!response.ok) {
    const detail = typeof body?.detail === 'string' ? body.detail : `Request failed with HTTP ${response.status}.`
    throw new Error(detail)
  }
  return body
}

const json = (method, body) => ({ method, body: JSON.stringify(body) })

export const api = {
  baseUrl: API_BASE_URL,
  getSourceState: () => request('/source/state'),
  seedSource: (files) => request('/source/seed', json('POST', files)),
  modifySource: (fileId, content) => request('/source/modify', json('POST', { file_id: fileId, content })),
  addSource: (fileId, filename, content) => request('/source/add', json('POST', { file_id: fileId, filename, content })),
  getBackups: () => request('/backups'),
  getBackupDetails: (id) => request(`/backups/${encodeURIComponent(id)}`),
  createFullBackup: () => request('/backup/full', { method: 'POST' }),
  createIncrementalBackup: () => request('/backup/incremental', { method: 'POST' }),
  validateBackup: (id) => request(`/backups/${encodeURIComponent(id)}/validate`, { method: 'POST' }),
  verifyChain: () => request('/chain/verify'),
  restore: (id) => request('/restore', json('POST', { recovery_point_id: id })),
  verifyRestore: (id) => request('/restore/verify', json('POST', { recovery_point_id: id })),
  findAlternate: (id) => request(`/backups/${encodeURIComponent(id)}/find-alternate`, { method: 'POST' }),
  verifyAlternate: (id, alternateId) => request(`/backups/${encodeURIComponent(id)}/verify-alternate?alternate_id=${encodeURIComponent(alternateId)}`, { method: 'POST' }),
}
