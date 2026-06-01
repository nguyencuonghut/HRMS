<template>
  <RecruitmentReportView
    :breadcrumb-crumbs="[
      { label: 'Báo cáo', to: '/reports' },
      { label: 'Báo cáo tuyển dụng' },
    ]"
  />
</template>

<script setup lang="ts">
import RecruitmentReportView from '@/views/recruitment/RecruitmentReportView.vue'
</script>
