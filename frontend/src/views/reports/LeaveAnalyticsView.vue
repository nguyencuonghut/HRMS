<template>
  <div class="leave-analytics-view">
    <!-- Page Header -->
    <div class="page-header">
      <div>
        <h2>Phân tích nghỉ phép</h2>
        <span class="subtitle">Báo cáo trực quan và phân tích chuyên sâu về tình hình nghỉ phép</span>
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
        v-model="filters.department_id"
        :options="departments"
        option-label="name"
        option-value="id"
        placeholder="Phòng ban"
        show-clear
        filter
        class="toolbar-filter"
      />

      <Select
        v-model="filters.leave_type_id"
        :options="leaveTypes"
        option-label="name"
        option-value="id"
        placeholder="Loại phép"
        show-clear
        filter
        class="toolbar-filter"
      />

      <Button label="Lọc" icon="pi pi-filter" :loading="loading" @click="loadData" />
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
        :loading="exporting"
        @click="exportExcel"
      />
    </div>

    <!-- Error Message -->
    <div v-if="errorMsg" class="error-banner card">
      <i class="pi pi-exclamation-triangle" />
      <span>{{ errorMsg }}</span>
    </div>

    <!-- KPI Summary Cards -->
    <div class="kpi-grid">
      <!-- Card 1: Tổng ngày YTD -->
      <div class="kpi-card border-blue">
        <div class="kpi-card-header">
          <span class="kpi-card-title">Tổng ngày nghỉ YTD</span>
          <i class="pi pi-calendar kpi-icon-blue" />
        </div>
        <div v-if="loading" class="kpi-skeleton">
          <Skeleton width="100px" height="36px" />
          <Skeleton width="150px" height="16px" class="mt-2" />
        </div>
        <div v-else>
          <div class="kpi-card-value">{{ formatNumber(summary?.total_days_ytd) }}</div>
          <div class="kpi-card-sub">Tổng số ngày nghỉ trong năm {{ filters.year }}</div>
        </div>
      </div>

      <!-- Card 2: Tỷ lệ sử dụng phép -->
      <div class="kpi-card border-green">
        <div class="kpi-card-header">
          <span class="kpi-card-title">Tỷ lệ dùng phép TB</span>
          <i class="pi pi-chart-pie kpi-icon-green" />
        </div>
        <div v-if="loading" class="kpi-skeleton">
          <Skeleton width="100px" height="36px" />
          <Skeleton width="150px" height="16px" class="mt-2" />
        </div>
        <div v-else>
          <div class="kpi-card-value">{{ formatNumber(summary?.avg_usage_rate) }}%</div>
          <div class="kpi-card-sub">So với tổng quỹ phép được cấp</div>
        </div>
      </div>

      <!-- Card 3: Số NV chưa nghỉ -->
      <div class="kpi-card border-orange">
        <div class="kpi-card-header">
          <span class="kpi-card-title">Nhân sự chưa nghỉ</span>
          <i class="pi pi-user-minus kpi-icon-orange" />
        </div>
        <div v-if="loading" class="kpi-skeleton">
          <Skeleton width="100px" height="36px" />
          <Skeleton width="150px" height="16px" class="mt-2" />
        </div>
        <div v-else>
          <div class="kpi-card-value">{{ formatInteger(summary?.employees_not_taken) }} NV</div>
          <div class="kpi-card-sub">Có phép năm nhưng chưa nghỉ ngày nào</div>
        </div>
      </div>

      <!-- Card 4: Tồn sắp hết hạn -->
      <div class="kpi-card border-red">
        <div class="kpi-card-header">
          <span class="kpi-card-title">Phép sắp hết hạn</span>
          <i class="pi pi-exclamation-triangle kpi-icon-red" />
        </div>
        <div v-if="loading" class="kpi-skeleton">
          <Skeleton width="100px" height="36px" />
          <Skeleton width="150px" height="16px" class="mt-2" />
        </div>
        <div v-else>
          <div class="kpi-card-value">{{ formatNumber(summary?.days_expiring_30d) }} ngày</div>
          <div class="kpi-card-sub">Số ngày tồn phép hết hạn trong 30 ngày</div>
        </div>
      </div>
    </div>

    <!-- Section 2: Bar Chart theo loại phép -->
    <div class="analytics-card">
      <h3 class="section-title">Ngày nghỉ theo loại phép</h3>
      <div v-if="loading" style="padding: 1rem 0">
        <Skeleton v-for="i in 3" :key="i" height="24px" style="margin-bottom: 1rem" />
      </div>
      <div v-else-if="!byType || byType.items.length === 0" class="empty-state">
        <i class="pi pi-inbox" />
        <span>Không có dữ liệu loại phép nghỉ</span>
      </div>
      <div v-else class="custom-bar-chart">
        <div v-for="item in byType.items" :key="item.leave_type_id" class="custom-bar-chart-row">
          <div class="custom-bar-chart-label">
            <strong>{{ item.leave_type_name }}</strong>
            <span class="custom-bar-chart-caption">{{ item.unique_employees }} nhân sự đã nghỉ</span>
          </div>
          <div class="custom-bar-chart-track-wrapper">
            <div class="custom-bar-chart-track">
              <div
                class="custom-bar-chart-fill"
                :style="{
                  width: `${item.percentage}%`,
                  backgroundColor: item.color_tag || 'var(--p-primary-color)'
                }"
              ></div>
            </div>
          </div>
          <div class="custom-bar-chart-value">
            <strong>{{ formatNumber(item.total_days) }} ngày</strong>
            <span class="custom-bar-chart-subvalue">({{ item.percentage }}% — {{ item.record_count }} lần)</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Section 3: Monthly Heatmap -->
    <div class="analytics-card">
      <h3 class="section-title">Chi tiết ngày nghỉ theo tháng & phòng ban</h3>
      <div v-if="loading" style="padding: 1rem 0">
        <Skeleton height="200px" />
      </div>
      <div v-else-if="!heatmap || heatmap.departments.length === 0" class="empty-state">
        <i class="pi pi-inbox" />
        <span>Không có dữ liệu heatmap tháng</span>
      </div>
      <div v-else class="heatmap-container">
        <DataTable
          :value="heatmapRows"
          responsive-layout="scroll"
          class="heatmap-table"
          :row-class="getHeatmapRowClass"
        >
          <Column header="Phòng ban" style="min-width: 180px">
            <template #body="{ data }">
              <span :class="{ 'font-semibold': data.dept_id === null }">
                {{ data.dept_name || 'Không xác định' }}
              </span>
            </template>
          </Column>
          <Column v-for="m in 12" :key="m" :header="`T${m}`" class="text-right" style="width: 70px">
            <template #body="{ data }">
              <div :class="['heat-cell', data.dept_id === null ? 'font-semibold' : getHeatClass(data.monthly_days[m])]">
                {{ formatNumber(data.monthly_days[m]) || '0' }}
              </div>
            </template>
          </Column>
          <Column header="Tổng năm" class="text-right" style="width: 100px">
            <template #body="{ data }">
              <span class="font-bold">{{ formatNumber(data.annual_total) }}</span>
            </template>
          </Column>
        </DataTable>
      </div>
    </div>

    <!-- Grid: Top 10 Employees & Department Comparison -->
    <div class="half-grid">
      <!-- Section 4: Top 10 nhân viên nghỉ nhiều -->
      <div class="analytics-card no-margin">
        <h3 class="section-title">Top 10 nhân sự nghỉ phép nhiều nhất</h3>
        <DataTable :value="topEmployees?.items" :loading="loading" responsive-layout="scroll">
          <Column header="Hạng" style="width: 60px">
            <template #body="{ data }">
              <span :class="['rank-badge', `rank-badge-${data.rank}`]">{{ data.rank }}</span>
            </template>
          </Column>
          <Column header="Nhân sự" style="min-width: 150px">
            <template #body="{ data }">
              <div class="employee-cell">
                <span class="employee-name">{{ data.employee_name }}</span>
                <span class="employee-code">{{ data.employee_code }}</span>
              </div>
            </template>
          </Column>
          <Column field="dept_name" header="Phòng ban" />
          <Column header="Ngày nghỉ / Được cấp" class="text-right">
            <template #body="{ data }">
              <strong>{{ formatNumber(data.total_days_taken) }}</strong>
              <span class="allocated-span"> / {{ formatNumber(data.total_entitled) }} ngày</span>
            </template>
          </Column>
          <Column header="Tỷ lệ sử dụng" style="width: 120px">
            <template #body="{ data }">
              <div class="progress-cell">
                <ProgressBar :value="data.usage_rate" :show-value="false" style="height: 6px" />
                <span class="progress-value">{{ data.usage_rate }}%</span>
              </div>
            </template>
          </Column>
          <template #empty>
            <div class="empty-state p-4">Không có dữ liệu xếp hạng</div>
          </template>
        </DataTable>
      </div>

      <!-- Section 5: So sánh phòng ban -->
      <div class="analytics-card no-margin">
        <h3 class="section-title">Tỷ lệ nghỉ giữa các phòng ban</h3>
        <DataTable :value="deptComparison?.items" :loading="loading" responsive-layout="scroll">
          <Column field="dept_name" header="Phòng ban" style="min-width: 150px">
            <template #body="{ data }">
              {{ data.dept_name || 'Không xác định' }}
            </template>
          </Column>
          <Column field="employee_count" header="Số NV" class="text-right" style="width: 70px" />
          <Column header="Tổng ngày" class="text-right" style="width: 90px">
            <template #body="{ data }">
              <strong>{{ formatNumber(data.total_days_taken) }}</strong>
            </template>
          </Column>
          <Column header="TB/NV" class="text-right" style="width: 80px">
            <template #body="{ data }">
              {{ formatNumber(data.avg_days_per_employee) }}
            </template>
          </Column>
          <Column header="Tỷ lệ sử dụng" style="width: 120px">
            <template #body="{ data }">
              <div class="progress-cell">
                <ProgressBar :value="data.usage_rate" :show-value="false" style="height: 6px" />
                <span class="progress-value">{{ data.usage_rate }}%</span>
              </div>
            </template>
          </Column>
          <template #empty>
            <div class="empty-state p-4">Không có dữ liệu so sánh</div>
          </template>
        </DataTable>
      </div>
    </div>

    <!-- Section 6: Cảnh báo carryover sắp hết hạn -->
    <div class="analytics-card">
      <div class="card-header-row">
        <h3 class="section-title">Cảnh báo tồn phép sắp hết hạn</h3>
        <div class="card-header-actions">
          <span class="threshold-label">Ngưỡng cảnh báo:</span>
          <Select
            v-model="filters.expire_days"
            :options="expireDaysOptions"
            option-label="label"
            option-value="value"
            style="width: 140px"
            @change="loadExpiringBalance"
          />
        </div>
      </div>
      <DataTable
        :value="expiringBalance?.items"
        :loading="loading"
        responsive-layout="scroll"
        :row-class="getExpiringRowClass"
      >
        <Column header="Mã NV" field="employee_code" style="width: 100px" />
        <Column header="Nhân sự" field="employee_name" style="min-width: 150px" />
        <Column header="Phòng ban" field="dept_name" />
        <Column header="Loại phép" field="leave_type_name" />
        <Column header="Ngày chuyển dư" class="text-right" style="width: 130px">
          <template #body="{ data }">
            {{ formatNumber(data.carryover_days) }} ngày
          </template>
        </Column>
        <Column header="Tồn phép còn lại" class="text-right" style="width: 130px">
          <template #body="{ data }">
            <strong class="critical-text">{{ formatNumber(data.remaining_days) }} ngày</strong>
          </template>
        </Column>
        <Column header="Ngày hết hạn" style="width: 120px">
          <template #body="{ data }">
            {{ formatDate(data.carryover_expires) }}
          </template>
        </Column>
        <Column header="Hết hạn sau" style="width: 130px">
          <template #body="{ data }">
            <span :class="['days-badge', data.days_until_expire <= 7 ? 'critical' : 'warning']">
              Còn {{ data.days_until_expire }} ngày
            </span>
          </template>
        </Column>
        <template #empty>
          <div class="empty-state p-4">Không có nhân sự nào sắp hết hạn tồn phép trong {{ filters.expire_days }} ngày tới</div>
        </template>
      </DataTable>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import Button from 'primevue/button'
import Select from 'primevue/select'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ProgressBar from 'primevue/progressbar'
import Skeleton from 'primevue/skeleton'
import vTooltip from 'primevue/tooltip'

import leaveAnalyticsService, {
  type LeaveAnalyticsSummary,
  type LeaveByTypeReport,
  type MonthlyHeatmapReport,
  type TopEmployeesReport,
  type DeptComparisonReport,
  type ExpiringBalanceReport,
} from '@/services/leaveAnalyticsService'
import departmentService, { type DepartmentRead } from '@/services/departmentService'
import otherBusinessCatalogService, { type LeaveTypeRead } from '@/services/otherBusinessCatalogService'

// ── Filters & Configuration ──────────────────────────────────────────────────
const now = new Date()
const currentYear = now.getFullYear()

const yearOptions = Array.from({ length: 7 }, (_, i) => {
  const y = currentYear - 3 + i
  return { label: `Năm ${y}`, value: y }
})

const expireDaysOptions = [
  { label: '30 ngày tới', value: 30 },
  { label: '60 ngày tới', value: 60 },
  { label: '90 ngày tới', value: 90 },
]

const filters = reactive({
  year: currentYear,
  department_id: null as number | null,
  leave_type_id: null as number | null,
  expire_days: 30,
})

// ── State ─────────────────────────────────────────────────────────────────────
const loading = ref(false)
const exporting = ref(false)
const errorMsg = ref('')

const departments = ref<DepartmentRead[]>([])
const leaveTypes = ref<LeaveTypeRead[]>([])

const summary = ref<LeaveAnalyticsSummary | null>(null)
const byType = ref<LeaveByTypeReport | null>(null)
const heatmap = ref<MonthlyHeatmapReport | null>(null)
const topEmployees = ref<TopEmployeesReport | null>(null)
const deptComparison = ref<DeptComparisonReport | null>(null)
const expiringBalance = ref<ExpiringBalanceReport | null>(null)

// ── Computed Heatmap Rows ─────────────────────────────────────────────────────
const heatmapRows = computed(() => {
  if (!heatmap.value) return []
  const rows = [...heatmap.value.departments]
  if (heatmap.value.departments.length > 0) {
    const companyAnnualTotal = Object.values(heatmap.value.company_monthly).reduce((a, b) => a + b, 0)
    rows.push({
      dept_id: null,
      dept_name: 'TỔNG CÔNG TY',
      monthly_days: heatmap.value.company_monthly,
      annual_total: companyAnnualTotal,
    })
  }
  return rows
})

// ── API Load Functions ────────────────────────────────────────────────────────
async function loadMeta() {
  try {
    const [deptRes, ltRes] = await Promise.all([
      departmentService.getList(true),
      otherBusinessCatalogService.lookupLeaveTypes({ limit: 100 }),
    ])
    departments.value = deptRes.data
    leaveTypes.value = ltRes.data
  } catch (e) {
    console.error('Lỗi tải danh mục filter', e)
  }
}

async function loadData() {
  loading.value = true
  errorMsg.value = ''
  
  const params = {
    year: filters.year,
    department_id: filters.department_id,
    leave_type_id: filters.leave_type_id,
  }

  try {
    const [summaryRes, byTypeRes, heatmapRes, topRes, compRes] = await Promise.all([
      leaveAnalyticsService.getAnalyticsSummary(params),
      leaveAnalyticsService.getByType({ year: filters.year, department_id: filters.department_id }),
      leaveAnalyticsService.getMonthlyHeatmap({ year: filters.year }),
      leaveAnalyticsService.getTopEmployees(params),
      leaveAnalyticsService.getDeptComparison({ year: filters.year }),
    ])

    summary.value = summaryRes.data
    byType.value = byTypeRes.data
    heatmap.value = heatmapRes.data
    topEmployees.value = topRes.data
    deptComparison.value = compRes.data

    await loadExpiringBalance()
  } catch (e) {
    errorMsg.value = 'Không thể kết nối đến máy chủ. Vui lòng tải lại trang.'
    console.error('Lỗi tải dữ liệu phân tích', e)
  } finally {
    loading.value = false
  }
}

async function loadExpiringBalance() {
  try {
    const res = await leaveAnalyticsService.getExpiringBalance({
      year: filters.year,
      department_id: filters.department_id,
      expire_days: filters.expire_days,
    })
    expiringBalance.value = res.data
  } catch (e) {
    console.error('Lỗi tải cảnh báo tồn phép hết hạn', e)
  }
}

function resetFilters() {
  filters.year = currentYear
  filters.department_id = null
  filters.leave_type_id = null
  filters.expire_days = 30
  loadData()
}

// ── Export Excel ──────────────────────────────────────────────────────────────
async function exportExcel() {
  exporting.value = true
  try {
    const url = leaveAnalyticsService.exportAnalyticsUrl({
      year: filters.year,
      department_id: filters.department_id,
    })
    const a = document.createElement('a')
    a.href = url
    a.click()
  } catch (e) {
    console.error('Lỗi xuất báo cáo excel', e)
  } finally {
    exporting.value = false
  }
}

// ── Helpers & Cell Styles ─────────────────────────────────────────────────────
function formatNumber(val: number | undefined): string {
  if (val === undefined || val === null) return '—'
  return new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 1 }).format(val)
}

function formatInteger(val: number | undefined): string {
  if (val === undefined || val === null) return '—'
  return new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 }).format(val)
}

function formatDate(val: string): string {
  if (!val) return '—'
  const date = new Date(val)
  if (Number.isNaN(date.getTime())) return val
  return new Intl.DateTimeFormat('vi-VN').format(date)
}

function getHeatClass(days: number | undefined): string {
  if (!days || days <= 0) return 'heat-0'
  if (days <= 5) return 'heat-1'
  if (days <= 10) return 'heat-2'
  if (days <= 20) return 'heat-3'
  return 'heat-4'
}

function getHeatmapRowClass(data: any) {
  return data.dept_id === null ? 'font-bold bg-gray-100 dark:bg-gray-800' : ''
}


function getExpiringRowClass(data: any) {
  if (data.days_until_expire <= 7) return 'expiry-critical'
  if (data.days_until_expire <= 30) return 'expiry-warning'
  return ''
}

// ── Lifecycle Init ────────────────────────────────────────────────────────────
onMounted(async () => {
  await loadMeta()
  await loadData()
})
</script>

<style scoped>
.leave-analytics-view {
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
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
}

.half-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.25rem;
}

@media (max-width: 1024px) {
  .kpi-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .half-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .kpi-grid {
    grid-template-columns: 1fr;
  }
}

/* Premium Analytics Card */
.analytics-card {
  padding: 1.5rem;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 10px;
  box-shadow: var(--l-shadow);
}

.analytics-card.no-margin {
  margin-top: 0;
}

/* Card Header row */
.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.25rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.card-header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.threshold-label {
  font-size: 0.875rem;
  color: var(--l-text-muted);
}

/* KPI Cards styling */
.kpi-card {
  background: var(--l-surface);
  border: 1px solid var(--l-border);
  border-radius: 16px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  box-shadow: var(--l-shadow);
}
.kpi-card.border-blue { border-left: 4px solid var(--p-blue-500); }
.kpi-card.border-green { border-left: 4px solid var(--p-green-500); }
.kpi-card.border-orange { border-left: 4px solid var(--p-orange-500); }
.kpi-card.border-red { border-left: 4px solid var(--p-red-500); }

.kpi-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.kpi-card-title {
  color: var(--l-text-muted);
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.kpi-card-header i {
  font-size: 1.1rem;
  padding: 0.4rem;
  border-radius: 8px;
  background: color-mix(in srgb, var(--l-border) 40%, transparent);
}
.kpi-icon-blue { color: var(--p-blue-500); }
.kpi-icon-green { color: var(--p-green-500); }
.kpi-icon-orange { color: var(--p-orange-500); }
.kpi-icon-red { color: var(--p-red-500); }

.kpi-card-value {
  font-size: 1.95rem;
  font-weight: 800;
  line-height: 1;
  color: var(--l-text);
  margin-top: 0.25rem;
}
.kpi-card-sub {
  color: var(--l-text-muted);
  font-size: 0.82rem;
}

/* Custom Bar Chart styling */
.custom-bar-chart {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.custom-bar-chart-row {
  display: grid;
  grid-template-columns: minmax(150px, 1.5fr) minmax(0, 3fr) minmax(130px, 1.2fr);
  gap: 1rem;
  align-items: center;
}
.custom-bar-chart-label {
  display: flex;
  flex-direction: column;
  line-height: 1.35;
}
.custom-bar-chart-caption {
  font-size: 0.78rem;
  color: var(--l-text-muted);
}
.custom-bar-chart-track-wrapper {
  flex: 1;
}
.custom-bar-chart-track {
  height: 1rem;
  border-radius: 999px;
  background: color-mix(in srgb, var(--l-border) 60%, transparent);
  overflow: hidden;
}
.custom-bar-chart-fill {
  height: 100%;
  border-radius: inherit;
  transition: width 0.3s ease;
}
.custom-bar-chart-value {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  line-height: 1.35;
}
.custom-bar-chart-subvalue {
  font-size: 0.78rem;
  color: var(--l-text-muted);
}

/* Heatmap cell styling */
.heatmap-container {
  overflow-x: auto;
}
.heatmap-table {
  min-width: 800px;
}
.heat-cell {
  width: 100%;
  height: 100%;
  min-height: 2.25rem;
  padding: 0.35rem 0.5rem;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  border-radius: 4px;
  transition: background-color 0.2s;
  font-variant-numeric: tabular-nums;
}

/* Inner cell helpers */
.progress-cell {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.progress-value {
  font-size: 0.75rem;
  text-align: right;
  font-weight: 500;
}
.employee-cell {
  display: flex;
  flex-direction: column;
}
.employee-name {
  font-weight: 500;
}
.employee-code {
  font-size: 0.75rem;
  color: var(--l-text-muted);
}
.allocated-span {
  font-size: 0.75rem;
  color: var(--l-text-muted);
}
.critical-text {
  color: var(--p-red-600);
}
html.dark-mode .critical-text {
  color: var(--p-red-400);
}

/* Top Employees styling */
.rank-badge {
  display: inline-flex;
  width: 1.6rem;
  height: 1.6rem;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 700;
  background: var(--l-surface-variant, #f1f5f9);
  color: var(--l-text, #334155);
}

/* Rank 1 (Đỏ - Cảnh báo cao nhất) */
.rank-badge.rank-badge-1 {
  background: #ef4444;
  color: #ffffff;
}
html.dark-mode .rank-badge.rank-badge-1 {
  background: #fca5a5;
  color: #7f1d1d;
}

/* Rank 2 (Cam - Cảnh báo vừa) */
.rank-badge.rank-badge-2 {
  background: #f97316;
  color: #ffffff;
}
html.dark-mode .rank-badge.rank-badge-2 {
  background: #fed7aa;
  color: #7c2d12;
}

/* Rank 3 (Vàng - Cảnh báo thấp) */
.rank-badge.rank-badge-3 {
  background: #eab308;
  color: #ffffff;
}
html.dark-mode .rank-badge.rank-badge-3 {
  background: #fde68a;
  color: #78350f;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .custom-bar-chart-row {
    grid-template-columns: 1fr;
    gap: 0.25rem;
  }
  .custom-bar-chart-value {
    align-items: flex-start;
    margin-bottom: 0.5rem;
  }
}
</style>
