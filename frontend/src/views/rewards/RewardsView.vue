<template>
  <div class="rewards-view">
    <div class="page-header insurance-header">
      <div>
        <h2 class="page-title">Khen thưởng & Kỷ luật</h2>
        <span class="page-subtitle">Quyết định khen thưởng · Kỷ luật · Shortcut tới báo cáo tổng hợp</span>
      </div>
      <Button
        v-if="permissionGate.canAccessRoute('/reports/rewards')"
        label="Xem báo cáo khen thưởng & kỷ luật"
        icon="pi pi-chart-bar"
        severity="secondary"
        outlined
        @click="router.push('/reports/rewards')"
      />
    </div>

    <Tabs v-model:value="activeTab">
      <TabList>
        <Tab v-if="canViewRewards" value="rewards">Khen thưởng</Tab>
        <Tab v-if="canViewDisciplines" value="disciplines">Kỷ luật</Tab>
      </TabList>

      <TabPanels>
        <TabPanel v-if="canViewRewards" value="rewards">
          <RewardListTab />
        </TabPanel>
        <TabPanel v-if="canViewDisciplines" value="disciplines">
          <DisciplineListTab />
        </TabPanel>
      </TabPanels>
    </Tabs>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Tabs from 'primevue/tabs'
import { usePermissionGate } from '@/composables/usePermissionGate'

import RewardListTab from './components/RewardListTab.vue'
import DisciplineListTab from './components/DisciplineListTab.vue'

const router = useRouter()
const permissionGate = usePermissionGate()
const canViewRewards = computed(() => permissionGate.canView('rewards'))
const canViewDisciplines = computed(() => permissionGate.canView('disciplines'))
const activeTab = ref(canViewRewards.value ? 'rewards' : 'disciplines')

watch(
  [canViewRewards, canViewDisciplines],
  ([nextCanViewRewards, nextCanViewDisciplines]) => {
    if (activeTab.value === 'rewards' && !nextCanViewRewards && nextCanViewDisciplines) {
      activeTab.value = 'disciplines'
      return
    }
    if (activeTab.value === 'disciplines' && !nextCanViewDisciplines && nextCanViewRewards) {
      activeTab.value = 'rewards'
      return
    }
    if (!nextCanViewRewards && !nextCanViewDisciplines) {
      activeTab.value = 'rewards'
    }
  },
  { immediate: true },
)
</script>
