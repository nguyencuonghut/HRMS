<template>
  <div class="performance-view">
    <div class="page-header insurance-header">
      <div>
        <h2 class="page-title">Đánh giá Hiệu suất</h2>
        <span class="page-subtitle">KPI Tháng · Đánh giá Cuối năm · Báo cáo</span>
      </div>
    </div>

    <Tabs v-model:value="activeTab">
      <TabList>
        <Tab value="kpi">KPI Tháng</Tab>
        <Tab value="yearly">Đánh giá Cuối năm</Tab>
        <Tab value="report">Báo cáo</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="kpi"><KpiMonthlyTab /></TabPanel>
        <TabPanel value="yearly">
          <div class="perf-placeholder">
            <i class="pi pi-chart-line" />
            <span>Đánh giá cuối năm — đang phát triển (10.2)</span>
          </div>
        </TabPanel>
        <TabPanel value="report">
          <div class="perf-placeholder">
            <i class="pi pi-file-excel" />
            <span>Báo cáo hiệu suất — đang phát triển (10.4)</span>
          </div>
        </TabPanel>
      </TabPanels>
    </Tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Tabs from 'primevue/tabs'
import KpiMonthlyTab from './components/KpiMonthlyTab.vue'

const activeTab = ref('kpi')
</script>
