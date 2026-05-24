<template>
  <div class="training-view">
    <div class="page-header insurance-header">
      <div>
        <h2 class="page-title">Đào tạo &amp; Phát triển</h2>
        <span class="page-subtitle">Khóa học · Kế hoạch đào tạo · Theo dõi · Chứng chỉ</span>
      </div>
    </div>

    <Tabs v-model:value="activeTab">
      <TabList>
        <Tab value="courses">Khóa học</Tab>
        <Tab value="plans">Kế hoạch đào tạo</Tab>
        <Tab value="records">Theo dõi</Tab>
        <Tab value="certs">Chứng chỉ</Tab>
        <Tab value="report">Báo cáo</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="courses"><CourseListTab /></TabPanel>
        <TabPanel value="plans"><TrainingPlanTab /></TabPanel>
        <TabPanel value="records"><TrainingRecordTab /></TabPanel>
        <TabPanel value="certs"><CertificateTab /></TabPanel>
        <TabPanel value="report"><TrainingReportTab /></TabPanel>
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
import CourseListTab from './components/CourseListTab.vue'
import TrainingPlanTab from './components/TrainingPlanTab.vue'
import TrainingRecordTab from './components/TrainingRecordTab.vue'
import CertificateTab from './components/CertificateTab.vue'
import TrainingReportTab from './components/TrainingReportTab.vue'

const activeTab = ref('courses')
</script>
