<template>
  <div class="contract-report-view">
    <Toast />

    <div class="page-header">
      <div>
        <h2>Báo cáo hợp đồng</h2>
        <div class="subtitle">
          Theo dõi hợp đồng sắp hết hạn, cơ cấu loại hợp đồng, dự báo gia hạn và lịch sử hợp đồng nhân sự.
        </div>
      </div>
    </div>

    <div class="contract-toolbar">
      <Button
        class="contract-mobile-filter-btn"
        icon="pi pi-sliders-h"
        label="Bộ lọc"
        severity="secondary"
        outlined
        @click="mobileFiltersOpen = true"
      />
      <div class="contract-toolbar-actions">
        <Button
          label="Xem báo cáo"
          icon="pi pi-search"
          :loading="loading"
          @click="refreshAll"
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

    <div v-if="!isMobile" class="card contract-filter-card">
      <div class="contract-filter-grid">
        <div class="contract-field">
          <label>Phòng ban</label>
          <Select
            v-model="filters.department_id"
            :options="departments"
            option-label="name"
            option-value="id"
            placeholder="Toàn công ty"
            show-clear
            filter
          />
        </div>
        <div class="contract-field">
          <label>Cửa sổ sắp hết hạn</label>
          <Select
            v-model="filters.days_ahead"
            :options="daysAheadOptions"
            option-label="label"
            option-value="value"
          />
        </div>
        <div class="contract-field">
          <label>Năm ký hợp đồng</label>
          <Select
            v-model="filters.year"
            :options="yearOptions"
            option-label="label"
            option-value="value"
            placeholder="Tất cả năm"
            show-clear
          />
        </div>
        <div class="contract-field">
          <label>Số tháng dự báo</label>
          <Select
            v-model="filters.months_ahead"
            :options="monthsAheadOptions"
            option-label="label"
            option-value="value"
          />
        </div>
        <div class="contract-field contract-field-span-2">
          <label>Tìm kiếm hợp đồng sắp hết hạn</label>
          <InputText
            v-model.trim="filters.keyword"
            placeholder="Nhập mã nhân viên, tên nhân viên hoặc số hợp đồng"
            @keyup.enter="loadExpiringPage(1)"
          />
        </div>
      </div>
    </div>

    <Drawer
      v-model:visible="mobileFiltersOpen"
      header="Bộ lọc báo cáo hợp đồng"
      position="right"
      class="contract-mobile-drawer"
    >
      <div class="contract-filter-grid is-mobile">
        <div class="contract-field">
          <label>Phòng ban</label>
          <Select
            v-model="filters.department_id"
            :options="departments"
            option-label="name"
            option-value="id"
            placeholder="Toàn công ty"
            show-clear
            filter
          />
        </div>
        <div class="contract-field">
          <label>Cửa sổ sắp hết hạn</label>
          <Select
            v-model="filters.days_ahead"
            :options="daysAheadOptions"
            option-label="label"
            option-value="value"
          />
        </div>
        <div class="contract-field">
          <label>Năm ký hợp đồng</label>
          <Select
            v-model="filters.year"
            :options="yearOptions"
            option-label="label"
            option-value="value"
            placeholder="Tất cả năm"
            show-clear
          />
        </div>
        <div class="contract-field">
          <label>Số tháng dự báo</label>
          <Select
            v-model="filters.months_ahead"
            :options="monthsAheadOptions"
            option-label="label"
            option-value="value"
          />
        </div>
        <div class="contract-field">
          <label>Tìm kiếm hợp đồng sắp hết hạn</label>
          <InputText
            v-model.trim="filters.keyword"
            placeholder="Nhập mã nhân viên, tên nhân viên hoặc số hợp đồng"
          />
        </div>
      </div>
      <div class="contract-drawer-actions">
        <Button
          label="Áp dụng"
          icon="pi pi-check"
          class="w-full"
          @click="applyMobileFilters"
        />
      </div>
    </Drawer>

    <div v-if="errorMsg" class="contract-error-banner card">
      <i class="pi pi-exclamation-triangle" />
      <span>{{ errorMsg }}</span>
    </div>

    <div class="contract-kpi-grid">
      <div class="contract-kpi-card border-blue">
        <div class="contract-kpi-header">
          <span class="contract-kpi-title">Hợp đồng active</span>
          <i class="pi pi-file-edit contract-kpi-icon blue" />
        </div>
        <div v-if="loading" class="contract-kpi-skeleton">
          <Skeleton width="5rem" height="2rem" />
        </div>
        <template v-else>
          <div class="contract-kpi-value">{{ formatInteger(summary?.total_active) }}</div>
          <div class="contract-kpi-sub">Tính đến {{ formatDate(summary?.as_of_date) }}</div>
        </template>
      </div>

      <div class="contract-kpi-card border-red">
        <div class="contract-kpi-header">
          <span class="contract-kpi-title">Hết hạn trong 30 ngày</span>
          <i class="pi pi-bell contract-kpi-icon red" />
        </div>
        <div v-if="loading" class="contract-kpi-skeleton">
          <Skeleton width="5rem" height="2rem" />
        </div>
        <template v-else>
          <div class="contract-kpi-value">{{ formatInteger(summary?.expiring_0_30) }}</div>
          <div class="contract-kpi-sub">Cần ưu tiên rà soát và gia hạn</div>
        </template>
      </div>

      <div class="contract-kpi-card border-orange">
        <div class="contract-kpi-header">
          <span class="contract-kpi-title">31 - 60 ngày</span>
          <i class="pi pi-calendar-clock contract-kpi-icon orange" />
        </div>
        <div v-if="loading" class="contract-kpi-skeleton">
          <Skeleton width="5rem" height="2rem" />
        </div>
        <template v-else>
          <div class="contract-kpi-value">{{ formatInteger(summary?.expiring_31_60) }}</div>
          <div class="contract-kpi-sub">Nhóm trung hạn trong kỳ theo dõi</div>
        </template>
      </div>

      <div class="contract-kpi-card border-gold">
        <div class="contract-kpi-header">
          <span class="contract-kpi-title">61 - 90 ngày</span>
          <i class="pi pi-clock contract-kpi-icon gold" />
        </div>
        <div v-if="loading" class="contract-kpi-skeleton">
          <Skeleton width="5rem" height="2rem" />
        </div>
        <template v-else>
          <div class="contract-kpi-value">{{ formatInteger(summary?.expiring_61_90) }}</div>
          <div class="contract-kpi-sub">Nguồn pipeline chuẩn bị cho kỳ tiếp theo</div>
        </template>
      </div>

      <div class="contract-kpi-card border-green">
        <div class="contract-kpi-header">
          <span class="contract-kpi-title">Tỷ lệ gia hạn</span>
          <i class="pi pi-chart-line contract-kpi-icon green" />
        </div>
        <div v-if="loading" class="contract-kpi-skeleton">
          <Skeleton width="5rem" height="2rem" />
        </div>
        <template v-else>
          <div class="contract-kpi-value">{{ formatPercent(summary?.renewal_rate) }}</div>
          <div class="contract-kpi-sub">
            {{ formatInteger(summary?.already_expired) }} hợp đồng đã quá hạn cần xử lý
          </div>
        </template>
      </div>
    </div>

    <div class="analytics-card contract-expiring-card">
      <div class="contract-section-header">
        <div>
          <h3 class="section-title">Hợp đồng sắp hết hạn</h3>
          <span class="contract-section-subtitle">
            Theo dõi trong {{ expiringPage?.days_ahead || filters.days_ahead }} ngày tới.
          </span>
        </div>
        <Tag :value="`${expiringPage?.total || 0} hợp đồng`" severity="secondary" />
      </div>

      <DataTable
        :value="expiringPage?.items || []"
        :loading="loadingExpiring"
        lazy
        paginator
        striped-rows
        responsive-layout="scroll"
        :rows="pageState.pageSize"
        :first="(pageState.page - 1) * pageState.pageSize"
        :total-records="expiringPage?.total || 0"
        :rows-per-page-options="[5, 10, 20, 50]"
        @page="onExpiringPage"
      >
        <template #empty>
          <div class="contract-empty">Không có hợp đồng phù hợp bộ lọc hiện tại.</div>
        </template>

        <Column field="contract_number" header="Số hợp đồng" style="min-width: 150px" />
        <Column header="Nhân sự" style="min-width: 210px">
          <template #body="{ data }">
            <div class="contract-employee-cell">
              <strong>{{ data.employee_name }}</strong>
              <span>{{ data.employee_code }}</span>
            </div>
          </template>
        </Column>
        <Column field="department_name" header="Phòng ban" style="min-width: 170px">
          <template #body="{ data }">{{ data.department_name || 'Chưa phân công' }}</template>
        </Column>
        <Column field="category_name" header="Loại hợp đồng" style="min-width: 160px" />
        <Column header="Hiệu lực" style="min-width: 180px">
          <template #body="{ data }">
            {{ formatDate(data.effective_from) }} - {{ formatDate(data.effective_to) }}
          </template>
        </Column>
        <Column header="Còn lại" style="width: 130px">
          <template #body="{ data }">
            <div class="contract-days-cell">
              <strong>{{ data.days_remaining }}</strong>
              <span>ngày</span>
            </div>
          </template>
        </Column>
        <Column header="Mức độ" style="width: 150px">
          <template #body="{ data }">
            <Tag :value="urgencyLabel(data.urgency)" :severity="urgencySeverity(data.urgency)" rounded />
          </template>
        </Column>
      </DataTable>
    </div>

    <div class="contract-analytics-grid">
      <div class="analytics-card">
        <div class="contract-section-header">
          <div>
            <h3 class="section-title">Cơ cấu loại hợp đồng</h3>
            <span class="contract-section-subtitle">Tỷ trọng theo loại hợp đồng lao động gốc.</span>
          </div>
        </div>

        <div v-if="loading" class="contract-chart-loading">
          <Skeleton width="12rem" height="12rem" shape="circle" />
        </div>
        <div v-else-if="!donutSlices.length" class="contract-empty">
          Chưa có dữ liệu cơ cấu loại hợp đồng.
        </div>
        <div v-else class="contract-donut-panel">
          <div class="contract-donut-wrap">
            <div class="contract-donut-chart" :style="{ background: donutGradient }">
              <div class="contract-donut-inner">
                <strong>{{ formatInteger(byType?.total_contracts) }}</strong>
                <span>hợp đồng</span>
              </div>
            </div>
          </div>
          <div class="contract-donut-legend">
            <div
              v-for="slice in donutSlices"
              :key="slice.category_id"
              class="contract-donut-item"
            >
              <span class="contract-donut-swatch" :style="{ backgroundColor: slice.color }"></span>
              <div class="contract-donut-copy">
                <strong>{{ slice.category_name }}</strong>
                <span>{{ formatPercent(slice.percentage, 2) }} • {{ formatInteger(slice.total) }} hợp đồng</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="analytics-card">
        <div class="contract-section-header">
          <div>
            <h3 class="section-title">Dự báo hết hạn theo tháng</h3>
            <span class="contract-section-subtitle">
              {{ forecast?.total_expiring || 0 }} hợp đồng trong {{ filters.months_ahead }} tháng tới.
            </span>
          </div>
        </div>

        <div v-if="loading" class="contract-chart-loading">
          <Skeleton width="100%" height="14rem" />
        </div>
        <div v-else-if="!forecast?.months.length" class="contract-empty">
          Chưa có dữ liệu dự báo hết hạn.
        </div>
        <div v-else class="contract-forecast-list">
          <div
            v-for="month in forecast.months"
            :key="month.year_month"
            class="contract-forecast-row"
          >
            <div class="contract-forecast-label">{{ formatYearMonth(month.year_month) }}</div>
            <div class="contract-forecast-track">
              <div
                class="contract-forecast-fill"
                :style="{ width: `${forecastWidth(month.expiring_count)}%` }"
              ></div>
            </div>
            <div class="contract-forecast-value">{{ month.expiring_count }}</div>
          </div>
        </div>
      </div>
    </div>

    <div class="analytics-card contract-history-card">
      <div class="contract-section-header">
        <div>
          <h3 class="section-title">Lịch sử hợp đồng theo nhân viên</h3>
          <span class="contract-section-subtitle">Tra cứu toàn bộ hợp đồng và phụ lục của một nhân viên.</span>
        </div>
      </div>

      <div class="contract-history-toolbar">
        <div class="contract-history-search">
          <label>Nhân viên</label>
          <AutoComplete
            v-model="selectedEmployee"
            :suggestions="employeeSuggestions"
            :option-label="employeeOptionLabel"
            dropdown
            force-selection
            :loading="employeeSearchLoading"
            placeholder="Nhập mã hoặc tên nhân viên"
            @complete="searchEmployees"
            @option-select="onEmployeeSelect"
            @clear="clearHistory"
          >
            <template #option="{ option }">
              <div class="contract-employee-option">
                <strong>{{ option.display_code }}</strong>
                <span>{{ option.full_name }}</span>
              </div>
            </template>
          </AutoComplete>
        </div>
        <div v-if="history" class="contract-history-summary">
          <strong>{{ history.employee_name }}</strong>
          <span>{{ history.employee_code }} • {{ history.total }} hồ sơ</span>
        </div>
      </div>

      <DataTable
        :value="history?.items || []"
        :loading="historyLoading"
        responsive-layout="scroll"
        striped-rows
      >
        <template #empty>
          <div class="contract-empty">
            {{ selectedEmployee ? 'Nhân viên này chưa có lịch sử hợp đồng.' : 'Chọn nhân viên để xem lịch sử hợp đồng.' }}
          </div>
        </template>

        <Column field="contract_number" header="Số hợp đồng" style="min-width: 160px" />
        <Column field="category_name" header="Loại" style="min-width: 160px" />
        <Column header="Văn bản" style="width: 130px">
          <template #body="{ data }">
            <Tag
              :value="data.is_appendix ? 'Phụ lục' : 'Hợp đồng'"
              :severity="data.is_appendix ? 'contrast' : 'info'"
              rounded
            />
          </template>
        </Column>
        <Column header="Hiệu lực" style="min-width: 190px">
          <template #body="{ data }">
            {{ formatDate(data.effective_from) }} - {{ data.effective_to ? formatDate(data.effective_to) : 'Không thời hạn' }}
          </template>
        </Column>
        <Column header="Ngày ký" style="width: 130px">
          <template #body="{ data }">{{ formatDate(data.signed_date) }}</template>
        </Column>
        <Column header="Trạng thái" style="width: 120px">
          <template #body="{ data }">
            <Tag :value="statusLabel(data.status)" :severity="statusSeverity(data.status)" rounded />
          </template>
        </Column>
      </DataTable>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import AutoComplete from 'primevue/autocomplete'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Skeleton from 'primevue/skeleton'
import Tag from 'primevue/tag'
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'

import contractReportService, {
  type ContractByTypeOut,
  type ContractExpiringPage,
  type ContractForecastOut,
  type ContractHistoryOut,
  type ContractSummaryOut,
  type UrgencyTier,
} from '@/services/contractReportService'
import departmentService, { type DepartmentRead } from '@/services/departmentService'
import employeeService, { type EmployeeLookupItem } from '@/services/employeeService'

interface OptionItem<T> {
  label: string
  value: T
}

interface ContractFilters {
  department_id: number | null
  days_ahead: number
  year: number | null
  months_ahead: number
  keyword: string
}

const toast = useToast()

const departments = ref<DepartmentRead[]>([])
const summary = ref<ContractSummaryOut | null>(null)
const expiringPage = ref<ContractExpiringPage | null>(null)
const byType = ref<ContractByTypeOut | null>(null)
const forecast = ref<ContractForecastOut | null>(null)
const history = ref<ContractHistoryOut | null>(null)

const loading = ref(false)
const loadingExpiring = ref(false)
const exporting = ref(false)
const historyLoading = ref(false)
const errorMsg = ref('')

const employeeSuggestions = ref<EmployeeLookupItem[]>([])
const employeeSearchLoading = ref(false)
const selectedEmployee = ref<EmployeeLookupItem | null>(null)

const mobileFiltersOpen = ref(false)
const isMobile = ref(false)

const filters = ref<ContractFilters>({
  department_id: null,
  days_ahead: 90,
  year: new Date().getFullYear(),
  months_ahead: 12,
  keyword: '',
})

const pageState = ref({
  page: 1,
  pageSize: 10,
})

const daysAheadOptions: OptionItem<number>[] = [
  { label: '30 ngày', value: 30 },
  { label: '60 ngày', value: 60 },
  { label: '90 ngày', value: 90 },
  { label: '180 ngày', value: 180 },
]

const monthsAheadOptions: OptionItem<number>[] = [
  { label: '6 tháng', value: 6 },
  { label: '12 tháng', value: 12 },
  { label: '18 tháng', value: 18 },
  { label: '24 tháng', value: 24 },
]

const yearOptions = computed<OptionItem<number>[]>(() => {
  const currentYear = new Date().getFullYear()
  return Array.from({ length: 6 }, (_, index) => currentYear - index).map((year) => ({
    label: `Năm ${year}`,
    value: year,
  }))
})

const donutPalette = [
  '#1d4ed8',
  '#0f766e',
  '#c2410c',
  '#7c3aed',
  '#be123c',
  '#0891b2',
]

const donutSlices = computed(() =>
  (byType.value?.items || [])
    .filter((item) => item.total > 0)
    .map((item, index) => ({
      ...item,
      color: donutPalette[index % donutPalette.length],
    })),
)

const donutGradient = computed(() => {
  if (!donutSlices.value.length) {
    return 'conic-gradient(var(--p-surface-300) 0 100%)'
  }

  let cursor = 0
  const segments = donutSlices.value.map((slice) => {
    const start = cursor
    cursor = Math.min(100, cursor + slice.percentage)
    return `${slice.color} ${start}% ${cursor}%`
  })

  if (cursor < 100) {
    segments.push(`var(--p-surface-300) ${cursor}% 100%`)
  }

  return `conic-gradient(${segments.join(', ')})`
})

const maxForecastCount = computed(() =>
  Math.max(...(forecast.value?.months.map((item) => item.expiring_count) || [0])),
)

function syncViewport() {
  isMobile.value = window.innerWidth < 1024
}

function formatInteger(value?: number | null) {
  return new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 }).format(value || 0)
}

function formatPercent(value?: number | null, fractionDigits = 1) {
  const safe = Number(value || 0)
  return `${new Intl.NumberFormat('vi-VN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: fractionDigits,
  }).format(safe)}%`
}

function formatDate(value?: string | null) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('vi-VN').format(new Date(value))
}

function formatYearMonth(yearMonth: string) {
  const [year, month] = yearMonth.split('-')
  return `T${month}/${year}`
}

function urgencyLabel(value: UrgencyTier) {
  if (value === 'CRITICAL') return 'Khẩn cấp'
  if (value === 'WARNING') return 'Sắp đến hạn'
  return 'Theo dõi'
}

function urgencySeverity(value: UrgencyTier) {
  if (value === 'CRITICAL') return 'danger'
  if (value === 'WARNING') return 'warn'
  return 'info'
}

function statusLabel(value: string) {
  if (value === 'active') return 'Hiệu lực'
  if (value === 'expired') return 'Hết hạn'
  if (value === 'terminated') return 'Chấm dứt'
  return value
}

function statusSeverity(value: string) {
  if (value === 'active') return 'success'
  if (value === 'expired') return 'warn'
  if (value === 'terminated') return 'danger'
  return 'secondary'
}

function employeeOptionLabel(option: EmployeeLookupItem) {
  return `${option.display_code} - ${option.full_name}`
}

function forecastWidth(count: number) {
  if (!maxForecastCount.value) return 0
  return Math.max((count / maxForecastCount.value) * 100, count > 0 ? 10 : 0)
}

async function loadDepartments() {
  try {
    const response = await departmentService.getList(true)
    departments.value = response.data
  } catch {
    departments.value = []
  }
}

async function loadSummaryAndCharts() {
  const [summaryRes, byTypeRes, forecastRes] = await Promise.all([
    contractReportService.getSummary({
      department_id: filters.value.department_id,
    }),
    contractReportService.getByType({
      department_id: filters.value.department_id,
      year: filters.value.year,
    }),
    contractReportService.getForecast({
      months_ahead: filters.value.months_ahead,
    }),
  ])

  summary.value = summaryRes.data
  byType.value = byTypeRes.data
  forecast.value = forecastRes.data
}

async function loadExpiringPage(page = pageState.value.page) {
  loadingExpiring.value = true
  try {
    const response = await contractReportService.getExpiring({
      department_id: filters.value.department_id,
      days_ahead: filters.value.days_ahead,
      keyword: filters.value.keyword || undefined,
      page,
      page_size: pageState.value.pageSize,
    })
    expiringPage.value = response.data
    pageState.value.page = page
  } finally {
    loadingExpiring.value = false
  }
}

async function refreshAll() {
  loading.value = true
  errorMsg.value = ''

  try {
    await Promise.all([
      loadSummaryAndCharts(),
      loadExpiringPage(1),
    ])
  } catch {
    errorMsg.value = 'Không tải được báo cáo hợp đồng. Vui lòng thử lại.'
    toast.add({
      severity: 'error',
      summary: 'Không tải được báo cáo',
      detail: 'Một hoặc nhiều dữ liệu đã tải thất bại.',
      life: 3000,
    })
  } finally {
    loading.value = false
  }
}

async function exportExcel() {
  exporting.value = true
  try {
    await contractReportService.exportXlsx({
      department_id: filters.value.department_id,
      status: 'active',
      days_ahead: filters.value.days_ahead,
    })
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Xuất Excel thất bại',
      detail: 'Không thể xuất báo cáo hợp đồng.',
      life: 3000,
    })
  } finally {
    exporting.value = false
  }
}

async function searchEmployees(event: { query: string }) {
  employeeSearchLoading.value = true
  try {
    const response = await employeeService.lookup({
      keyword: event.query || undefined,
      limit: 20,
    })
    employeeSuggestions.value = response.data
  } finally {
    employeeSearchLoading.value = false
  }
}

async function loadHistory(employeeId: number) {
  historyLoading.value = true
  try {
    const response = await contractReportService.getHistory(employeeId)
    history.value = response.data
  } catch {
    history.value = null
    toast.add({
      severity: 'error',
      summary: 'Không tải được lịch sử hợp đồng',
      detail: 'Vui lòng chọn lại nhân viên hoặc thử lại sau.',
      life: 3000,
    })
  } finally {
    historyLoading.value = false
  }
}

function onEmployeeSelect(event: { value: EmployeeLookupItem }) {
  const employee = event.value
  if (employee?.id) {
    void loadHistory(employee.id)
  }
}

function clearHistory() {
  selectedEmployee.value = null
  history.value = null
}

function applyMobileFilters() {
  mobileFiltersOpen.value = false
  void refreshAll()
}

function onExpiringPage(event: { page: number; rows: number }) {
  pageState.value.page = event.page + 1
  pageState.value.pageSize = event.rows
  void loadExpiringPage(pageState.value.page)
}

onMounted(async () => {
  syncViewport()
  window.addEventListener('resize', syncViewport)
  await loadDepartments()
  await refreshAll()
})

onUnmounted(() => {
  window.removeEventListener('resize', syncViewport)
})
</script>

<style>
.contract-report-view {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.contract-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.contract-mobile-filter-btn {
  display: none;
}

.contract-toolbar-actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.contract-filter-card {
  padding: 1rem;
  border: 1px solid var(--l-border);
  background: var(--l-surface);
  box-shadow: var(--l-shadow);
}

.contract-filter-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1rem;
}

.contract-filter-grid.is-mobile {
  grid-template-columns: 1fr;
}

.contract-field {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.contract-field-span-2 {
  grid-column: span 2;
}

.contract-field label {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--l-text-muted);
}

.contract-drawer-actions {
  margin-top: 1rem;
}

.contract-error-banner {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1rem;
  border: 1px solid color-mix(in srgb, var(--p-red-500) 35%, transparent);
  background: color-mix(in srgb, var(--p-red-500) 8%, var(--l-surface));
  color: var(--l-text);
}

.contract-kpi-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 1rem;
}

.contract-kpi-card {
  padding: 1rem;
  border: 1px solid var(--l-border);
  border-radius: 1rem;
  background: var(--l-surface);
  box-shadow: var(--l-shadow);
}

.contract-kpi-card.border-blue {
  border-top: 4px solid #2563eb;
}

.contract-kpi-card.border-red {
  border-top: 4px solid #dc2626;
}

.contract-kpi-card.border-orange {
  border-top: 4px solid #ea580c;
}

.contract-kpi-card.border-gold {
  border-top: 4px solid #d97706;
}

.contract-kpi-card.border-green {
  border-top: 4px solid #059669;
}

.contract-kpi-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.85rem;
}

.contract-kpi-title {
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--l-text-muted);
}

.contract-kpi-icon {
  font-size: 1.05rem;
}

.contract-kpi-icon.blue {
  color: #2563eb;
}

.contract-kpi-icon.red {
  color: #dc2626;
}

.contract-kpi-icon.orange {
  color: #ea580c;
}

.contract-kpi-icon.gold {
  color: #d97706;
}

.contract-kpi-icon.green {
  color: #059669;
}

.contract-kpi-value {
  font-size: clamp(1.85rem, 2vw, 2.25rem);
  line-height: 1;
  font-weight: 800;
  color: var(--l-text);
}

.contract-kpi-sub {
  margin-top: 0.5rem;
  font-size: 0.82rem;
  color: var(--l-text-muted);
}

.contract-expiring-card,
.contract-history-card,
.contract-analytics-grid .analytics-card {
  border: 1px solid var(--l-border);
  background: var(--l-surface);
  box-shadow: var(--l-shadow);
}

.contract-section-header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.contract-section-subtitle {
  display: inline-block;
  margin-top: 0.2rem;
  font-size: 0.88rem;
  color: var(--l-text-muted);
}

.contract-empty {
  padding: 1.5rem 0.5rem;
  text-align: center;
  color: var(--l-text-muted);
}

.contract-employee-cell {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.contract-employee-cell span {
  color: var(--l-text-muted);
  font-size: 0.82rem;
}

.contract-days-cell {
  display: flex;
  align-items: baseline;
  gap: 0.25rem;
}

.contract-days-cell strong {
  font-size: 1rem;
}

.contract-days-cell span {
  color: var(--l-text-muted);
  font-size: 0.8rem;
}

.contract-analytics-grid {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 1rem;
}

.contract-chart-loading {
  display: flex;
  justify-content: center;
  padding: 1.5rem 0;
}

.contract-donut-panel {
  display: grid;
  grid-template-columns: minmax(12rem, 15rem) minmax(0, 1fr);
  gap: 1.5rem;
  align-items: center;
}

.contract-donut-wrap {
  display: flex;
  justify-content: center;
}

.contract-donut-chart {
  display: grid;
  place-items: center;
  width: 13.5rem;
  height: 13.5rem;
  border-radius: 50%;
}

.contract-donut-inner {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  width: 7rem;
  height: 7rem;
  border-radius: 50%;
  background: var(--l-surface);
  box-shadow: inset 0 0 0 1px var(--l-border);
}

.contract-donut-inner strong {
  font-size: 1.4rem;
  color: var(--l-text);
}

.contract-donut-inner span {
  font-size: 0.8rem;
  color: var(--l-text-muted);
}

.contract-donut-legend {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.contract-donut-item {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
}

.contract-donut-swatch {
  width: 0.85rem;
  height: 0.85rem;
  border-radius: 999px;
  margin-top: 0.25rem;
  flex: 0 0 auto;
}

.contract-donut-copy {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.contract-donut-copy strong {
  color: var(--l-text);
}

.contract-donut-copy span {
  color: var(--l-text-muted);
  font-size: 0.82rem;
}

.contract-forecast-list {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}

.contract-forecast-row {
  display: grid;
  grid-template-columns: 5rem minmax(0, 1fr) 3rem;
  gap: 0.75rem;
  align-items: center;
}

.contract-forecast-label,
.contract-forecast-value {
  font-size: 0.86rem;
  color: var(--l-text-muted);
}

.contract-forecast-track {
  height: 0.7rem;
  overflow: hidden;
  border-radius: 999px;
  background: color-mix(in srgb, var(--p-primary-color) 12%, var(--l-surface));
}

.contract-forecast-fill {
  height: 100%;
  min-width: 0;
  border-radius: inherit;
  background: linear-gradient(90deg, #2563eb, #0f766e);
}

.contract-history-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-end;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.contract-history-search {
  flex: 1 1 24rem;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.contract-history-search label {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--l-text-muted);
}

.contract-history-summary {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  color: var(--l-text-muted);
  text-align: right;
}

.contract-history-summary strong {
  color: var(--l-text);
}

.contract-employee-option {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}

.contract-employee-option span {
  color: var(--l-text-muted);
  font-size: 0.82rem;
}

@media (max-width: 1279px) {
  .contract-filter-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .contract-field-span-2 {
    grid-column: span 2;
  }

  .contract-kpi-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .contract-analytics-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 1023px) {
  .contract-mobile-filter-btn {
    display: inline-flex;
  }

  .contract-toolbar-actions {
    width: 100%;
  }

  .contract-toolbar-actions .p-button {
    flex: 1 1 auto;
  }

  .contract-kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .contract-donut-panel {
    grid-template-columns: 1fr;
  }

  .contract-history-summary {
    text-align: left;
  }
}

@media (max-width: 767px) {
  .contract-filter-grid,
  .contract-filter-grid.is-mobile {
    grid-template-columns: 1fr;
  }

  .contract-field-span-2 {
    grid-column: auto;
  }

  .contract-kpi-grid {
    grid-template-columns: 1fr;
  }

  .contract-section-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .contract-forecast-row {
    grid-template-columns: 4.25rem minmax(0, 1fr) 2.5rem;
  }

  .contract-donut-chart {
    width: 11.5rem;
    height: 11.5rem;
  }
}
</style>
