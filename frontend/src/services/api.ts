/**
 * Axios instance — M5: Token migration localStorage → memory + HttpOnly cookie
 *
 * - access_token: lấy từ Pinia store (in-memory), gắn vào Authorization header
 * - refresh_token: HttpOnly cookie — browser tự gửi đến /api/v1/auth/refresh
 *   → KHÔNG cần JS đọc/ghi localStorage cho refresh_token nữa
 *
 * Flow 401:
 *   → POST /api/v1/auth/refresh (no body, browser sends cookie)
 *   → nếu thành công: cập nhật accessToken in store → retry request gốc
 *   → nếu fail: logout + redirect /login
 */
import axios, { type AxiosRequestConfig } from 'axios'
import { pinia } from '@/stores/pinia'

declare module 'axios' {
  interface InternalAxiosRequestConfig {
    _retried?: boolean
    _authRetried?: boolean
  }
}

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
  // Cookie được gửi tự động bởi browser (withCredentials không cần cho same-origin)
})

function _isAuthEndpoint(url?: string): boolean {
  if (!url) return false
  return url.includes('/auth/login') || url.includes('/auth/refresh') || url.includes('/auth/logout')
}

// ── Request interceptor — gắn access_token từ Pinia store ─────────────────────
api.interceptors.request.use((config) => {
  const token = _getAccessToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ── Response interceptor ───────────────────────────────────────────────────────
api.interceptors.response.use(
  (res) => res,

  async (error) => {
    const config = error.config as AxiosRequestConfig & {
      _retried?: boolean
      _authRetried?: boolean
    }

    // Network error / timeout → retry 1 lần sau 1 giây
    if (!error.response && !config._retried) {
      config._retried = true
      await _delay(1000)
      return api(config)
    }

    const status = error.response?.status

    // Không retry auth flow trên chính auth endpoints để tránh refresh recursion / rate-limit storm.
    if (_isAuthEndpoint(config.url)) {
      return Promise.reject(error)
    }

    // 401 → thử refresh qua HttpOnly cookie
    if (status === 401 && !config._authRetried) {
      config._authRetried = true
      try {
        // POST /auth/refresh không có body — browser gửi cookie tự động
        const { data } = await axios.post('/api/v1/auth/refresh', undefined, {
          withCredentials: true,
        })
        // Cập nhật access_token in-memory
        _syncAuthStore(data.access_token)

        if (config.headers) {
          config.headers.Authorization = `Bearer ${data.access_token}`
        }
        return api(config)
      } catch {
        _logoutAndRedirect()
        return Promise.reject(error)
      }
    }

    // 5xx → toast
    if (status !== undefined && status >= 500) {
      const detail = error.response?.data?.detail ?? 'Máy chủ gặp sự cố, vui lòng thử lại.'
      document.dispatchEvent(new CustomEvent('api:server-error', { detail: { status, message: detail } }))
    }

    return Promise.reject(error)
  }
)

// ── Helpers ────────────────────────────────────────────────────────────────────

function _getAccessToken(): string | null {
  try {
    // Setup store trong Pinia được unwrap; accessToken ở đây là string | null, không phải ref.
    const storeMap = (pinia as unknown as { _s: Map<string, { accessToken: string | null }> })._s
    return storeMap?.get('auth')?.accessToken ?? null
  } catch {
    return null
  }
}

function _delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function _syncAuthStore(newToken: string) {
  try {
    api.defaults.headers.common.Authorization = `Bearer ${newToken}`
    import('@/stores/auth').then(({ useAuthStore }) => {
      const store = useAuthStore(pinia)
      store.accessToken = newToken
    })
  } catch {
    // Pinia chưa ready
  }
}

function _logoutAndRedirect() {
  try {
    delete api.defaults.headers.common.Authorization
    import('@/stores/auth').then(({ useAuthStore }) => {
      const store = useAuthStore(pinia)
      store.logout()
    })
  } catch {
    // Ignore
  }

  // Gọi logout endpoint để xóa cookie (fire-and-forget)
  axios.post('/api/v1/auth/logout', undefined, { withCredentials: true }).catch(() => {})

  if (!window.location.pathname.startsWith('/login')) {
    window.location.href = '/login'
  }
}

export default api
