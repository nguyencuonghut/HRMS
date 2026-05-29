<template>
  <div>
    <div class="page-header">
      <div>
        <h2>Nhập dữ liệu hàng loạt</h2>
        <div class="subtitle">Import hợp đồng, nghỉ phép, bảo hiểm từ file Excel</div>
      </div>
    </div>

    <Tabs v-model:value="activeTab">
      <TabList>
        <Tab value="contracts">Hợp đồng</Tab>
        <Tab value="leave-records">Nghỉ phép</Tab>
        <Tab value="insurance">Bảo hiểm</Tab>
        <Tab value="employees">Nhân viên</Tab>
      </TabList>

      <TabPanels>
        <!-- ── Hợp đồng ─────────────────────────────────────────────────── -->
        <TabPanel value="contracts">
          <ImportPanel
            title="Import hợp đồng lao động"
            description="Tạo hàng loạt hợp đồng từ file Excel. Mỗi dòng = 1 hợp đồng."
            :download-template="svc.downloadContractTemplate"
            :upload-fn="svc.importContracts"
          />
        </TabPanel>

        <!-- ── Nghỉ phép ───────────────────────────────────────────────── -->
        <TabPanel value="leave-records">
          <ImportPanel
            title="Import nghỉ phép"
            description="Tạo hàng loạt bản ghi nghỉ phép. Số ngày được tính tự động từ ngày bắt đầu đến ngày kết thúc."
            :download-template="svc.downloadLeaveRecordTemplate"
            :upload-fn="svc.importLeaveRecords"
          />
        </TabPanel>

        <!-- ── Bảo hiểm ────────────────────────────────────────────────── -->
        <TabPanel value="insurance">
          <ImportPanel
            title="Import hồ sơ bảo hiểm"
            description="Tạo hoặc cập nhật hồ sơ BHXH/BHYT. Nếu nhân viên đã có hồ sơ → tự động cập nhật."
            :download-template="svc.downloadInsuranceTemplate"
            :upload-fn="svc.importInsurance"
          />
        </TabPanel>

        <!-- ── Nhân viên (link ra) ─────────────────────────────────────── -->
        <TabPanel value="employees">
          <div class="import-redirect-panel">
            <i class="pi pi-users import-redirect-icon" />
            <p>Import nhân viên được thực hiện tại trang Danh sách nhân viên.</p>
            <RouterLink to="/employees">
              <Button label="Đến trang Nhân viên" icon="pi pi-arrow-right" icon-pos="right" />
            </RouterLink>
          </div>
        </TabPanel>
      </TabPanels>
    </Tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import Button from 'primevue/button'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Tabs from 'primevue/tabs'

import dataImportService from '@/services/dataImportService'
import ImportPanel from './ImportPanel.vue'

const activeTab = ref('contracts')
const svc = dataImportService
</script>

<style>
.import-redirect-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 3rem 1rem;
  text-align: center;
  color: var(--l-text-muted);
}

.import-redirect-icon {
  font-size: 3rem;
  color: var(--l-text-muted);
}
</style>
