<template>
  <div class="hr-report-tab">
    <Toast />

    <div class="hr-toolbar">
      <Button
        class="hr-mobile-filter-btn"
        icon="pi pi-sliders-h"
        label="Bộ lọc"
        severity="secondary"
        outlined
        @click="mobileFiltersOpen = true"
      />
      <div class="hr-toolbar-actions">
        <Button
          label="Xem báo cáo"
          icon="pi pi-search"
          :loading="loading"
          @click="loadPage(1)"
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

    <div v-if="!isMobile" class="hr-filter-card card">
      <div class="hr-filter-grid">
        <div class="hr-field">
          <label>Phòng ban</label>
          <Select
            v-model="filters.department_id"
            :options="departments"
            option-label="name"
            option-value="id"
            placeholder="Tất cả phòng ban"
            show-clear
            filter
          />
        </div>
        <div class="hr-field">
          <label>Trạng thái</label>
          <Select
            v-model="filters.status"
            :options="statusOptions"
            option-label="label"
            option-value="value"
            placeholder="Tất cả trạng thái"
            show-clear
          />
        </div>
        <div class="hr-field">
          <label>Giới tính</label>
          <Select
            v-model="filters.gender"
            :options="genderOptions"
            option-label="label"
            option-value="value"
            placeholder="Tất cả giới tính"
            show-clear
          />
        </div>
        <div class="hr-field">
          <label>Loại văn bản</label>
          <Select
            v-model="filters.document_kind"
            :options="documentKindOptions"
            option-label="label"
            option-value="value"
            placeholder="Tất cả loại văn bản"
            show-clear
          />
        </div>
        <div class="hr-field">
          <label>Từ ngày vào làm</label>
          <DatePicker v-model="startDateFrom" date-format="dd/mm/yy" show-icon />
        </div>
        <div class="hr-field">
          <label>Đến ngày vào làm</label>
          <DatePicker v-model="startDateTo" date-format="dd/mm/yy" show-icon />
        </div>
        <div class="hr-field">
          <label>Thâm niên từ</label>
          <InputNumber v-model="filters.tenure_min" :min="0" suffix=" năm" />
        </div>
        <div class="hr-field">
          <label>Thâm niên đến</label>
          <InputNumber v-model="filters.tenure_max" :min="0" suffix=" năm" />
        </div>
      </div>
    </div>

    <Drawer
      v-model:visible="mobileFiltersOpen"
      header="Bộ lọc báo cáo nhân sự"
      position="right"
      class="hr-mobile-drawer"
    >
      <div class="hr-filter-grid is-mobile">
        <div class="hr-field">
          <label>Phòng ban</label>
          <Select
            v-model="filters.department_id"
            :options="departments"
            option-label="name"
            option-value="id"
            placeholder="Tất cả phòng ban"
            show-clear
            filter
          />
        </div>
        <div class="hr-field">
          <label>Trạng thái</label>
          <Select
            v-model="filters.status"
            :options="statusOptions"
            option-label="label"
            option-value="value"
            placeholder="Tất cả trạng thái"
            show-clear
          />
        </div>
        <div class="hr-field">
          <label>Giới tính</label>
          <Select
            v-model="filters.gender"
            :options="genderOptions"
            option-label="label"
            option-value="value"
            placeholder="Tất cả giới tính"
            show-clear
          />
        </div>
        <div class="hr-field">
          <label>Loại văn bản</label>
          <Select
            v-model="filters.document_kind"
            :options="documentKindOptions"
            option-label="label"
            option-value="value"
            placeholder="Tất cả loại văn bản"
            show-clear
          />
        </div>
        <div class="hr-field">
          <label>Từ ngày vào làm</label>
          <DatePicker v-model="startDateFrom" date-format="dd/mm/yy" show-icon />
        </div>
        <div class="hr-field">
          <label>Đến ngày vào làm</label>
          <DatePicker v-model="startDateTo" date-format="dd/mm/yy" show-icon />
        </div>
        <div class="hr-field">
          <label>Thâm niên từ</label>
          <InputNumber v-model="filters.tenure_min" :min="0" suffix=" năm" />
        </div>
        <div class="hr-field">
          <label>Thâm niên đến</label>
          <InputNumber v-model="filters.tenure_max" :min="0" suffix=" năm" />
        </div>
      </div>
      <div class="hr-drawer-actions">
        <Button
          label="Áp dụng"
          icon="pi pi-check"
          class="w-full"
          @click="applyMobileFilters"
        />
      </div>
    </Drawer>

    <div class="hr-summary-strip">
      <div class="hr-summary-item">
        <span class="hr-summary-label">Tổng nhân sự</span>
        <strong>{{ pageState.total }}</strong>
      </div>
      <div class="hr-summary-item">
        <span class="hr-summary-label">Trang hiện tại</span>
        <strong>{{ pageState.page }}/{{ totalPages }}</strong>
      </div>
    </div>

    <div class="card hr-table-card">
      <DataTable
        :value="items"
        :loading="loading"
        lazy
        paginator
        striped-rows
        responsive-layout="scroll"
        :rows="pageState.pageSize"
        :first="(pageState.page - 1) * pageState.pageSize"
        :total-records="pageState.total"
        :rows-per-page-options="[10, 20, 50]"
        @page="onPage"
      >
        <template #empty>
          <div class="hr-empty">Không có nhân sự phù hợp bộ lọc hiện tại.</div>
        </template>

        <Column field="employee_code" header="Mã NV" style="width: 110px" />
        <Column field="full_name" header="Họ tên" style="min-width: 220px" />
        <Column header="Giới tính" style="width: 110px">
          <template #body="{ data }">
            {{ genderLabel(data.gender) }}
          </template>
        </Column>
        <Column field="department_name" header="Phòng ban" style="min-width: 180px">
          <template #body="{ data }">{{ data.department_name || 'Chưa phân công' }}</template>
        </Column>
        <Column field="job_title_name" header="Chức danh" style="min-width: 160px">
          <template #body="{ data }">{{ data.job_title_name || '—' }}</template>
        </Column>
        <Column header="Trạng thái" style="width: 130px">
          <template #body="{ data }">
            <Tag :value="statusLabel(data.status)" :severity="statusSeverity(data.status)" />
          </template>
        </Column>
        <Column header="Ngày vào làm" style="width: 130px">
          <template #body="{ data }">{{ formatDate(data.start_date) }}</template>
        </Column>
        <Column header="Loại HĐ" style="min-width: 150px">
          <template #body="{ data }">{{ data.contract_category_name || '—' }}</template>
        </Column>
        <Column header="Thâm niên" style="width: 110px">
          <template #body="{ data }">{{ data.tenure_years }} năm</template>
        </Column>
      </DataTable>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import type { DataTablePageEvent } from 'primevue/datatable'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import Drawer from 'primevue/drawer'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'

import departmentService, { type DepartmentRead } from '@/services/departmentService'
import hrReportService from '@/services/hrReportService'
import type { HrEmployeeListItem } from '@/types/hr_report.types'

const toast = useToast()

const items = ref<HrEmployeeListItem[]>([])
const departments = ref<DepartmentRead[]>([])
const loading = ref(false)
const exporting = ref(false)
const mobileFiltersOpen = ref(false)
const isMobile = ref(false)
const startDateFrom = ref<Date | null>(null)
const startDateTo = ref<Date | null>(null)

const filters = reactive({
  department_id: null as number | null,
  status: null as string | null,
  gender: null as string | null,
  document_kind: null as string | null,
  tenure_min: null as number | null,
  tenure_max: null as number | null,
})

const pageState = reactive({
  page: 1,
  pageSize: 10,
  total: 0,
})

const totalPages = computed(() =>
  Math.max(Math.ceil(pageState.total / pageState.pageSize), 1),
)

const statusOptions = [
  { label: 'Thử việc', value: 'probation' },
  { label: 'Chính thức', value: 'official' },
  { label: 'Nghỉ dài hạn', value: 'long_leave' },
  { label: 'Đã nghỉ việc', value: 'resigned' },
]

const genderOptions = [
  { label: 'Nam', value: 'male' },
  { label: 'Nữ', value: 'female' },
  { label: 'Khác', value: 'other' },
]

const documentKindOptions = [
  { label: 'Hợp đồng lao động', value: 'labor_contract' },
  { label: 'Thử việc', value: 'probation' },
  { label: 'Phụ lục', value: 'contract_appendix' },
]

function toApiDate(value: Date | null): string | null {
  if (!value) return null
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function formatDate(value: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('vi-VN').format(date)
}

function genderLabel(value: string) {
  return (
    {
      male: 'Nam',
      female: 'Nữ',
      other: 'Khác',
    }[value] ?? value
  )
}

function statusLabel(value: string) {
  return (
    {
      probation: 'Thử việc',
      official: 'Chính thức',
      long_leave: 'Nghỉ dài hạn',
      resigned: 'Đã nghỉ việc',
    }[value] ?? value
  )
}

function statusSeverity(value: string) {
  return (
    {
      probation: 'warn',
      official: 'success',
      long_leave: 'info',
      resigned: 'danger',
    }[value] ?? 'secondary'
  )
}

function syncViewport() {
  isMobile.value = window.innerWidth < 1024
}

function buildParams(page = pageState.page) {
  return {
    page,
    page_size: pageState.pageSize,
    department_id: filters.department_id,
    status: filters.status,
    gender: filters.gender,
    document_kind: filters.document_kind,
    start_date_from: toApiDate(startDateFrom.value),
    start_date_to: toApiDate(startDateTo.value),
    tenure_min: filters.tenure_min,
    tenure_max: filters.tenure_max,
  }
}

async function loadDepartments() {
  try {
    const res = await departmentService.getList(true)
    departments.value = res.data
  } catch {
    departments.value = []
  }
}

async function loadPage(page = pageState.page) {
  loading.value = true
  try {
    const res = await hrReportService.getEmployeeList(buildParams(page))
    items.value = res.data.items
    pageState.page = res.data.page
    pageState.pageSize = res.data.page_size
    pageState.total = res.data.total
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
    await hrReportService.exportReport('employee-list', buildParams(1))
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Xuất Excel thất bại',
      detail: 'Không thể xuất danh sách nhân sự.',
      life: 3000,
    })
  } finally {
    exporting.value = false
  }
}

function onPage(event: DataTablePageEvent) {
  pageState.page = Math.floor(event.first / event.rows) + 1
  pageState.pageSize = event.rows
  loadPage(pageState.page)
}

function applyMobileFilters() {
  mobileFiltersOpen.value = false
  loadPage(1)
}

onMounted(async () => {
  syncViewport()
  window.addEventListener('resize', syncViewport)
  await loadDepartments()
  await loadPage(1)
})

onUnmounted(() => {
  window.removeEventListener('resize', syncViewport)
})
</script>

<style>
.hr-report-tab {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.hr-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.hr-mobile-filter-btn {
  display: none;
}

.hr-toolbar-actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.hr-filter-card {
  padding: 1rem;
  border: 1px solid var(--l-border);
  background: var(--l-surface);
  box-shadow: var(--l-shadow);
}

.hr-filter-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1rem;
}

.hr-filter-grid.is-mobile {
  grid-template-columns: 1fr;
}

.hr-field {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.hr-field label {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--l-text-muted);
}

.hr-summary-strip {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.hr-summary-item {
  min-width: 11rem;
  padding: 0.875rem 1rem;
  border: 1px solid var(--l-border);
  border-radius: 0.75rem;
  background: var(--l-surface);
}

.hr-summary-label {
  display: block;
  margin-bottom: 0.25rem;
  font-size: 0.8rem;
  color: var(--l-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.hr-summary-item strong {
  font-size: 1.35rem;
  color: var(--l-text);
}

.hr-table-card {
  padding: 0.5rem;
  border: 1px solid var(--l-border);
  background: var(--l-surface);
  box-shadow: var(--l-shadow);
}

.hr-empty {
  padding: 1.25rem 0.5rem;
  text-align: center;
  color: var(--l-text-muted);
}

.hr-drawer-actions {
  margin-top: 1rem;
}

@media (max-width: 1023px) {
  .hr-mobile-filter-btn {
    display: inline-flex;
  }

  .hr-toolbar-actions {
    width: 100%;
  }

  .hr-toolbar-actions .p-button {
    flex: 1 1 auto;
  }
}

@media (max-width: 1279px) {
  .hr-filter-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 767px) {
  .hr-filter-grid {
    grid-template-columns: 1fr;
  }

  .hr-summary-item {
    flex: 1 1 100%;
  }
}
</style>
