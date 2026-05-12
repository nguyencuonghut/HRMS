import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

interface User {
  id: number
  username: string
  fullName: string
  role: string
  avatarUrl?: string
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))

  const isAuthenticated = computed(() => !!accessToken.value)

  async function login(username: string, password: string) {
    const { data } = await api.post('/auth/login', { username, password })
    accessToken.value = data.access_token
    localStorage.setItem('access_token', data.access_token)
    // TODO: fetch user profile after login
    user.value = { id: 1, username, fullName: 'Administrator', role: 'admin' }
  }

  function logout() {
    user.value = null
    accessToken.value = null
    localStorage.removeItem('access_token')
  }

  return { user, accessToken, isAuthenticated, login, logout }
})
