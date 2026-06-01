<template>
  <div class="report-canonical-page">
    <div class="report-canonical-header">
      <h2>Báo cáo hiệu suất / KPI</h2>
      <p>Phân tích xếp loại, xu hướng KPI theo tháng và hiệu suất theo phòng ban.</p>
    </div>
    <PerformanceReportTab />
  </div>
</template>

<script setup lang="ts">
import PerformanceReportTab from '@/views/performance/components/PerformanceReportTab.vue'
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
