import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
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
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))

  const isAuthenticated = computed(() => !!accessToken.value)

  async function login(email: string, password: string) {
    const { data } = await api.post('/auth/login', { email, password })
    accessToken.value = data.access_token
    localStorage.setItem('access_token', data.access_token)
    if (data.refresh_token) {
      localStorage.setItem('refresh_token', data.refresh_token)
    }
    await fetchMe()
  }

  async function fetchMe() {
    const { data } = await api.get('/auth/me')
    user.value = data
  }

  function logout() {
    user.value = null
    accessToken.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  function hasPermission(perm: string): boolean {
    if (!user.value) return false
    if (user.value.is_superuser || user.value.permissions.includes('*')) return true
    return user.value.permissions.includes(perm)
  }

  return { user, accessToken, isAuthenticated, login, fetchMe, logout, hasPermission }
})
