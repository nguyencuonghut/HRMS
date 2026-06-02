<template>
  <div class="report-canonical-page">
    <div class="report-canonical-header">
      <h2>Báo cáo checklist hồ sơ lao động</h2>
      <p>Theo dõi mức độ hoàn thành hồ sơ lao động bắt buộc, các giấy tờ còn thiếu và tình trạng sắp hết hạn.</p>
    </div>
    <DocumentChecklistSummaryTab />
  </div>
</template>

<script setup lang="ts">
import DocumentChecklistSummaryTab from '@/views/recruitment/components/DocumentChecklistSummaryTab.vue'
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
