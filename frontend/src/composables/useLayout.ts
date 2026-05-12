import { ref, computed } from 'vue'

const sidebarCollapsed = ref(false)
const mobileOpen = ref(false)
const darkMode = ref(false)

export function useLayout() {
  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function toggleMobile() {
    mobileOpen.value = !mobileOpen.value
  }

  function closeMobile() {
    mobileOpen.value = false
  }

  function toggleDarkMode() {
    darkMode.value = !darkMode.value
    document.documentElement.classList.toggle('dark-mode', darkMode.value)
    localStorage.setItem('hrms-dark-mode', String(darkMode.value))
  }

  function initDarkMode() {
    const saved = localStorage.getItem('hrms-dark-mode')
    if (saved === 'true') {
      darkMode.value = true
      document.documentElement.classList.add('dark-mode')
    }
  }

  return {
    sidebarCollapsed: computed(() => sidebarCollapsed.value),
    mobileOpen: computed(() => mobileOpen.value),
    darkMode: computed(() => darkMode.value),
    toggleSidebar,
    toggleMobile,
    closeMobile,
    toggleDarkMode,
    initDarkMode,
  }
}
