<template>
  <header class="layout-topbar">
    <!-- Logo -->
    <RouterLink to="/" class="layout-topbar-logo">
      <img src="/logo.svg" alt="Hồng Hà HRMS" />
      <span class="logo-text" v-if="!sidebarCollapsed">Hồng Hà HRMS</span>
    </RouterLink>

    <!-- Sidebar toggle -->
    <Button
      :icon="sidebarCollapsed ? 'pi pi-bars' : 'pi pi-bars'"
      text
      rounded
      severity="secondary"
      class="hidden md:flex"
      @click="toggleSidebar"
      v-tooltip.bottom="'Thu gọn menu'"
    />

    <!-- Mobile hamburger -->
    <Button
      icon="pi pi-bars"
      text
      rounded
      severity="secondary"
      class="flex md:hidden"
      @click="toggleMobile"
    />

    <div class="topbar-spacer" />

    <!-- Dark mode toggle -->
    <Button
      :icon="darkMode ? 'pi pi-sun' : 'pi pi-moon'"
      text
      rounded
      severity="secondary"
      v-tooltip.bottom="darkMode ? 'Chế độ sáng' : 'Chế độ tối'"
      @click="toggleDarkMode"
    />

    <!-- Notifications -->
    <Button
      icon="pi pi-bell"
      text
      rounded
      severity="secondary"
      v-tooltip.bottom="'Thông báo'"
    />

    <!-- User menu -->
    <Button
      :label="user?.fullName ?? 'Admin'"
      icon="pi pi-user"
      text
      severity="secondary"
      class="user-btn"
      @click="userMenu?.toggle($event)"
    />
    <Menu ref="userMenu" :model="userMenuItems" popup />
  </header>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Menu from 'primevue/menu'
import { useLayout } from '@/composables/useLayout'
import { useAuthStore } from '@/stores/auth'

const { sidebarCollapsed, darkMode, mobileOpen, toggleSidebar, toggleMobile, toggleDarkMode } = useLayout()
const auth = useAuthStore()
const router = useRouter()
const userMenu = ref()
const user = computed(() => auth.user)

const userMenuItems = [
  { label: 'Thông tin tài khoản', icon: 'pi pi-user' },
  { label: 'Đổi mật khẩu', icon: 'pi pi-lock' },
  { separator: true },
  {
    label: 'Đăng xuất',
    icon: 'pi pi-sign-out',
    command: () => {
      auth.logout()
      router.push('/login')
    },
  },
]
</script>

<style scoped>
.user-btn { font-size: 0.875rem; }
.hidden   { display: none; }
.flex     { display: flex; }
@media (min-width: 768px) {
  .hidden.md\:flex { display: flex; }
  .flex.md\:hidden { display: none; }
}
</style>
