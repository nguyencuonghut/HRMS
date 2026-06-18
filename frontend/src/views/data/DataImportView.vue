<template>
  <div>
    <div class="page-header">
      <div>
        <h2>Nhập dữ liệu hàng loạt</h2>
        <div class="subtitle">Import danh mục tổ chức, nhân viên và dữ liệu vận hành từ file Excel</div>
      </div>
    </div>

    <Tabs v-model:value="activeTab">
      <TabList>
        <Tab
          v-for="tab in visibleTabs"
          :key="tab.value"
          :value="tab.value"
        >
          {{ tab.label }}
        </Tab>
      </TabList>

      <TabPanels>
        <!-- ── Phòng ban ────────────────────────────────────────────────── -->
        <TabPanel v-if="canImportOrg" value="departments">
          <ImportPanel
            title="Import phòng ban"
            description="Nhập hoặc cập nhật cây phòng ban trước khi import nhân viên và vị trí công việc."
            :download-template="svc.downloadDepartmentTemplate"
            :upload-fn="svc.importDepartments"
          />
        </TabPanel>

        <!-- ── Chức danh ───────────────────────────────────────────────── -->
        <TabPanel v-if="canImportOrg" value="job-titles">
          <ImportPanel
            title="Import chức danh"
            description="Nhập hoặc cập nhật danh mục chức danh dùng cho vị trí công việc và cơ cấu tổ chức."
            :download-template="svc.downloadJobTitleTemplate"
            :upload-fn="svc.importJobTitles"
          />
        </TabPanel>

        <!-- ── Vị trí công việc ────────────────────────────────────────── -->
        <TabPanel v-if="canImportOrg" value="job-positions">
          <ImportPanel
            title="Import vị trí công việc"
            description="Nhập hoặc cập nhật vị trí công việc sau khi đã có phòng ban và chức danh."
            :download-template="svc.downloadJobPositionTemplate"
            :upload-fn="svc.importJobPositions"
          />
        </TabPanel>

        <TabPanel v-if="canImportEmployees" value="employees">
          <ImportPanel
            title="Import nhân viên"
            description="Nhập hồ sơ nhân viên hàng loạt từ file Excel. Có thể gán phòng ban, chức danh, vị trí công việc và hệ mã nhân viên ngay trong file."
            :download-template="svc.downloadEmployeeTemplate"
            :upload-fn="svc.importEmployees"
          />
        </TabPanel>

        <!-- ── Nghỉ phép ───────────────────────────────────────────────── -->
        <TabPanel v-if="canImportLeaves" value="leave-records">
          <ImportPanel
            title="Import nghỉ phép"
            description="Tạo hàng loạt bản ghi nghỉ phép. Số ngày được tính tự động từ ngày bắt đầu đến ngày kết thúc."
            :download-template="svc.downloadLeaveRecordTemplate"
            :upload-fn="svc.importLeaveRecords"
          />
        </TabPanel>

        <!-- ── Hợp đồng ─────────────────────────────────────────────────── -->
        <TabPanel v-if="canImportContracts" value="contracts">
          <ImportPanel
            title="Import hợp đồng lao động"
            description="Tạo hàng loạt hợp đồng từ file Excel. Mỗi dòng = 1 hợp đồng."
            :download-template="svc.downloadContractTemplate"
            :upload-fn="svc.importContracts"
          />
        </TabPanel>

        <!-- ── Bảo hiểm ────────────────────────────────────────────────── -->
        <TabPanel v-if="canImportInsurance" value="insurance">
          <ImportPanel
            title="Import hồ sơ bảo hiểm"
            description="Tạo hoặc cập nhật hồ sơ BHXH/BHYT. Nếu nhân viên đã có hồ sơ → tự động cập nhật."
            :download-template="svc.downloadInsuranceTemplate"
            :upload-fn="svc.importInsurance"
          />
        </TabPanel>
      </TabPanels>
    </Tabs>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watchEffect } from 'vue'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Tabs from 'primevue/tabs'

import dataImportService from '@/services/dataImportService'
import { usePermissionGate } from '@/composables/usePermissionGate'
import ImportPanel from './ImportPanel.vue'

const activeTab = ref('departments')
const svc = dataImportService
const permissionGate = usePermissionGate()

const canImportOrg = computed(() => permissionGate.canEdit('org'))
const canImportEmployees = computed(() => permissionGate.canEdit('employees'))
const canImportLeaves = computed(() => permissionGate.canEdit('leaves'))
const canImportContracts = computed(() => permissionGate.canEdit('contracts'))
const canImportInsurance = computed(() => permissionGate.canEdit('insurance'))

const visibleTabs = computed(() => [
  canImportOrg.value ? { value: 'departments', label: 'Phòng ban' } : null,
  canImportOrg.value ? { value: 'job-titles', label: 'Chức danh' } : null,
  canImportOrg.value ? { value: 'job-positions', label: 'Vị trí công việc' } : null,
  canImportEmployees.value ? { value: 'employees', label: 'Nhân viên' } : null,
  canImportLeaves.value ? { value: 'leave-records', label: 'Nghỉ phép' } : null,
  canImportContracts.value ? { value: 'contracts', label: 'Hợp đồng' } : null,
  canImportInsurance.value ? { value: 'insurance', label: 'Bảo hiểm' } : null,
].filter((tab): tab is { value: string; label: string } => tab !== null))

watchEffect(() => {
  if (!visibleTabs.value.some((tab) => tab.value === activeTab.value)) {
    activeTab.value = visibleTabs.value[0]?.value ?? ''
  }
})
</script>

<style>
</style>
