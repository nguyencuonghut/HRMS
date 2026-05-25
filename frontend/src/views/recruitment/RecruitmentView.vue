<template>
  <div class="recruitment-view">
    <div class="page-header">
      <div>
        <h2 class="page-title">Tuyển dụng</h2>
        <span class="page-subtitle">Yêu cầu tuyển dụng · Kế hoạch nhân sự</span>
      </div>
    </div>

    <Tabs v-model:value="activeTab">
      <TabList>
        <Tab value="jr">Yêu cầu tuyển dụng</Tab>
        <Tab value="headcount">Kế hoạch nhân sự</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="jr"><JRListTab /></TabPanel>
        <TabPanel value="headcount"><HeadcountPlanTab /></TabPanel>
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
import JRListTab from './components/JRListTab.vue'
import HeadcountPlanTab from './components/HeadcountPlanTab.vue'

const activeTab = ref('jr')
</script>
