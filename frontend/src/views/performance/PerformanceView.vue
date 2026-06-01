<template>
  <div class="performance-view">
    <div class="page-header insurance-header">
      <div>
        <h2 class="page-title">Đánh giá Hiệu suất</h2>
        <span class="page-subtitle">KPI Tháng · Đánh giá Cuối năm · Shortcut tới báo cáo hiệu suất</span>
      </div>
      <Button
        label="Xem báo cáo hiệu suất"
        icon="pi pi-chart-bar"
        severity="secondary"
        outlined
        @click="router.push('/reports/performance')"
      />
    </div>

    <Tabs v-model:value="activeTab">
      <TabList>
        <Tab value="kpi">KPI Tháng</Tab>
        <Tab value="yearly">Đánh giá Cuối năm</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="kpi"><KpiMonthlyTab /></TabPanel>
        <TabPanel value="yearly"><YearlyReviewTab /></TabPanel>
      </TabPanels>
    </Tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Tabs from 'primevue/tabs'
import KpiMonthlyTab from './components/KpiMonthlyTab.vue'
import YearlyReviewTab from './components/YearlyReviewTab.vue'

const router = useRouter()
const activeTab = ref('kpi')
</script>
