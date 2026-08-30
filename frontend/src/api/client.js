import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || ''

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'ngrok-skip-browser-warning': 'true',
  },
})

apiClient.interceptors.request.use((config) => {
  const initData = window.Telegram?.WebApp?.initData
  if (initData) {
    config.headers['X-Init-Data'] = initData
  }
  return config
})

// Every catch block across the app does `e.response?.data?.detail || '...'`
// to show an error message — that only works when `detail` is a plain
// string. FastAPI's own validation errors (422s the backend never wraps in
// a custom HTTPException) return `detail` as a list of {loc, msg, type}
// objects instead, which Vue then renders as raw JSON/[object Object]
// instead of a message. Normalizing it here fixes every call site at once
// instead of touching each one.
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error.response?.data?.detail
    if (Array.isArray(detail)) {
      error.response.data.detail = detail.map((d) => d?.msg || String(d)).join('; ') || 'Invalid request.'
    } else if (detail && typeof detail === 'object') {
      error.response.data.detail = detail.msg || 'Invalid request.'
    }
    return Promise.reject(error)
  },
)

export default apiClient