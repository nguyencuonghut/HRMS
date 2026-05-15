<template>
  <div class="employee-list-page">
    <div class="page-header">
      <div>
        <h2>Danh sách nhân viên</h2>
        <span class="subtitle">Điểm vào tạm thời để preview tích hợp danh mục hành chính và học vấn</span>
      </div>
      <Button
        label="Mở preview hồ sơ"
        icon="pi pi-id-card"
        @click="router.push('/employees/preview')"
      />
    </div>

    <div class="placeholder-card">
      <i class="pi pi-users" />
      <strong>Danh sách nhân viên đầy đủ đang phát triển</strong>
      <span>
        Trong phase hiện tại, bạn có thể mở màn preview hồ sơ để kiểm tra contract dùng lại
        từ danh mục hành chính và danh mục học vấn.
      </span>
      <Button
        label="Đi tới hồ sơ preview"
        icon="pi pi-arrow-right"
        severity="secondary"
        outlined
        @click="router.push('/employees/preview')"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import Button from 'primevue/button'

const router = useRouter()
</script>

<style scoped>
.employee-list-page {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.page-header h2 {
  margin: 0 0 0.2rem;
  font-size: 1.5rem;
  font-weight: 700;
}

.subtitle {
  color: var(--l-text-muted);
}

.placeholder-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.85rem;
  min-height: 240px;
  padding: 1.5rem;
  text-align: center;
  background: var(--l-surface);
  border: 1px dashed color-mix(in srgb, var(--l-border) 82%, var(--p-primary-color) 18%);
  border-radius: 20px;
  color: var(--l-text-muted);
}

.placeholder-card strong {
  color: var(--l-text);
}

.placeholder-card i {
  font-size: 2rem;
  opacity: 0.45;
}

.placeholder-card span {
  max-width: 54ch;
  line-height: 1.6;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
  }
}
</style>
