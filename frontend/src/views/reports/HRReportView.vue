<template>
  <div class="hr-report-view">
    <div class="page-header">
      <div>
        <h2>Báo cáo nhân sự</h2>
        <div class="subtitle">
          Danh sách nhân viên, biến động nhân sự, thâm niên và cơ cấu tổ chức.
        </div>
      </div>
    </div>

    <Tabs v-model:value="activeTab">
      <TabList>
        <Tab value="employee-list">Danh sách nhân viên</Tab>
        <Tab value="movement">Biến động nhân sự</Tab>
        <Tab value="tenure">Thâm niên</Tab>
        <Tab value="org-structure">Cơ cấu tổ chức</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="employee-list">
          <EmployeeListTab />
        </TabPanel>
        <TabPanel value="movement">
          <MovementTab />
        </TabPanel>
        <TabPanel value="tenure">
          <Message severity="secondary" :closable="false">
            Tab Thâm niên sẽ hoàn thiện ở Slice 4.
          </Message>
        </TabPanel>
        <TabPanel value="org-structure">
          <Message severity="secondary" :closable="false">
            Tab Cơ cấu tổ chức sẽ hoàn thiện ở Slice 4.
          </Message>
        </TabPanel>
      </TabPanels>
    </Tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Message from 'primevue/message'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Tabs from 'primevue/tabs'

import EmployeeListTab from './components/hr/EmployeeListTab.vue'
import MovementTab from './components/hr/MovementTab.vue'

const activeTab = ref('employee-list')
</script>

<style>
.hr-report-view {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
</style>
