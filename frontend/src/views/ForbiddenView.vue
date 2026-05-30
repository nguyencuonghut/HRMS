<template>
  <div class="forbidden-page">
    <div class="forbidden-card">
      <i class="pi pi-lock forbidden-icon" />
      <h1>403</h1>
      <h2>Không có quyền truy cập</h2>
      <p>Bạn không có quyền xem trang này. Liên hệ quản trị viên nếu cần hỗ trợ.</p>
      <div class="forbidden-actions">
        <Button label="Quay lại" icon="pi pi-arrow-left" @click="router.back()" />
        <Button label="Trang chủ" icon="pi pi-home" severity="secondary" outlined @click="router.push('/')" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import Button from 'primevue/button'

const router = useRouter()
</script>

<style>
.forbidden-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  padding: 2rem;
}

.forbidden-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  text-align: center;
  max-width: 400px;
}

.forbidden-icon {
  font-size: 3.5rem;
  color: var(--p-red-400);
}

.forbidden-card h1 {
  font-size: 4rem;
  font-weight: 800;
  color: var(--p-red-500);
  margin: 0;
  line-height: 1;
}

.forbidden-card h2 {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
}

.forbidden-card p {
  color: var(--l-text-muted);
  font-size: 0.9rem;
  margin: 0;
}

.forbidden-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.5rem;
  flex-wrap: wrap;
  justify-content: center;
}
</style>
