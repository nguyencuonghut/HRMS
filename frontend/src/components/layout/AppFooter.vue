<template>
  <footer class="layout-footer">
    <span>© {{ year }} Hồng Hà HRMS</span>
    <span class="layout-footer-sep">·</span>
    <span>v1.0.0</span>
  </footer>
</template>

<script setup lang="ts">
const year = new Date().getFullYear()
</script>
