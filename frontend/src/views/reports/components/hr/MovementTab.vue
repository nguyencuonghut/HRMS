<template>
  <div class="hr-report-tab">
    <Toast />

    <div class="hr-toolbar">
      <div class="hr-toolbar-actions">
        <Button
          label="Xem báo cáo"
          icon="pi pi-chart-line"
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
      <div class="hr-filter-grid hr-movement-grid">
        <div class="hr-field">
          <label>Năm báo cáo</label>
          <Select
            v-model="selectedYear"
            :options="yearOptions"
            option-label="label"
            option-value="value"
          />
        </div>
        <div class="hr-field">
          <label>Nhóm kỳ</label>
          <Select
            v-model="groupBy"
            :options="groupByOptions"
            option-label="label"
            option-value="value"
          />
        </div>
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

    <div class="hr-summary-strip">
      <div class="hr-summary-item">
        <span class="hr-summary-label">Tuyển mới</span>
        <strong>{{ report?.total_hired ?? 0 }}</strong>
      </div>
      <div class="hr-summary-item">
        <span class="hr-summary-label">Thôi việc</span>
        <strong>{{ report?.total_resigned ?? 0 }}</strong>
      </div>
      <div class="hr-summary-item">
        <span class="hr-summary-label">Chuyển bộ phận</span>
        <strong>{{ report?.total_transfers ?? 0 }}</strong>
      </div>
    </div>

    <div class="card hr-table-card">
      <DataTable
        :value="report?.rows ?? []"
        :loading="loading"
        striped-rows
        responsive-layout="scroll"
      >
        <template #empty>
          <div class="hr-empty">Chưa có dữ liệu biến động trong năm đã chọn.</div>
        </template>

        <Column field="period_label" header="Kỳ" style="width: 130px" />
        <Column header="Từ ngày" style="width: 130px">
          <template #body="{ data }">{{ formatDate(data.period_start) }}</template>
        </Column>
        <Column header="Đến ngày" style="width: 130px">
          <template #body="{ data }">{{ formatDate(data.period_end) }}</template>
        </Column>
        <Column field="hired_count" header="Tuyển mới" style="width: 110px" />
        <Column field="resigned_count" header="Thôi việc" style="width: 110px" />
        <Column field="transfer_count" header="Chuyển BP" style="width: 120px" />
        <Column header="Biến động ròng" style="width: 140px">
          <template #body="{ data }">
            <Tag
              :value="netChangeLabel(data.net_change)"
              :severity="netChangeSeverity(data.net_change)"
            />
          </template>
        </Column>
      </DataTable>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'

import departmentService, { type DepartmentRead } from '@/services/departmentService'
import hrReportService from '@/services/hrReportService'
import type {
  HrMovementGroupBy,
  HrMovementReportResponse,
} from '@/types/hr_report.types'

const toast = useToast()
const now = new Date()

const departments = ref<DepartmentRead[]>([])
const report = ref<HrMovementReportResponse | null>(null)
const loading = ref(false)
const exporting = ref(false)

const selectedYear = ref(now.getFullYear())
const groupBy = ref<HrMovementGroupBy>('month')
const departmentId = ref<number | null>(null)

const yearOptions = computed(() =>
  Array.from({ length: 7 }, (_, index) => {
    const year = now.getFullYear() - 3 + index
    return { label: `Năm ${year}`, value: year }
  }),
)

const groupByOptions = [
  { label: 'Theo tháng', value: 'month' },
  { label: 'Theo quý', value: 'quarter' },
  { label: 'Theo năm', value: 'year' },
]

function formatDate(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('vi-VN').format(date)
}

function buildParams() {
  return {
    start_date: `${selectedYear.value}-01-01`,
    end_date: `${selectedYear.value}-12-31`,
    group_by: groupBy.value,
    department_id: departmentId.value,
  }
}

function netChangeLabel(value: number) {
  if (value > 0) return `+${value}`
  return String(value)
}

function netChangeSeverity(value: number) {
  if (value > 0) return 'success'
  if (value < 0) return 'danger'
  return 'secondary'
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
    const res = await hrReportService.getMovementReport(buildParams())
    report.value = res.data
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
    await hrReportService.exportReport('movement', buildParams())
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Xuất Excel thất bại',
      detail: 'Không thể xuất báo cáo biến động.',
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
