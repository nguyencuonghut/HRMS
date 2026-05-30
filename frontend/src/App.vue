<template>
  <!-- Global Error Boundary — hiện khi component nào đó throw unhandled error -->
  <div v-if="appError" class="app-error-boundary">
    <div class="app-error-card">
      <i class="pi pi-exclamation-triangle app-error-icon" />
      <h2>Đã xảy ra lỗi không mong muốn</h2>
      <p>Vui lòng tải lại trang. Nếu lỗi tiếp tục, liên hệ bộ phận IT.</p>
      <div class="app-error-detail" v-if="appError.message">
        <code>{{ appError.message }}</code>
      </div>
      <div class="app-error-actions">
        <button class="app-error-btn app-error-btn-primary" @click="reloadPage">
          <i class="pi pi-refresh" />  Tải lại trang
        </button>
        <button class="app-error-btn app-error-btn-secondary" @click="clearError">
          Thử tiếp tục
        </button>
      </div>
    </div>
  </div>

  <RouterView v-else />
</template>

<script setup lang="ts">
import { onErrorCaptured, onMounted, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const appError = ref<Error | null>(null)

// Restore user info after page refresh
onMounted(async () => {
  if (auth.accessToken && !auth.user) {
    try {
      await auth.fetchMe()
    } catch {
      auth.logout()
    }
  }
})

// Global error boundary — catch mọi unhandled component error
onErrorCaptured((err: Error, _instance, info) => {
  console.error('[App ErrorBoundary]', err, '\nComponent:', info)
  appError.value = err

  // Gửi lên Sentry nếu đã được cấu hình
  const w = window as unknown as { Sentry?: { captureException: (e: Error, opts?: object) => void } }
  w.Sentry?.captureException(err, { extra: { vueInfo: info } })

  return false // ngăn propagation tiếp lên
})

function reloadPage() {
  window.location.reload()
}

function clearError() {
  // Cho phép user thử tiếp tục — xóa error state
  appError.value = null
}
</script>

<style>
.app-error-boundary {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100dvh;
  padding: 2rem;
  background: var(--l-bg, #f8fafc);
}

.app-error-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  text-align: center;
  max-width: 480px;
  padding: 2.5rem 2rem;
  background: var(--l-surface, white);
  border: 1px solid var(--l-border, #e2e8f0);
  border-radius: 1rem;
  box-shadow: 0 4px 24px rgba(0,0,0,.08);
}

.app-error-icon {
  font-size: 3rem;
  color: #f59e0b;
}

.app-error-card h2 {
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0;
  color: var(--l-text, #1e293b);
}

.app-error-card p {
  color: var(--l-text-muted, #64748b);
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.6;
}

.app-error-detail {
  background: var(--l-surface-raised, #f1f5f9);
  border-radius: 0.5rem;
  padding: 0.5rem 1rem;
  font-size: 0.8rem;
  max-width: 100%;
  overflow-x: auto;
  color: #ef4444;
}

.app-error-actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  justify-content: center;
  margin-top: 0.5rem;
}

.app-error-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.6rem 1.25rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: opacity 0.15s;
}

.app-error-btn:hover {
  opacity: 0.85;
}

.app-error-btn-primary {
  background: var(--p-primary-color, #0d9488);
  color: white;
}

.app-error-btn-secondary {
  background: var(--l-surface-raised, #f1f5f9);
  color: var(--l-text, #1e293b);
  border: 1px solid var(--l-border, #e2e8f0);
}
</style>
