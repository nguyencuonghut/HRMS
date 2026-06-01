<template>
  <div class="report-canonical-page">
    <div class="report-canonical-header">
      <h2>Báo cáo đào tạo</h2>
      <p>Tổng hợp hiệu quả đào tạo, chi phí, hoàn thành và tình trạng đào tạo bắt buộc.</p>
    </div>
    <TrainingReportTab />
  </div>
</template>

<script setup lang="ts">
import TrainingReportTab from '@/views/training/components/TrainingReportTab.vue'
</script>

<style>
.report-canonical-page {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.report-canonical-header h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 700;
}

.report-canonical-header p {
  margin: 0.4rem 0 0;
  color: var(--p-text-muted-color);
}
</style>
