<template>
  <div class="rewards-view">
    <div class="page-header insurance-header">
      <div>
        <h2 class="page-title">Khen thưởng & Kỷ luật</h2>
        <span class="page-subtitle">Quyết định khen thưởng · Kỷ luật · Báo cáo tổng hợp</span>
      </div>
    </div>

    <Tabs v-model:value="activeTab">
      <TabList>
        <Tab value="rewards">Khen thưởng</Tab>
        <Tab value="disciplines">Kỷ luật</Tab>
        <Tab value="report">Báo cáo</Tab>
      </TabList>

      <TabPanels>
        <TabPanel value="rewards">
          <RewardListTab />
        </TabPanel>
        <TabPanel value="disciplines">
          <div class="rewards-placeholder">
            <i class="pi pi-gavel" />
            <span>Kỷ luật — đang phát triển (Plan 8.2)</span>
          </div>
        </TabPanel>
        <TabPanel value="report">
          <div class="rewards-placeholder">
            <i class="pi pi-chart-bar" />
            <span>Báo cáo tổng hợp — đang phát triển (Plan 8.3)</span>
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

import RewardListTab from './components/RewardListTab.vue'

const activeTab = ref('rewards')
</script>
