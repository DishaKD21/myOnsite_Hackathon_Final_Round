const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

export async function request(path, options = {}) {
  let response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: options.body instanceof FormData ? { ...options.headers } : { 'Content-Type': 'application/json', ...options.headers },
    })
  } catch {
    throw new Error(`Backend unavailable at ${API_BASE_URL}. Please start FastAPI and try again.`)
  }

  let body = null
  try { body = await response.json() } catch { body = null }
  if (!response.ok) {
    const detail = typeof body?.detail === 'string' ? body.detail : `Request failed with HTTP ${response.status}.`
    throw new Error(detail)
  }
  return body
}

export const apiBaseUrl = API_BASE_URL
export const jsonRequest = (method, body) => ({ method, body: JSON.stringify(body) })
