/**
 * Axios instance dùng chung cho toàn bộ app.
 *
 * Tính năng:
 *  - Timeout 30s mặc định
 *  - Tự gắn Bearer token từ localStorage vào header
 *  - Network error → retry 1 lần sau 1 giây
 *  - 401 → thử refresh token → nếu fail → logout + redirect /login
 *  - 5xx → dispatch event 'api:server-error' để App.vue hiển thị toast
 */
import axios, { type AxiosRequestConfig } from 'axios'
import { getActivePinia } from 'pinia'

// ── Khai báo custom fields trên config để theo dõi retry ─────────────────────
declare module 'axios' {
  interface InternalAxiosRequestConfig {
    _retried?: boolean        // đã retry do network error
    _authRetried?: boolean    // đã retry sau khi refresh token
  }
}

// ── Tạo instance ──────────────────────────────────────────────────────────────
const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

// ── Request interceptor — gắn auth token ─────────────────────────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ── Response interceptor ──────────────────────────────────────────────────────
api.interceptors.response.use(
  (res) => res,

  async (error) => {
    const config = error.config as AxiosRequestConfig & {
      _retried?: boolean
      _authRetried?: boolean
    }

    // ── Network error hoặc timeout → retry 1 lần sau 1 giây ─────────────────
    if (!error.response && !config._retried) {
      config._retried = true
      await _delay(1000)
      return api(config)
    }

    const status = error.response?.status

    // ── 401 Unauthorized → thử refresh token ─────────────────────────────────
    if (status === 401 && !config._authRetried) {
      config._authRetried = true

      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          // Dùng axios raw (không intercepted) để tránh vòng lặp vô hạn
          const { data } = await axios.post('/api/v1/auth/refresh', {
            refresh_token: refreshToken,
          })
          // Lưu token mới
          localStorage.setItem('access_token', data.access_token)
          if (data.refresh_token) {
            localStorage.setItem('refresh_token', data.refresh_token)
          }
          // Cập nhật Pinia store nếu đang active
          _syncAuthStore(data.access_token)

          // Retry request gốc với token mới
          if (config.headers) {
            config.headers.Authorization = `Bearer ${data.access_token}`
          }
          return api(config)
        } catch {
          // Refresh thất bại → logout hoàn toàn
          _logoutAndRedirect()
          return Promise.reject(error)
        }
      }

      // Không có refresh token → logout
      _logoutAndRedirect()
      return Promise.reject(error)
    }

    // ── 5xx Server Error → thông báo cho user qua custom event ───────────────
    if (status !== undefined && status >= 500) {
      const detail = error.response?.data?.detail ?? 'Máy chủ gặp sự cố, vui lòng thử lại.'
      document.dispatchEvent(
        new CustomEvent('api:server-error', {
          detail: { status, message: detail },
        })
      )
    }

    return Promise.reject(error)
  }
)

// ── Helpers ───────────────────────────────────────────────────────────────────

function _delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function _syncAuthStore(newToken: string) {
  // Sync Pinia auth store nếu đã được khởi tạo
  try {
    const pinia = getActivePinia()
    if (!pinia) return
    // Import động để tránh circular dependency
    import('@/stores/auth').then(({ useAuthStore }) => {
      const store = useAuthStore(pinia)
      store.accessToken = newToken
    })
  } catch {
    // Pinia chưa ready → bỏ qua, localStorage đã được cập nhật
  }
}

function _logoutAndRedirect() {
  // Xóa tokens
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')

  // Sync Pinia store
  try {
    const pinia = getActivePinia()
    if (pinia) {
      import('@/stores/auth').then(({ useAuthStore }) => {
        const store = useAuthStore(pinia)
        store.logout()
      })
    }
  } catch {
    // Ignore
  }

  // Redirect về login (chỉ nếu chưa ở trang login)
  if (!window.location.pathname.startsWith('/login')) {
    window.location.href = '/login'
  }
}

export default api
