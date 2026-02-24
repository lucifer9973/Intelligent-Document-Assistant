import axios from 'axios'

function resolveApiBase() {
  const explicit = import.meta.env.VITE_API_BASE
  if (explicit) return explicit

  if (import.meta.env.DEV) return 'http://127.0.0.1:8000'

  // Production build:
  // - If served over http(s), use same-origin API.
  // - If opened as file://, fall back to local backend URL.
  if (typeof window !== 'undefined') {
    const origin = window.location.origin || ''
    if (origin.startsWith('http://') || origin.startsWith('https://')) {
      return ''
    }
  }

  return 'http://127.0.0.1:8000'
}

const rawBase = resolveApiBase()
const API_BASE = rawBase.endsWith('/') ? rawBase.slice(0, -1) : rawBase

export const client = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
})

export default client
