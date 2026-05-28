<template>
  <RouterView />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

// Restore user info after page refresh if token is still present
onMounted(async () => {
  if (auth.accessToken && !auth.user) {
    try {
      await auth.fetchMe()
    } catch {
      // Token expired / invalid — clear it so router guard redirects to login
      auth.logout()
    }
  }
})
</script>
