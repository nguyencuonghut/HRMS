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
import { onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import Toast from 'primevue/toast'
import ConfirmDialog from 'primevue/confirmdialog'
import AppTopbar from './AppTopbar.vue'
import AppSidebar from './AppSidebar.vue'
import AppFooter from './AppFooter.vue'
import { useLayout } from '@/composables/useLayout'

const { darkMode, mobileOpen, closeMobile, initDarkMode } = useLayout()
const route = useRoute()

// Scroll content area về đầu khi chuyển route
watch(
  () => route.path,
  () => {
    const el = document.getElementById('main-content')
    if (el) el.scrollTop = 0
  },
)

onMounted(() => {
  initDarkMode()
})
</script>
