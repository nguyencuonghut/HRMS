<template>
  <div class="recruitment-view">
    <div class="page-header">
      <div>
        <h2 class="page-title">Tuyển dụng</h2>
        <span class="page-subtitle">Yêu cầu tuyển dụng · Tin tuyển dụng · Ứng viên · Kế hoạch nhân sự</span>
      </div>
    </div>

    <Tabs v-model:value="activeTab">
      <TabList>
        <Tab value="jr">Yêu cầu tuyển dụng</Tab>
        <Tab value="postings">Tin tuyển dụng</Tab>
        <Tab value="candidates">Ứng viên</Tab>
        <Tab value="headcount">Kế hoạch nhân sự</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="jr"><JRListTab /></TabPanel>
        <TabPanel value="postings"><JobPostingTab /></TabPanel>
        <TabPanel value="candidates"><CandidateListTab /></TabPanel>
        <TabPanel value="headcount"><HeadcountPlanTab /></TabPanel>
      </TabPanels>
    </Tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Tabs from 'primevue/tabs'
import CandidateListTab from './components/CandidateListTab.vue'
import JRListTab from './components/JRListTab.vue'
import JobPostingTab from './components/JobPostingTab.vue'
import HeadcountPlanTab from './components/HeadcountPlanTab.vue'

const route = useRoute()
const router = useRouter()

const validTabs = new Set(['jr', 'postings', 'candidates', 'headcount'])
const resolveTab = (raw: unknown) =>
  typeof raw === 'string' && validTabs.has(raw) ? raw : 'jr'

const activeTab = ref(resolveTab(route.query.tab))

watch(
  () => route.query.tab,
  (tab) => {
    const next = resolveTab(tab)
    if (activeTab.value !== next) {
      activeTab.value = next
    }
  },
)

watch(activeTab, (tab) => {
  if (resolveTab(route.query.tab) === tab) {
    return
  }
  router.replace({
    query: {
      ...route.query,
      tab,
    },
  })
})
</script>
