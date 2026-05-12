<template>
  <aside
    class="layout-sidebar"
    :class="{
      collapsed: sidebarCollapsed,
      'mobile-open': mobileOpen,
    }"
  >
    <AppMenu :collapsed="sidebarCollapsed" />
  </aside>
</template>

<script setup lang="ts">
import AppMenu from './AppMenu.vue'
import { useLayout } from '@/composables/useLayout'

const { sidebarCollapsed, mobileOpen } = useLayout()
</script>
