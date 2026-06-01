<template>
  <div class="rewards-view">
    <div class="page-header insurance-header">
      <div>
        <h2 class="page-title">Khen thưởng & Kỷ luật</h2>
        <span class="page-subtitle">Quyết định khen thưởng · Kỷ luật · Shortcut tới báo cáo tổng hợp</span>
      </div>
      <Button
        label="Xem báo cáo khen thưởng & kỷ luật"
        icon="pi pi-chart-bar"
        severity="secondary"
        outlined
        @click="router.push('/reports/rewards')"
      />
    </div>

    <Tabs v-model:value="activeTab">
      <TabList>
        <Tab value="rewards">Khen thưởng</Tab>
        <Tab value="disciplines">Kỷ luật</Tab>
      </TabList>

      <TabPanels>
        <TabPanel value="rewards">
          <RewardListTab />
        </TabPanel>
        <TabPanel value="disciplines">
          <DisciplineListTab />
        </TabPanel>
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

import RewardListTab from './components/RewardListTab.vue'
import DisciplineListTab from './components/DisciplineListTab.vue'

const router = useRouter()
const activeTab = ref('rewards')
</script>
