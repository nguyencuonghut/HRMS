<template>
  <div class="insurance-analytics-view">
    <!-- Page Header -->
    <div class="page-header">
      <div>
        <h2>Phân tích bảo hiểm</h2>
        <span class="subtitle">{{ subtitleText }}</span>
      </div>
    </div>

    <!-- Toolbar Filters -->
    <div class="toolbar">
      <Select
        v-model="filters.year"
        :options="yearOptions"
        option-label="label"
        option-value="value"
        placeholder="Năm"
        class="toolbar-filter-sm"
      />

      <Select
        v-model="filters.month"
        :options="monthOptions"
        option-label="label"
        option-value="value"
        placeholder="Tháng"
        class="toolbar-filter-sm"
      />

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

      <Button label="Lọc" icon="pi pi-filter" :loading="loading" @click="loadAllData" />
      <Button
        icon="pi pi-refresh"
        severity="secondary"
        text rounded
        :loading="loading"
        v-tooltip.top="'Làm mới'"
        @click="resetFilters"
      />
      <Button
        icon="pi pi-file-excel"
        label="Xuất Excel"
        severity="success"
        outlined
        :loading="isExporting"
        @click="exportExcel"
      />
    </div>

    <!-- Error Banner -->
    <div v-if="errorMsg" class="error-banner card">
      <i class="pi pi-exclamation-triangle" />
      <span>{{ errorMsg }}</span>
    </div>

    <!-- KPI Summary Cards -->
    <div class="kpi-grid">
      <!-- Card 1: Đang tham gia BHXH -->
      <div class="kpi-card border-blue">
        <div class="kpi-card-header">
          <span class="kpi-card-title">Đang tham gia BHXH</span>
          <i class="pi pi-shield kpi-icon-blue" />
        </div>
        <div v-if="loading" class="kpi-skeleton">
          <Skeleton width="100px" height="36px" />
          <Skeleton width="150px" height="16px" class="mt-2" />
        </div>
        <div v-else>
          <div class="kpi-card-value">{{ formatInteger(dashboard?.participating_count) }} NV</div>
          <div class="kpi-card-sub">Nhân sự có trạng thái active</div>
        </div>
      </div>

      <!-- Card 2: Tổng nhân viên -->
      <div class="kpi-card border-teal">
        <div class="kpi-card-header">
          <span class="kpi-card-title">Tổng nhân sự active</span>
          <i class="pi pi-users kpi-icon-teal" />
        </div>
        <div v-if="loading" class="kpi-skeleton">
          <Skeleton width="100px" height="36px" />
          <Skeleton width="150px" height="16px" class="mt-2" />
        </div>
        <div v-else>
          <div class="kpi-card-value">{{ formatInteger(dashboard?.total_active_employees) }} NV</div>
          <div class="kpi-card-sub">Toàn bộ nhân viên công ty</div>
        </div>
      </div>

      <!-- Card 3: Tỷ lệ tham gia -->
      <div class="kpi-card border-green">
        <div class="kpi-card-header">
          <span class="kpi-card-title">Tỷ lệ tham gia</span>
          <i class="pi pi-chart-pie kpi-icon-green" />
        </div>
        <div v-if="loading" class="kpi-skeleton">
          <Skeleton width="100px" height="36px" />
          <Skeleton width="150px" height="16px" class="mt-2" />
        </div>
        <div v-else>
          <div class="kpi-card-value">{{ formatNumber(dashboard?.participation_rate) }}%</div>
          <div class="kpi-card-sub">Tỷ lệ đóng bảo hiểm xã hội</div>
        </div>
      </div>

      <!-- Card 4: Tổng quỹ lương BHXH -->
      <div class="kpi-card border-orange">
        <div class="kpi-card-header">
          <span class="kpi-card-title">Tổng quỹ lương BHXH</span>
          <i class="pi pi-money-bill kpi-icon-orange" />
        </div>
        <div v-if="loading" class="kpi-skeleton">
          <Skeleton width="130px" height="36px" />
          <Skeleton width="150px" height="16px" class="mt-2" />
        </div>
        <div v-else>
          <div class="kpi-card-value currency">{{ formatCurrency(dashboard?.total_basis_amount) }}</div>
          <div class="kpi-card-sub">Mức lương đóng BHXH thực tế</div>
        </div>
      </div>

      <!-- Card 5: Biến động theo kỳ -->
      <div class="kpi-card border-red">
        <div class="kpi-card-header">
          <span class="kpi-card-title">{{ annualMode ? 'Biến động năm' : 'Biến động tháng' }}</span>
          <i class="pi pi-arrows-h kpi-icon-red" />
        </div>
        <div v-if="loading" class="kpi-skeleton">
          <Skeleton width="100px" height="36px" />
          <Skeleton width="150px" height="16px" class="mt-2" />
        </div>
        <div v-else>
          <div class="kpi-card-value variation">
            <span class="text-green-500" v-tooltip.top="annualMode ? 'Tăng trong năm' : 'Tăng trong tháng'">+{{ dashboard?.increased_count }}</span>
            <span class="text-red-500" v-tooltip.top="annualMode ? 'Giảm trong năm' : 'Giảm trong tháng'">-{{ dashboard?.decreased_count }}</span>
          </div>
          <div class="kpi-card-sub">Thay đổi ròng: {{ (dashboard?.net_change ?? 0) >= 0 ? '+' : '' }}{{ dashboard?.net_change ?? 0 }} NV</div>
        </div>
      </div>
    </div>

    <!-- Charts Section -->
    <div class="half-grid">
      <!-- Stacked Bar Chart: Tăng giảm 12 tháng -->
      <div class="analytics-card">
        <h3 class="section-title">Xu hướng tăng/giảm bảo hiểm (12 tháng)</h3>
        <div v-if="loading" class="chart-loading">
          <Skeleton height="200px" />
        </div>
        <div v-else class="custom-chart-wrapper">
          <div class="chart-legend">
            <div class="legend-item"><span class="legend-dot bg-green"></span> Tăng lao động</div>
            <div class="legend-item"><span class="legend-dot bg-red"></span> Giảm lao động</div>
          </div>
          <!-- SVG Stacked Bar Chart -->
          <svg class="svg-chart" viewBox="0 0 500 200" width="100%">
            <!-- Y-Axis Grid Lines & Labels -->
            <line x1="45" y1="20" x2="480" y2="20" class="grid-line" />
            <line x1="45" y1="65" x2="480" y2="65" class="grid-line" />
            <line x1="45" y1="110" x2="480" y2="110" class="grid-line" />
            <line x1="45" y1="155" x2="480" y2="155" class="grid-line" />
            <text x="35" y="24" class="axis-label text-right">{{ formatInteger(monthlyChangesMaxVal) }}</text>
            <text x="35" y="89" class="axis-label text-right">{{ formatInteger(monthlyChangesMaxVal / 2) }}</text>
            <text x="35" y="159" class="axis-label text-right">0</text>

            <!-- Bars -->
            <g v-for="(point, idx) in monthlyChanges?.data" :key="point.month">
              <!-- Increased (Green) -->
              <rect
                :x="50 + idx * 35"
                :y="155 - (point.increased / (monthlyChangesMaxVal || 1)) * 135"
                width="10"
                :height="(point.increased / (monthlyChangesMaxVal || 1)) * 135"
                class="bar-green"
              >
                <title>Tháng {{ point.month }}: Tăng {{ point.increased }} NV</title>
              </rect>
              <!-- Decreased (Red) -->
              <rect
                :x="50 + idx * 35 + 12"
                :y="155 - (point.decreased / (monthlyChangesMaxVal || 1)) * 135"
                width="10"
                :height="(point.decreased / (monthlyChangesMaxVal || 1)) * 135"
                class="bar-red"
              >
                <title>Tháng {{ point.month }}: Giảm {{ point.decreased }} NV</title>
              </rect>
              <!-- X-Axis Label -->
              <text :x="50 + idx * 35 + 11" y="175" class="axis-label text-center">T{{ point.month }}</text>
            </g>
          </svg>
        </div>
      </div>

      <!-- Line Chart: Biến động quỹ lương -->
      <div class="analytics-card">
        <h3 class="section-title">Thay đổi quỹ lương đóng BHXH YTD (12 tháng)</h3>
        <div v-if="loading" class="chart-loading">
          <Skeleton height="200px" />
        </div>
        <div v-else class="custom-chart-wrapper">
          <div class="chart-legend">
            <div class="legend-item"><span class="legend-dot bg-green"></span> Quỹ lương tăng (VND)</div>
            <div class="legend-item"><span class="legend-dot bg-red"></span> Quỹ lương giảm (VND)</div>
          </div>
          <!-- SVG Line Chart -->
          <svg class="svg-chart" viewBox="0 0 500 200" width="100%">
            <!-- Y-Axis Grid Lines & Labels -->
            <line x1="45" y1="20" x2="480" y2="20" class="grid-line" />
            <line x1="45" y1="65" x2="480" y2="65" class="grid-line" />
            <line x1="45" y1="110" x2="480" y2="110" class="grid-line" />
            <line x1="45" y1="155" x2="480" y2="155" class="grid-line" />
            
            <text x="35" y="24" class="axis-label text-right">{{ formatCompactAmount(payrollFundMaxVal) }}</text>
            <text x="35" y="89" class="axis-label text-right">{{ formatCompactAmount(payrollFundMaxVal / 2) }}</text>
            <text x="35" y="159" class="axis-label text-right">0</text>

            <!-- Line Path: Added Amount (Green) -->
            <path
              :d="generateLinePath('added')"
              fill="none"
              stroke="#22c55e"
              stroke-width="2.5"
            />
            <!-- Line Path: Removed Amount (Red) -->
            <path
              :d="generateLinePath('removed')"
              fill="none"
              stroke="#ef4444"
              stroke-width="2.5"
            />

            <!-- Dots for points -->
            <g v-for="(point, idx) in payrollFund?.data" :key="point.month">
              <!-- Added Point -->
              <circle
                :cx="50 + idx * 35 + 5"
                :cy="155 - (point.added_amount / (payrollFundMaxVal || 1)) * 135"
                r="4.5"
                fill="#22c55e"
                class="chart-dot"
              >
                <title>Tháng {{ point.month }}: Tăng quỹ +{{ formatCurrency(point.added_amount) }}</title>
              </circle>
              <!-- Removed Point -->
              <circle
                :cx="50 + idx * 35 + 5"
                :cy="155 - (point.removed_amount / (payrollFundMaxVal || 1)) * 135"
                r="4.5"
                fill="#ef4444"
                class="chart-dot"
              >
                <title>Tháng {{ point.month }}: Giảm quỹ -{{ formatCurrency(point.removed_amount) }}</title>
              </circle>
              <!-- X-Axis Label -->
              <text :x="50 + idx * 35 + 5" y="175" class="axis-label text-center">T{{ point.month }}</text>
            </g>
          </svg>
        </div>
      </div>
    </div>

    <!-- Section: Department Breakdown -->
    <div class="analytics-card">
      <h3 class="section-title">Tỷ lệ và quỹ lương bảo hiểm theo phòng ban</h3>
      <DataTable :value="departmentBreakdown?.items" :loading="loading" responsive-layout="scroll">
        <Column header="Phòng ban" field="department_name" style="min-width: 200px" />
        <Column header="Số NV tham gia BHXH" class="text-right" style="width: 150px">
          <template #body="{ data }">
            <strong>{{ formatInteger(data.participating_count) }}</strong>
            <span class="text-muted"> / {{ formatInteger(data.total_count) }} NV</span>
          </template>
        </Column>
        <Column header="Tỷ lệ tham gia BHXH" class="text-right" style="width: 180px">
          <template #body="{ data }">
            <span :class="['participation-rate', getRateClass(data.participation_rate)]">
              {{ formatNumber(data.participation_rate) }}%
            </span>
          </template>
        </Column>
        <Column header="Quỹ lương đóng BHXH" class="text-right" style="min-width: 180px">
          <template #body="{ data }">
            <span class="font-semibold">{{ formatCurrency(data.total_basis_amount) }}</span>
          </template>
        </Column>
        <template #empty>
          <div class="empty-state p-4">Không có dữ liệu thống kê phòng ban</div>
        </template>
      </DataTable>
    </div>

    <!-- Section: Non-Participants Warning & DataTable -->
    <div class="analytics-card warning-card">
      <div class="card-header-row">
        <div class="header-with-badge">
          <h3 class="section-title">Nhân sự chưa tham gia bảo hiểm bắt buộc</h3>
          <span v-if="!loading && (nonParticipants?.total ?? 0) > 0" class="badge-warning">
            ⚠ Phát hiện {{ nonParticipants?.total ?? 0 }} nhân sự
          </span>
        </div>
      </div>
      
      <DataTable
        :value="nonParticipants?.items"
        :loading="loading"
        responsive-layout="scroll"
      >
        <Column field="employee_code" header="Mã NV" style="width: 120px" />
        <Column field="full_name" header="Nhân sự" style="min-width: 180px" />
        <Column field="department_name" header="Phòng ban" style="min-width: 150px" />
        <Column header="Trạng thái hồ sơ" style="width: 160px">
          <template #body="{ data }">
            <span :class="['status-badge', getStatusClass(data.participation_status)]">
              {{ getStatusLabel(data.participation_status) }}
            </span>
          </template>
        </Column>
        <Column header="Ngày hiệu lực" style="width: 140px">
          <template #body="{ data }">
            {{ formatDate(data.status_effective_from) }}
          </template>
        </Column>
        <Column header="Tham gia BHXH lần đầu" style="width: 180px">
          <template #body="{ data }">
            {{ formatDate(data.company_bhxh_joined_date) }}
          </template>
        </Column>
        <Column field="status_note" header="Ghi chú hồ sơ" style="min-width: 200px">
          <template #body="{ data }">
            <span class="text-muted text-sm">{{ data.status_note || '—' }}</span>
          </template>
        </Column>
        <template #empty>
          <div class="empty-state p-4 text-green-500 font-semibold">
            <i class="pi pi-check-circle" /> Tất cả nhân viên đang làm việc đều tham gia bảo hiểm đầy đủ
          </div>
        </template>
      </DataTable>

      <!-- Pagination for Non-Participants -->
      <div v-if="nonParticipants && nonParticipants.total > filters.page_size" class="pagination-row">
        <Button
          icon="pi pi-chevron-left"
          severity="secondary"
          text
          :disabled="filters.page === 1"
          @click="changePage(filters.page - 1)"
        />
        <span class="page-info">Trang {{ filters.page }} / {{ Math.ceil(nonParticipants.total / filters.page_size) }}</span>
        <Button
          icon="pi pi-chevron-right"
          severity="secondary"
          text
          :disabled="filters.page >= Math.ceil(nonParticipants.total / filters.page_size)"
          @click="changePage(filters.page + 1)"
        />
      </div>
    <!-- Progress Dialog for Asynchronous Queue Export -->
    <Dialog v-model:visible="showExportDialog" modal header="Đang chuẩn bị tệp tin..." :closable="false" style="width: 25rem">
      <div class="text-center p-4">
        <ProgressSpinner v-if="exportProgress === 0" style="width: 50px; height: 50px" />
        <ProgressBar v-else :value="exportProgress" style="height: 6px" class="mt-3"></ProgressBar>
        <p class="mt-3">Hệ thống đang chuẩn bị tệp tin của bạn. Vui lòng không đóng trình duyệt hoặc tải lại trang.</p>
        <Button label="Hủy" class="mt-2" severity="secondary" @click="cancelExport" />
      </div>
    </Dialog>
    </div>
  </div>
  <Toast />
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import Button from 'primevue/button'
import Select from 'primevue/select'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Skeleton from 'primevue/skeleton'
import Toast from 'primevue/toast'
import vTooltip from 'primevue/tooltip'
import { useToast } from 'primevue/usetoast'
import Dialog from 'primevue/dialog'
import ProgressBar from 'primevue/progressbar'
import ProgressSpinner from 'primevue/progressspinner'

import { usePermissionGate } from '@/composables/usePermissionGate'
import insuranceService, {
  type InsuranceDashboardKPI,
  type InsuranceMonthlyChangesResponse,
  type InsurancePayrollFundResponse,
  type InsuranceDepartmentBreakdownResponse,
  type InsuranceNonParticipantsResponse,
} from '@/services/insuranceService'
import departmentService, { type DepartmentRead } from '@/services/departmentService'
import { useExportQueue } from '@/composables/useExportQueue'

const toast = useToast()
const permissionGate = usePermissionGate()
const canLoadDepartments = computed(() => permissionGate.canAccessRoute('/org/departments'))

// ── Configuration Options ────────────────────────────────────────────────────
const now = new Date()
const currentYear = now.getFullYear()
const currentMonth = now.getMonth() + 1

const yearOptions = Array.from({ length: 7 }, (_, i) => {
  const y = currentYear - 3 + i
  return { label: `Năm ${y}`, value: y }
})

const monthOptions = [
  { label: 'Toàn năm', value: null },
  ...Array.from({ length: 12 }, (_, i) => {
    const m = i + 1
    return { label: `Tháng ${m}`, value: m }
  }),
]

// ── State ─────────────────────────────────────────────────────────────────────
const loading = ref(false)
const { isExporting, exportProgress, showExportDialog, startExport, cancelExport } = useExportQueue()
const errorMsg = ref('')

const departments = ref<DepartmentRead[]>([])
const filters = reactive({
  year: currentYear,
  month: currentMonth as number | null,
  department_id: null as number | null,
  page: 1,
  page_size: 10,
})

const dashboard = ref<InsuranceDashboardKPI | null>(null)
const monthlyChanges = ref<InsuranceMonthlyChangesResponse | null>(null)
const payrollFund = ref<InsurancePayrollFundResponse | null>(null)
const departmentBreakdown = ref<InsuranceDepartmentBreakdownResponse | null>(null)
const nonParticipants = ref<InsuranceNonParticipantsResponse | null>(null)
const annualMode = computed(() => filters.month === null)
const subtitleText = computed(() =>
  annualMode.value
    ? `Phân tích toàn năm ${filters.year} về tình hình đóng bảo hiểm, biến động tăng giảm và cảnh báo rủi ro toàn hệ thống`
    : 'Phân tích tình hình đóng bảo hiểm, biến động tăng giảm và cảnh báo rủi ro toàn hệ thống'
)

// ── Computations for SVG Charts ───────────────────────────────────────────────
const monthlyChangesMaxVal = computed(() => {
  if (!monthlyChanges.value || monthlyChanges.value.data.length === 0) return 10
  const max = Math.max(
    ...monthlyChanges.value.data.map(p => Math.max(p.increased, p.decreased))
  )
  return max > 0 ? Math.ceil(max * 1.2) : 10
})

const payrollFundMaxVal = computed(() => {
  if (!payrollFund.value || payrollFund.value.data.length === 0) return 10000000
  const max = Math.max(
    ...payrollFund.value.data.map(p => Math.max(Number(p.added_amount), Number(p.removed_amount)))
  )
  return max > 0 ? Math.ceil(max * 1.15) : 10000000
})

function generateLinePath(type: 'added' | 'removed'): string {
  if (!payrollFund.value || payrollFund.value.data.length === 0) return ''
  const maxVal = payrollFundMaxVal.value || 1
  const coords = payrollFund.value.data.map((point, idx) => {
    const val = type === 'added' ? Number(point.added_amount) : Number(point.removed_amount)
    const x = 50 + idx * 35 + 5
    const y = 155 - (val / maxVal) * 135
    return `${x},${y}`
  })
  return `M ${coords.join(' L ')}`
}

// ── API Loader functions ──────────────────────────────────────────────────────
async function loadMeta() {
  if (!canLoadDepartments.value) {
    departments.value = []
    return
  }
  try {
    const res = await departmentService.getList(true)
    departments.value = res.data
  } catch (e) {
    console.error('Lỗi tải danh sách phòng ban', e)
  }
}

async function loadAllData() {
  loading.value = true
  errorMsg.value = ''
  
  const dashboardParams = {
    year: filters.year,
    month: filters.month,
    department_id: filters.department_id,
  }

  const trendParams = {
    year: filters.year,
    department_id: filters.department_id,
  }

  const nonParticipantsParams = {
    department_id: filters.department_id,
    page: filters.page,
    page_size: filters.page_size,
  }

  try {
    const [dashRes, changesRes, fundRes, breakdownRes, nonRes] = await Promise.all([
      insuranceService.getAnalyticsDashboard(dashboardParams),
      insuranceService.getMonthlyChanges(trendParams),
      insuranceService.getPayrollFund(trendParams),
      insuranceService.getDepartmentBreakdown({ year: filters.year, month: filters.month }),
      insuranceService.getNonParticipants(nonParticipantsParams),
    ])

    dashboard.value = dashRes.data
    monthlyChanges.value = changesRes.data
    payrollFund.value = fundRes.data
    departmentBreakdown.value = breakdownRes.data
    nonParticipants.value = nonRes.data
  } catch (e) {
    errorMsg.value = 'Không thể tải dữ liệu báo cáo bảo hiểm. Vui lòng thử lại.'
    console.error('Lỗi tải báo cáo bảo hiểm', e)
  } finally {
    loading.value = false
  }
}

async function changePage(p: number) {
  filters.page = p
  try {
    const nonRes = await insuranceService.getNonParticipants({
      department_id: filters.department_id,
      page: filters.page,
      page_size: filters.page_size,
    })
    nonParticipants.value = nonRes.data
  } catch (e) {
    console.error('Lỗi tải phân trang', e)
  }
}

function resetFilters() {
  filters.year = currentYear
  filters.month = currentMonth
  filters.department_id = null
  filters.page = 1
  loadAllData()
}

// ── Excel Export ──
async function exportExcel() {
  const jobFilters = {
    year: filters.year,
    month: filters.month,
    department_id: filters.department_id,
  }
  const filename = `bao_cao_bao_hiem_${filters.year}_${filters.month || 'ca_nam'}.xlsx`
  await startExport('insurance', jobFilters, filename)
}

// ── Formatters & Helper Style Classes ─────────────────────────────────────────
function formatNumber(val: number | undefined): string {
  if (val === undefined || val === null) return '—'
  return new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 1 }).format(val)
}

function formatInteger(val: number | undefined): string {
  if (val === undefined || val === null) return '0'
  return new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 }).format(val)
}

function formatCurrency(val: number | undefined | string): string {
  if (val === undefined || val === null) return '0 đ'
  const num = typeof val === 'string' ? Number(val) : val
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(num)
}

function formatCompactAmount(val: number): string {
  if (val >= 1000000000) return `${(val / 1000000000).toFixed(1)}B`
  if (val >= 1000000) return `${(val / 1000000).toFixed(1)}M`
  if (val >= 1000) return `${(val / 1000).toFixed(0)}k`
  return String(val)
}

function formatDate(val: string | null): string {
  if (!val) return '—'
  const date = new Date(val)
  if (Number.isNaN(date.getTime())) return val
  return new Intl.DateTimeFormat('vi-VN').format(date)
}

function getRateClass(rate: number): string {
  if (rate === 100) return 'text-green'
  if (rate < 80) return 'text-red'
  return 'text-normal'
}

function getStatusClass(status: string | null): string {
  if (status === 'paused') return 'badge-paused'
  if (status === 'stopped') return 'badge-stopped'
  return 'badge-unregistered'
}

function getStatusLabel(status: string | null): string {
  if (status === 'paused') return 'Tạm dừng đóng'
  if (status === 'stopped') return 'Dừng đóng'
  return 'Chưa có hồ sơ'
}

onMounted(async () => {
  await loadMeta()
  await loadAllData()
})
</script>

<style scoped>
.insurance-analytics-view {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.section-title {
  font-size: 1.05rem;
  font-weight: 700;
  margin-top: 0;
  margin-bottom: 1.25rem;
  color: var(--l-text);
}

.error-banner {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.875rem 1rem;
  border: 1px solid color-mix(in srgb, var(--p-red-500) 28%, transparent);
  background: color-mix(in srgb, var(--p-red-500) 10%, var(--p-surface-0));
  color: var(--p-red-700);
  border-radius: 12px;
}
html.dark-mode .error-banner {
  color: var(--p-red-300);
}

/* Grids */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 1rem;
}

.half-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.25rem;
}

@media (max-width: 1200px) {
  .kpi-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .kpi-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .half-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 480px) {
  .kpi-grid {
    grid-template-columns: 1fr;
  }
}

/* Premium Analytics Card */
.analytics-card {
  padding: 1.5rem;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 12px;
  box-shadow: var(--l-shadow, 0 4px 6px -1px rgb(0 0 0 / 0.05));
}

.warning-card {
  border-color: color-mix(in srgb, var(--p-orange-500) 40%, var(--p-content-border-color));
  background: color-mix(in srgb, var(--p-orange-500) 2%, var(--p-content-background));
}

/* KPI Cards styling */
.kpi-card {
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 16px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  box-shadow: var(--l-shadow, 0 4px 6px -1px rgb(0 0 0 / 0.05));
}
.kpi-card.border-blue { border-color: color-mix(in srgb, var(--p-blue-500) 28%, var(--p-content-border-color)); }
.kpi-card.border-teal { border-color: color-mix(in srgb, var(--p-teal-500) 28%, var(--p-content-border-color)); }
.kpi-card.border-green { border-color: color-mix(in srgb, var(--p-green-500) 28%, var(--p-content-border-color)); }
.kpi-card.border-orange { border-color: color-mix(in srgb, var(--p-orange-500) 28%, var(--p-content-border-color)); }
.kpi-card.border-red { border-color: color-mix(in srgb, var(--p-red-500) 28%, var(--p-content-border-color)); }

.kpi-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.kpi-card-title {
  color: var(--p-text-muted-color);
  font-size: 0.78rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.kpi-card-header i {
  font-size: 1.1rem;
  padding: 0.4rem;
  border-radius: 8px;
  background: color-mix(in srgb, var(--p-content-border-color) 40%, transparent);
}
.kpi-icon-blue { color: var(--p-blue-500); }
.kpi-icon-teal { color: var(--p-teal-500); }
.kpi-icon-green { color: var(--p-green-500); }
.kpi-icon-orange { color: var(--p-orange-500); }
.kpi-icon-red { color: var(--p-red-500); }

.kpi-card-value {
  font-size: 1.8rem;
  font-weight: 800;
  line-height: 1.1;
  color: var(--p-text-color);
  margin-top: 0.25rem;
}
.kpi-card-value.currency {
  font-size: 1.5rem;
  font-weight: 700;
}
.kpi-card-value.variation {
  display: flex;
  gap: 0.75rem;
  font-size: 1.7rem;
}
.kpi-card-sub {
  color: var(--p-text-muted-color);
  font-size: 0.8rem;
}

/* Custom SVG Chart Elements */
.custom-chart-wrapper {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.chart-legend {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  font-size: 0.8rem;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  color: var(--p-text-muted-color);
}
.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 99px;
}
.legend-dot.bg-green { background-color: #22c55e; }
.legend-dot.bg-red { background-color: #ef4444; }

.svg-chart {
  background: color-mix(in srgb, var(--p-content-border-color) 10%, transparent);
  border-radius: 8px;
  padding: 0.5rem;
}

.grid-line {
  stroke: color-mix(in srgb, var(--p-content-border-color) 40%, transparent);
  stroke-dasharray: 4, 4;
}

.axis-label {
  fill: var(--p-text-muted-color);
  font-size: 8px;
  font-family: inherit;
}
.text-right { text-anchor: end; }
.text-center { text-anchor: middle; }

.bar-green {
  fill: #22c55e;
  rx: 2px;
  transition: fill 0.2s;
  cursor: pointer;
}
.bar-green:hover {
  fill: #16a34a;
}

.bar-red {
  fill: #ef4444;
  rx: 2px;
  transition: fill 0.2s;
  cursor: pointer;
}
.bar-red:hover {
  fill: #dc2626;
}

.chart-dot {
  stroke: #ffffff;
  stroke-width: 1.5;
  cursor: pointer;
  transition: r 0.2s;
}
.chart-dot:hover {
  r: 6.5px;
}

/* Warnings and Badges */
.header-with-badge {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}
.badge-warning {
  background-color: color-mix(in srgb, var(--p-orange-500) 15%, transparent);
  border: 1px solid color-mix(in srgb, var(--p-orange-500) 30%, transparent);
  color: var(--p-orange-600);
  font-size: 0.78rem;
  font-weight: 700;
  padding: 0.25rem 0.5rem;
  border-radius: 99px;
  margin-bottom: 1.25rem;
}
html.dark-mode .badge-warning {
  color: var(--p-orange-400);
}

.status-badge {
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.2rem 0.5rem;
  border-radius: 6px;
  text-align: center;
}
.badge-paused {
  background-color: color-mix(in srgb, var(--p-orange-500) 15%, transparent);
  color: var(--p-orange-600);
}
.badge-stopped {
  background-color: color-mix(in srgb, var(--p-red-500) 15%, transparent);
  color: var(--p-red-600);
}
.badge-unregistered {
  background-color: color-mix(in srgb, var(--p-content-border-color) 40%, transparent);
  color: var(--p-text-muted-color);
}

.participation-rate {
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.text-green { color: var(--p-green-500); }
.text-red { color: var(--p-red-500); }
.text-normal { color: inherit; }

.pagination-row {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 1rem;
}
.page-info {
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}
</style>
