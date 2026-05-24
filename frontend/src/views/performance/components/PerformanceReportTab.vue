<template>
  <div class="rpt-tab">
    <!-- Toolbar -->
    <div class="rpt-toolbar">
      <div class="rpt-filters">
        <Select
          v-model="year"
          :options="yearOptions"
          option-label="label"
          option-value="value"
          class="rpt-year-select"
        />
        <Select
          v-model="filterDeptId"
          :options="deptOptions"
          option-label="label"
          option-value="value"
          placeholder="Tất cả phòng ban"
          show-clear
          class="rpt-dept-select"
        />
      </div>
      <div class="rpt-actions">
        <Button label="Xem báo cáo" icon="pi pi-search" @click="loadAll" :loading="loading" />
        <Button label="Xuất Excel" icon="pi pi-file-excel" severity="success" outlined @click="exportExcel" :loading="exporting" />
      </div>
    </div>

    <!-- Summary cards -->
    <div class="rpt-cards" v-if="dist">
      <div class="rpt-card">
        <div class="rpt-card-value">{{ dist.total_reviewed }}</div>
        <div class="rpt-card-label">Đã đánh giá</div>
      </div>
      <div class="rpt-card">
        <div class="rpt-card-value">{{ dist.coverage_rate }}%</div>
        <div class="rpt-card-label">Tỷ lệ bao phủ</div>
      </div>
      <div class="rpt-card rpt-card-good">
        <div class="rpt-card-value">{{ topCount }}</div>
        <div class="rpt-card-label">Xuất sắc + Tốt</div>
      </div>
      <div class="rpt-card rpt-card-warn">
        <div class="rpt-card-value">{{ lowCount }}</div>
        <div class="rpt-card-label">Cần cải thiện</div>
      </div>
    </div>

    <div class="rpt-body" v-if="dist">
      <!-- Rating distribution -->
      <div class="rpt-section">
        <div class="rpt-section-title">Phân phối xếp loại — {{ year }}</div>
        <DataTable :value="dist.distribution" size="small" class="rpt-table">
          <Column header="Xếp loại" field="rating_label">
            <template #body="{ data }">
              <Tag :severity="ratingColor(data.rating)" :value="data.rating_label" />
            </template>
          </Column>
          <Column header="Số NV" field="count" header-style="text-align:center" style="text-align:center;width:90px" />
          <Column header="Tỷ lệ (%)" header-style="text-align:center" style="text-align:center;width:110px">
            <template #body="{ data }">{{ data.percentage.toFixed(1) }}%</template>
          </Column>
        </DataTable>
      </div>

      <!-- Department KPI -->
      <div class="rpt-section">
        <div class="rpt-section-title">KPI theo phòng ban — {{ year }}</div>
        <DataTable :value="deptStats" size="small" class="rpt-table" :loading="loading">
          <Column header="Phòng ban" field="department_name">
            <template #body="{ data }">{{ data.department_name || 'Chưa phân công' }}</template>
          </Column>
          <Column header="Số NV" field="employee_count" header-style="text-align:center" style="text-align:center;width:80px" />
          <Column header="Điểm TB" header-style="text-align:center" style="text-align:center;width:90px">
            <template #body="{ data }">
              <span v-if="data.avg_score" :class="scoreClass(parseFloat(data.avg_score))">
                {{ parseFloat(data.avg_score).toFixed(1) }}
              </span>
              <span v-else class="rpt-muted">—</span>
            </template>
          </Column>
          <Column header="Thấp nhất" header-style="text-align:center" style="text-align:center;width:100px">
            <template #body="{ data }">{{ data.min_score ? parseFloat(data.min_score).toFixed(1) : '—' }}</template>
          </Column>
          <Column header="Cao nhất" header-style="text-align:center" style="text-align:center;width:100px">
            <template #body="{ data }">{{ data.max_score ? parseFloat(data.max_score).toFixed(1) : '—' }}</template>
          </Column>
          <Column header="Lượt nhập" field="months_data_count" header-style="text-align:center" style="text-align:center;width:90px" />
        </DataTable>
      </div>

      <!-- Monthly trend -->
      <div class="rpt-section">
        <div class="rpt-section-title-row">
          <span class="rpt-section-title">Xu hướng KPI theo tháng — {{ year }}</span>
          <Select
            v-model="trendDeptId"
            :options="deptOptions"
            option-label="label"
            option-value="value"
            placeholder="Toàn công ty"
            show-clear
            class="rpt-trend-dept"
            @change="loadTrend"
          />
        </div>
        <DataTable :value="trend?.points ?? []" size="small" class="rpt-table rpt-trend-table" :loading="loadingTrend">
          <Column header="Tháng" field="month" style="width:100px">
            <template #body="{ data }">Tháng {{ data.month }}</template>
          </Column>
          <Column header="Điểm TB" style="width:120px">
            <template #body="{ data }">
              <span v-if="data.avg_score" :class="scoreClass(parseFloat(data.avg_score))">
                {{ parseFloat(data.avg_score).toFixed(1) }}
              </span>
              <span v-else class="rpt-muted">—</span>
            </template>
          </Column>
          <Column header="Số NV có KPI" field="employee_count" style="width:120px" />
        </DataTable>
      </div>
    </div>

    <div v-else-if="!loading" class="rpt-empty">
      <i class="pi pi-chart-bar" />
      <span>Chọn năm và nhấn "Xem báo cáo"</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import performanceService, {
  type RatingDistributionReport,
  type DepartmentKpiStat,
  type MonthlyKpiTrend,
} from '@/services/performanceService'
import departmentService from '@/services/departmentService'

const toast = useToast()

const currentYear = new Date().getFullYear()
const year = ref(currentYear)
const filterDeptId = ref<number | null>(null)
const trendDeptId = ref<number | null>(null)

const yearOptions = Array.from({ length: 6 }, (_, i) => {
  const y = currentYear - i
  return { label: `Năm ${y}`, value: y }
})

const deptOptions = ref<{ label: string; value: number }[]>([])

const loading = ref(false)
const loadingTrend = ref(false)
const exporting = ref(false)

const dist = ref<RatingDistributionReport | null>(null)
const deptStats = ref<DepartmentKpiStat[]>([])
const trend = ref<MonthlyKpiTrend | null>(null)

const topCount = computed(() => {
  if (!dist.value) return 0
  return dist.value.distribution
    .filter(d => d.rating === 'xuat_sac' || d.rating === 'tot')
    .reduce((s, d) => s + d.count, 0)
})
const lowCount = computed(() => {
  if (!dist.value) return 0
  return dist.value.distribution.find(d => d.rating === 'can_cai_thien')?.count ?? 0
})

function ratingColor(rating: string): 'success' | 'info' | 'warn' | 'danger' | undefined {
  if (rating === 'xuat_sac') return 'success'
  if (rating === 'tot') return 'info'
  if (rating === 'dat') return 'warn'
  return 'danger'
}

function scoreClass(score: number) {
  if (score >= 95) return 'perf-score-high'
  if (score >= 85) return 'perf-score-mid'
  return 'perf-score-low'
}

async function loadAll() {
  loading.value = true
  try {
    const [distRes, deptRes] = await Promise.all([
      performanceService.getRatingDistribution(year.value),
      performanceService.getDepartmentKpi(year.value, null, filterDeptId.value),
    ])
    dist.value = distRes.data
    deptStats.value = deptRes.data
    await loadTrend()
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể tải báo cáo', life: 3000 })
  } finally {
    loading.value = false
  }
}

async function loadTrend() {
  loadingTrend.value = true
  try {
    const res = await performanceService.getMonthlyTrend(year.value, trendDeptId.value)
    trend.value = res.data
  } catch {
    // silent
  } finally {
    loadingTrend.value = false
  }
}

async function exportExcel() {
  exporting.value = true
  try {
    const res = await performanceService.exportReport(year.value)
    const url = URL.createObjectURL(new Blob([res.data]))
    const a = document.createElement('a')
    a.href = url
    a.download = `bao_cao_hieu_suat_${year.value}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Xuất Excel thất bại', life: 3000 })
  } finally {
    exporting.value = false
  }
}

onMounted(async () => {
  try {
    const res = await departmentService.getList(true)
    deptOptions.value = res.data.map(d => ({ label: d.name, value: d.id }))
  } catch { /* ignore */ }
  await loadAll()
})
</script>
