<template>
  <div>
    <!-- Page header -->
    <div class="page-header">
      <div>
        <h2>Báo cáo nghỉ phép</h2>
        <span class="subtitle">Tổng hợp và xuất báo cáo theo nhân viên, phòng ban, tồn phép</span>
      </div>
    </div>

    <!-- Tabs -->
    <Tabs v-model:value="activeTab" class="report-tabs">
      <TabList>
        <Tab value="A">Chi tiết nhân viên</Tab>
        <Tab value="B">Theo phòng ban</Tab>
        <Tab value="C">Tồn phép cuối năm</Tab>
      </TabList>
    </Tabs>

    <!-- Toolbar -->
    <div class="toolbar" style="margin-top: 0.75rem">
      <!-- Chung: năm -->
      <Select
        v-model="filters.year"
        :options="yearOptions"
        option-label="label"
        option-value="value"
        placeholder="Năm"
        filter
        class="toolbar-filter-sm"
      />

      <!-- Phòng ban (A, B, C) -->
      <Select
        v-model="filters.department_id"
        :options="departments"
        option-label="name"
        option-value="id"
        placeholder="Phòng ban"
        show-clear
        filter
        class="toolbar-filter"
      />

      <!-- Loại phép (A, B) -->
      <Select
        v-if="activeTab !== 'C'"
        v-model="filters.leave_type_id"
        :options="leaveTypes"
        option-label="name"
        option-value="id"
        placeholder="Loại phép"
        show-clear
        filter
        class="toolbar-filter"
      />

      <!-- Keyword (A only) -->
      <IconField v-if="activeTab === 'A'" class="toolbar-search">
        <InputIcon class="pi pi-search" />
        <InputText
          v-model="filters.keyword"
          placeholder="Tìm nhân viên..."
          class="w-full"
          @keyup.enter="applyFilter"
        />
      </IconField>

      <!-- Tháng (B only) -->
      <template v-if="activeTab === 'B'">
        <Select
          v-model="filters.month_from"
          :options="monthOptions"
          option-label="label"
          option-value="value"
          placeholder="Tháng từ"
          show-clear
          filter
          class="toolbar-filter-sm"
        />
        <Select
          v-model="filters.month_to"
          :options="monthOptions"
          option-label="label"
          option-value="value"
          placeholder="Tháng đến"
          show-clear
          filter
          class="toolbar-filter-sm"
        />
      </template>

      <Button label="Lọc" icon="pi pi-filter" @click="applyFilter" />
      <Button
        icon="pi pi-refresh"
        severity="secondary"
        text rounded
        :loading="loading"
        v-tooltip.top="'Làm mới'"
        @click="reset"
      />
      <Button
        v-can:export="'leaves'"
        icon="pi pi-file-excel"
        label="Xuất Excel"
        severity="success"
        outlined
        :loading="exporting"
        @click="exportExcel"
      />
    </div>

    <!-- Tab A — Chi tiết nhân viên -->
    <div v-show="activeTab === 'A'" class="card">
      <DataTable
        :value="summaryItems"
        :loading="loading"
        responsive-layout="scroll"
        :rows="pageSize"
        :total-records="total"
        :lazy="true"
        paginator
        paginator-template="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
        current-page-report-template="Hiển thị từ {first} đến {last} trên tổng số {totalRecords} dòng"
        :rows-per-page-options="[50, 100, 200]"
        @page="onPage"
      >
        <Column header="Nhân viên" style="min-width: 180px">
          <template #body="{ data }">
            <div style="font-weight:500">{{ data.employee_name }}</div>
            <div class="muted-text" style="font-size:0.78rem">{{ data.employee_code }}</div>
          </template>
        </Column>
        <Column field="department_name" header="Phòng ban" style="min-width:130px">
          <template #body="{ data }">
            <span v-if="data.department_name">{{ data.department_name }}</span>
            <span v-else class="muted-text">—</span>
          </template>
        </Column>
        <Column field="leave_type_name" header="Loại phép" style="min-width:130px" />
        <Column header="Cấp phép" style="width:90px">
          <template #body="{ data }">
            <span class="right-text">{{ data.allocated_days }}</span>
          </template>
        </Column>
        <Column header="Chuyển dư" style="width:95px">
          <template #body="{ data }">
            <span v-if="data.carryover_days > 0" class="right-text">{{ data.carryover_days }}</span>
            <span v-else class="muted-text right-text">—</span>
          </template>
        </Column>
        <Column header="Đã dùng" style="width:85px">
          <template #body="{ data }">
            <span class="right-text">{{ data.used_days }}</span>
          </template>
        </Column>
        <Column header="Còn lại" style="width:90px">
          <template #body="{ data }">
            <span :class="['days-badge', remainingClass(data.remaining_days)]">
              {{ data.remaining_days }}
            </span>
          </template>
        </Column>
        <Column header="Số lần" style="width:75px">
          <template #body="{ data }">
            <span class="right-text muted-text">{{ data.record_count }}</span>
          </template>
        </Column>
        <template #empty>
          <div class="empty-state"><i class="pi pi-chart-bar" /><span>Không có dữ liệu</span></div>
        </template>
      </DataTable>
    </div>

    <!-- Tab B — Theo phòng ban -->
    <div v-show="activeTab === 'B'" class="card">
      <DataTable
        :value="deptItems"
        :loading="loading"
        responsive-layout="scroll"
      >
        <Column header="Phòng ban" style="min-width:150px">
          <template #body="{ data }">
            <span v-if="data.department_name">{{ data.department_name }}</span>
            <span v-else class="muted-text">—</span>
          </template>
        </Column>
        <Column field="leave_type_name" header="Loại phép" style="min-width:130px" />
        <Column header="Số NV" style="width:80px">
          <template #body="{ data }">
            <span class="right-text">{{ data.employee_count }}</span>
          </template>
        </Column>
        <Column header="Số lần" style="width:80px">
          <template #body="{ data }">
            <span class="right-text">{{ data.total_records }}</span>
          </template>
        </Column>
        <Column header="Tổng ngày" style="width:100px">
          <template #body="{ data }">
            <span class="right-text" style="font-weight:600">{{ data.total_days_taken }}</span>
          </template>
        </Column>
        <Column header="TB/NV" style="width:85px">
          <template #body="{ data }">
            <span class="right-text muted-text">{{ data.avg_days_per_employee }}</span>
          </template>
        </Column>
        <template #empty>
          <div class="empty-state"><i class="pi pi-chart-bar" /><span>Không có dữ liệu</span></div>
        </template>
      </DataTable>
    </div>

    <!-- Tab C — Tồn phép cuối năm -->
    <div v-show="activeTab === 'C'" class="card">
      <DataTable
        :value="yearEndItems"
        :loading="loading"
        responsive-layout="scroll"
        :rows="pageSize"
        :total-records="total"
        :lazy="true"
        paginator
        paginator-template="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
        current-page-report-template="Hiển thị từ {first} đến {last} trên tổng số {totalRecords} dòng"
        :rows-per-page-options="[50, 100, 200]"
        @page="onPage"
      >
        <Column header="Nhân viên" style="min-width:180px">
          <template #body="{ data }">
            <div style="font-weight:500">{{ data.employee_name }}</div>
            <div class="muted-text" style="font-size:0.78rem">{{ data.employee_code }}</div>
          </template>
        </Column>
        <Column header="Phòng ban" style="min-width:130px">
          <template #body="{ data }">
            <span v-if="data.department_name">{{ data.department_name }}</span>
            <span v-else class="muted-text">—</span>
          </template>
        </Column>
        <Column field="leave_type_name" header="Loại phép" style="min-width:130px" />
        <Column header="Cấp phép" style="width:90px">
          <template #body="{ data }">
            <span class="right-text">{{ data.allocated_days }}</span>
          </template>
        </Column>
        <Column header="Chuyển dư" style="width:95px">
          <template #body="{ data }">
            <span v-if="data.carryover_days > 0" class="right-text">{{ data.carryover_days }}</span>
            <span v-else class="muted-text right-text">—</span>
          </template>
        </Column>
        <Column header="Đã dùng" style="width:85px">
          <template #body="{ data }">
            <span class="right-text">{{ data.used_days }}</span>
          </template>
        </Column>
        <Column header="Còn lại" style="width:90px">
          <template #body="{ data }">
            <span :class="['days-badge', remainingClass(data.remaining_days)]">
              {{ data.remaining_days }}
            </span>
          </template>
        </Column>
        <Column header="Sẽ chuyển" style="width:95px">
          <template #body="{ data }">
            <span :class="['days-badge', data.will_carry > 0 ? 'ok' : 'expired']">
              {{ data.will_carry }}
            </span>
          </template>
        </Column>
        <template #empty>
          <div class="empty-state"><i class="pi pi-chart-bar" /><span>Không có dữ liệu</span></div>
        </template>
      </DataTable>
    </div>

    <Toast />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import Tabs from 'primevue/tabs'
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'

import leaveReportService, {
  type EmployeeSummaryRow,
  type DepartmentSummaryRow,
  type YearEndRow,
} from '@/services/leaveReportService'
import otherBusinessCatalogService, { type LeaveTypeRead } from '@/services/otherBusinessCatalogService'
import departmentService, { type DepartmentRead } from '@/services/departmentService'

const toast = useToast()

// ── State ─────────────────────────────────────────────────────────────────────

const activeTab = ref<'A' | 'B' | 'C'>('A')
const loading   = ref(false)
const exporting = ref(false)
const page      = ref(1)
const pageSize  = ref(50)
const total     = ref(0)

const summaryItems  = ref<EmployeeSummaryRow[]>([])
const deptItems     = ref<DepartmentSummaryRow[]>([])
const yearEndItems  = ref<YearEndRow[]>([])

const leaveTypes  = ref<LeaveTypeRead[]>([])
const departments = ref<DepartmentRead[]>([])

const currentYear = new Date().getFullYear()
const yearOptions = Array.from({ length: 10 }, (_, i) => {
  const y = currentYear - 2 + i
  return { label: String(y), value: y }
})
const monthOptions = Array.from({ length: 12 }, (_, i) => ({
  label: `Tháng ${i + 1}`,
  value: i + 1,
}))

const filters = ref({
  year:          currentYear,
  department_id: null as number | null,
  leave_type_id: null as number | null,
  keyword:       '',
  month_from:    null as number | null,
  month_to:      null as number | null,
})

// ── Load ──────────────────────────────────────────────────────────────────────

async function load() {
  loading.value = true
  try {
    if (activeTab.value === 'A') {
      const params: Record<string, unknown> = { year: filters.value.year, page: page.value, page_size: pageSize.value }
      if (filters.value.department_id) params.department_id = filters.value.department_id
      if (filters.value.leave_type_id)  params.leave_type_id  = filters.value.leave_type_id
      if (filters.value.keyword)        params.keyword        = filters.value.keyword
      const res = await leaveReportService.employeeSummary(params)
      summaryItems.value = res.data.items
      total.value = res.data.total

    } else if (activeTab.value === 'B') {
      const params: Record<string, unknown> = { year: filters.value.year }
      if (filters.value.department_id) params.department_id = filters.value.department_id
      if (filters.value.leave_type_id)  params.leave_type_id  = filters.value.leave_type_id
      if (filters.value.month_from)     params.month_from     = filters.value.month_from
      if (filters.value.month_to)       params.month_to       = filters.value.month_to
      const res = await leaveReportService.departmentSummary(params)
      deptItems.value = res.data.items
      total.value = res.data.items.length

    } else {
      const params: Record<string, unknown> = { year: filters.value.year, page: page.value, page_size: pageSize.value }
      if (filters.value.department_id) params.department_id = filters.value.department_id
      const res = await leaveReportService.yearEnd(params)
      yearEndItems.value = res.data.items
      total.value = res.data.total
    }
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    toast.add({
      severity: 'error',
      summary:  'Lỗi tải báo cáo',
      detail:   err?.response?.data?.detail ?? 'Có lỗi xảy ra',
      life: 4000,
    })
  } finally {
    loading.value = false
  }
}

async function loadMeta() {
  try {
    const [ltRes, deptRes] = await Promise.all([
      otherBusinessCatalogService.lookupLeaveTypes({ limit: 100 }),
      departmentService.getList(true),
    ])
    leaveTypes.value  = ltRes.data
    departments.value = deptRes.data
  } catch { /* non-blocking */ }
}

function applyFilter() {
  page.value = 1
  load()
}

function reset() {
  filters.value = {
    year:          currentYear,
    department_id: null,
    leave_type_id: null,
    keyword:       '',
    month_from:    null,
    month_to:      null,
  }
  page.value = 1
  load()
}

function onPage(e: { page: number; rows: number }) {
  page.value     = e.page + 1
  pageSize.value = e.rows
  load()
}

watch(activeTab, () => {
  page.value = 1
  load()
})

// ── Helpers ───────────────────────────────────────────────────────────────────

function remainingClass(remaining: number): string {
  if (remaining <= 0) return 'expired'
  if (remaining <= 2) return 'warning'
  return 'ok'
}

// ── Export Excel ──────────────────────────────────────────────────────────────

async function exportExcel() {
  exporting.value = true
  try {
    const params: Record<string, unknown> = { year: filters.value.year }
    if (filters.value.department_id) params.department_id = filters.value.department_id
    if (filters.value.leave_type_id)  params.leave_type_id  = filters.value.leave_type_id
    if (filters.value.keyword)        params.keyword        = filters.value.keyword
    if (filters.value.month_from)     params.month_from     = filters.value.month_from
    if (filters.value.month_to)       params.month_to       = filters.value.month_to

    const url = leaveReportService.exportUrl(activeTab.value, params)
    const a = document.createElement('a')
    a.href = url
    a.click()
  } finally {
    exporting.value = false
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────

onMounted(() => {
  loadMeta()
  load()
})
</script>
