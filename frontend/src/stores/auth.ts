/**
 * Auth store — M5: Token migration localStorage → memory + HttpOnly cookie
 *
 * - access_token: in-memory (Pinia ref) — cleared on page refresh
 * - refresh_token: HttpOnly cookie — set/cleared by backend, JS không thể đọc
 *
 * Page refresh flow:
 *   App.vue onMounted → auth.tryRefresh() → POST /auth/refresh (cookie auto-sent)
 *   → nếu thành công: accessToken updated in memory → fetchMe()
 *   → nếu fail: stay unauthenticated → router guard redirect to /login
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import api from '@/services/api'

interface User {
  id: number
  email: string
  full_name: string
  is_active: boolean
  is_superuser: boolean
  roles: string[]
  permissions: string[]
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  // In-memory only — cleared on page refresh (intentional security choice)
  const accessToken = ref<string | null>(null)
  const sessionResolved = ref(false)
  let refreshPromise: Promise<boolean> | null = null

  const isAuthenticated = computed(() => !!accessToken.value)

  async function login(email: string, password: string) {
    const { data } = await api.post('/auth/login', { email, password })
    accessToken.value = data.access_token
    api.defaults.headers.common.Authorization = `Bearer ${data.access_token}`
    sessionResolved.value = true
    // refresh_token được set bởi backend qua HttpOnly cookie tự động
    await fetchMe()
  }

  async function fetchMe() {
    const { data } = await api.get('/auth/me')
    user.value = data
  }

  /**
   * Thử refresh access_token qua cookie — gọi khi page refresh.
   * Browser tự gửi cookie HttpOnly, không cần JS đọc refresh_token.
   * Returns true nếu thành công.
   */
  async function tryRefresh(): Promise<boolean> {
    if (accessToken.value) {
      sessionResolved.value = true
      return true
    }

    if (refreshPromise) {
      return refreshPromise
    }

    if (sessionResolved.value) {
      return false
    }

    refreshPromise = (async () => {
      try {
        // Dùng raw axios để tránh response interceptor của api.ts tự refresh lại chính /auth/refresh.
        const { data } = await axios.post('/api/v1/auth/refresh', undefined, {
          withCredentials: true,
        })
        accessToken.value = data.access_token
        api.defaults.headers.common.Authorization = `Bearer ${data.access_token}`
        await fetchMe()
        return true
      } catch {
        accessToken.value = null
        user.value = null
        delete api.defaults.headers.common.Authorization
        return false
      } finally {
        sessionResolved.value = true
        refreshPromise = null
      }
    })()

    return refreshPromise
  }

  function logout() {
    user.value = null
    accessToken.value = null
    sessionResolved.value = true
    delete api.defaults.headers.common.Authorization
    // Cookie sẽ bị xóa bởi backend khi gọi POST /auth/logout
  }

  function hasPermission(perm: string): boolean {
    if (!user.value) return false
    if (user.value.is_superuser || user.value.permissions.includes('*')) return true
    return user.value.permissions.includes(perm)
  }

  return {
    user,
    accessToken,
    isAuthenticated,
    sessionResolved,
    login,
    fetchMe,
    tryRefresh,
    logout,
    hasPermission,
  }
})

export type { }
