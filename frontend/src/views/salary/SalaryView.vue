<template>
  <div class="salary-view">
    <!-- Header -->
    <div class="page-header insurance-header">
      <div>
        <h2 class="page-title">Lương BHXH</h2>
        <span class="page-subtitle">Mức lương làm căn cứ đóng BHXH · Lịch sử điều chỉnh · Tổng hợp</span>
      </div>
    </div>

    <!-- Tabs -->
    <Tabs v-model:value="activeTab">
      <TabList>
        <Tab value="basis">Mức lương BHXH</Tab>
      </TabList>

      <TabPanels>
        <TabPanel value="basis">
          <BhxhBasisTable />
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

import BhxhBasisTable from './components/BhxhBasisTable.vue'

const activeTab = ref('basis')
</script>
