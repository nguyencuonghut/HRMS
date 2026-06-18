<template>
  <!-- Skip to main content (keyboard accessibility) -->
  <a href="#main-content" class="skip-to-content">Bỏ qua điều hướng</a>

  <div class="layout-wrapper" :class="{ 'dark-mode': darkMode }">
    <AppTopbar />

    <div class="layout-main">
      <!-- Sidebar overlay (mobile) -->
      <div v-if="mobileOpen" class="layout-sidebar-overlay" @click="closeMobile" />

      <AppSidebar />

      <main id="main-content" class="layout-content">
        <RouterView />
        <AppFooter />
      </main>
    </div>
  </div>

  <Toast position="top-right" />
  <ConfirmDialog />
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Toast from 'primevue/toast'
import ConfirmDialog from 'primevue/confirmdialog'
import { useToast } from 'primevue/usetoast'
import AppTopbar from './AppTopbar.vue'
import AppSidebar from './AppSidebar.vue'
import AppFooter from './AppFooter.vue'
import { useLayout } from '@/composables/useLayout'

const { darkMode, mobileOpen, closeMobile, initDarkMode } = useLayout()
const route = useRoute()
const router = useRouter()
const toast = useToast()

// Scroll content area về đầu khi chuyển route
watch(
  () => route.path,
  () => {
    const el = document.getElementById('main-content')
    if (el) el.scrollTop = 0
  },
)

// Lắng nghe lỗi 5xx từ axios interceptor và hiển thị toast
function onServerError(e: Event) {
  const { message } = (e as CustomEvent<{ status: number; message: string }>).detail
  toast.add({
    severity: 'error',
    summary: 'Lỗi máy chủ',
    detail: message,
    life: 6000,
  })
}

let lastToastMessage = ''
let lastToastTime = 0

// Lắng nghe lỗi 403 từ axios interceptor và xử lý
function onForbiddenError(e: Event) {
  const { message, method } = (e as CustomEvent<{ status: number; message: string; method: string }>).detail
  
  if (method.toLowerCase() === 'get') {
    router.push({ name: 'forbidden' })
  } else {
    const now = Date.now()
    if (message === lastToastMessage && now - lastToastTime < 2000) {
      return
    }
    lastToastMessage = message
    lastToastTime = now
    
    toast.add({
      severity: 'warn',
      summary: 'Không có quyền',
      detail: message,
      life: 4000,
    })
  }
}

onMounted(() => {
  initDarkMode()
  document.addEventListener('api:server-error', onServerError)
  document.addEventListener('api:forbidden', onForbiddenError)
})

onUnmounted(() => {
  document.removeEventListener('api:server-error', onServerError)
  document.removeEventListener('api:forbidden', onForbiddenError)
})
</script>
