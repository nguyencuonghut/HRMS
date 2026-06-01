<template>
  <div class="report-canonical-page">
    <div class="report-canonical-header">
      <h2>Báo cáo khen thưởng & kỷ luật</h2>
      <p>Thống kê, đối chiếu và xuất báo cáo tổng hợp quyết định khen thưởng, kỷ luật.</p>
    </div>
    <RewardDisciplineReport />
  </div>
</template>

<script setup lang="ts">
import RewardDisciplineReport from '@/views/rewards/components/RewardDisciplineReport.vue'
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
