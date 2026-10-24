import axios from 'axios'

/** Same-origin by default (Vite proxy or /desk on :8001). */
const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '')

export const api = axios.create({
  baseURL: API_BASE || undefined,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('mailroom_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

function loginPath(): string {
  const base = import.meta.env.BASE_URL || '/'
  return `${base.endsWith('/') ? base : `${base}/`}login`
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = String(error.config?.url || '')
    // Display /api/* stays open. Only operator /v1 routes are JWT-gated.
    if (error.response?.status === 401 && url.includes('/v1/')) {
      localStorage.removeItem('mailroom_token')
      window.location.href = loginPath()
    }
    return Promise.reject(error)
  },
)
