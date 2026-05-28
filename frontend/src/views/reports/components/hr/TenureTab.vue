<template>
  <div class="hr-report-tab">
    <Toast />

    <div class="hr-toolbar">
      <div class="hr-toolbar-actions">
        <Button
          label="Xem báo cáo"
          icon="pi pi-refresh"
          :loading="loading"
          @click="loadReport"
        />
        <Button
          label="Xuất Excel"
          icon="pi pi-file-excel"
          severity="success"
          outlined
          :loading="exporting"
          @click="exportExcel"
        />
      </div>
    </div>

    <div class="card hr-filter-card">
      <div class="hr-filter-grid" style="grid-template-columns: repeat(2, minmax(0, 1fr))">
        <div class="hr-field">
          <label>Phòng ban</label>
          <Select
            v-model="departmentId"
            :options="departments"
            option-label="name"
            option-value="id"
            placeholder="Toàn công ty"
            show-clear
            filter
          />
        </div>
      </div>
    </div>

    <div v-if="report" class="hr-summary-strip">
      <div class="hr-summary-item">
        <span class="hr-summary-label">Tổng nhân viên</span>
        <strong>{{ report.total_active }}</strong>
      </div>
      <div class="hr-summary-item">
        <span class="hr-summary-label">Thâm niên TB</span>
        <strong>{{ report.avg_tenure_years.toFixed(1) }} năm</strong>
      </div>
      <div
        v-for="group in report.groups"
        :key="group.group_key"
        class="hr-summary-item"
      >
        <span class="hr-summary-label">{{ group.group_label }}</span>
        <strong>{{ group.headcount }} NV</strong>
        <span class="hr-tenure-pct">{{ group.percentage.toFixed(1) }}%</span>
      </div>
    </div>

    <div class="card hr-table-card">
      <DataTable
        v-model:expanded-rows="expandedRows"
        :value="report?.groups ?? []"
        :loading="loading"
        data-key="group_key"
        striped-rows
        responsive-layout="scroll"
      >
        <template #empty>
          <div class="hr-empty">Chưa có dữ liệu thâm niên.</div>
        </template>

        <Column expander style="width: 3rem" />
        <Column field="group_label" header="Nhóm thâm niên" />
        <Column field="headcount" header="Số nhân viên" style="width: 140px" />
        <Column header="Tỷ lệ" style="width: 100px">
          <template #body="{ data }">{{ data.percentage.toFixed(1) }}%</template>
        </Column>
        <Column header="Thâm niên TB" style="width: 140px">
          <template #body="{ data }">{{ data.avg_tenure_years.toFixed(1) }} năm</template>
        </Column>

        <template #expansion="{ data }">
          <div class="hr-tenure-expansion">
            <DataTable :value="data.employees" striped-rows responsive-layout="scroll">
              <Column field="full_name" header="Họ tên" />
              <Column field="department_name" header="Phòng ban">
                <template #body="{ data: emp }">{{ emp.department_name ?? '—' }}</template>
              </Column>
              <Column header="Ngày vào làm" style="width: 140px">
                <template #body="{ data: emp }">{{ formatDate(emp.start_date) }}</template>
              </Column>
              <Column field="tenure_years" header="Thâm niên (năm)" style="width: 150px" />
            </DataTable>
          </div>
        </template>
      </DataTable>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Select from 'primevue/select'
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'

import departmentService, { type DepartmentRead } from '@/services/departmentService'
import hrReportService from '@/services/hrReportService'
import type { HrTenureGroup, HrTenureReportResponse } from '@/types/hr_report.types'

const toast = useToast()

const departments = ref<DepartmentRead[]>([])
const report = ref<HrTenureReportResponse | null>(null)
const loading = ref(false)
const exporting = ref(false)
const departmentId = ref<number | null>(null)
const expandedRows = ref<HrTenureGroup[]>([])

function formatDate(value: string) {
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return new Intl.DateTimeFormat('vi-VN').format(d)
}

async function loadDepartments() {
  try {
    const res = await departmentService.getList(true)
    departments.value = res.data
  } catch {
    departments.value = []
  }
}

async function loadReport() {
  loading.value = true
  try {
    const res = await hrReportService.getTenureReport(departmentId.value)
    report.value = res.data
    expandedRows.value = []
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Không tải được báo cáo',
      detail: 'Vui lòng thử lại.',
      life: 3000,
    })
  } finally {
    loading.value = false
  }
}

async function exportExcel() {
  exporting.value = true
  try {
    await hrReportService.exportReport('tenure', { department_id: departmentId.value })
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Xuất Excel thất bại',
      detail: 'Không thể xuất báo cáo thâm niên.',
      life: 3000,
    })
  } finally {
    exporting.value = false
  }
}

onMounted(async () => {
  await loadDepartments()
  await loadReport()
})
</script>

<style>
.hr-tenure-pct {
  display: block;
  font-size: 0.8rem;
  color: var(--l-text-muted);
  margin-top: 0.1rem;
}

.hr-tenure-expansion {
  padding: 0.75rem 1rem;
  background: var(--l-surface-raised, var(--l-surface));
}
</style>
