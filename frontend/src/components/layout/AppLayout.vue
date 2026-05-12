<template>
  <div class="layout-wrapper" :class="{ 'dark-mode': darkMode }">
    <AppTopbar />

    <div class="layout-main">
      <!-- Sidebar overlay (mobile) -->
      <div v-if="mobileOpen" class="layout-sidebar-overlay" @click="closeMobile" />

      <AppSidebar />

      <main class="layout-content">
        <RouterView />
        <AppFooter />
      </main>
    </div>
  </div>

  <Toast position="top-right" />
  <ConfirmDialog />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import Toast from 'primevue/toast'
import ConfirmDialog from 'primevue/confirmdialog'
import AppTopbar from './AppTopbar.vue'
import AppSidebar from './AppSidebar.vue'
import AppFooter from './AppFooter.vue'
import { useLayout } from '@/composables/useLayout'

const { darkMode, mobileOpen, closeMobile, initDarkMode } = useLayout()

onMounted(() => {
  initDarkMode()
})
</script>
