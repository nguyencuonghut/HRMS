<template>
  <div class="rc-detail">
    <RecruitmentBreadcrumb :crumbs="[
      { label: 'Yêu cầu tuyển dụng', to: '/recruitment/jr' },
      { label: 'Báo cáo tuyển dụng' },
    ]" />

    <!-- Toolbar -->
    <div class="rc-detail-header">
      <div class="rc-header-left">
        <span class="rc-jr-code">Báo cáo tuyển dụng</span>
      </div>
      <div class="rc-header-right">
        <Button
          label="Xem báo cáo"
          icon="pi pi-chart-bar"
          :loading="loading"
          @click="loadAll"
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

    <!-- Filter bar -->
    <div class="section-card" style="margin-top: 0.75rem">
      <div style="display: flex; gap: 1rem; flex-wrap: wrap; align-items: flex-end">
        <div>
          <label class="rc-filter-label">Từ ngày</label>
          <DatePicker v-model="startDate" date-format="dd/mm/yy" show-icon />
        </div>
        <div>
          <label class="rc-filter-label">Đến ngày</label>
          <DatePicker v-model="endDate" date-format="dd/mm/yy" show-icon />
        </div>
        <div>
          <label class="rc-filter-label">Năm (xu hướng tháng)</label>
          <InputNumber v-model="selectedYear" :min="2020" :max="2100" :use-grouping="false" style="width: 100px" />
        </div>
      </div>
    </div>

    <div v-if="!hasLoaded" class="section-card" style="margin-top: 0.75rem">
      <div class="rc-empty">Chọn khoảng thời gian và nhấn "Xem báo cáo"</div>
    </div>

    <template v-else>
      <!-- Summary KPI Cards -->
      <div class="section-stack" style="margin-top: 0.75rem" v-if="summary">
        <div class="section-card">
          <div class="section-header">
            <span class="section-title">Tổng quan kỳ {{ formatDate(summary.period_start) }} – {{ formatDate(summary.period_end) }}</span>
          </div>
          <div class="rc-kpi-grid">
            <div class="rc-kpi-card">
              <div class="rc-kpi-label">Tổng JR</div>
              <div class="rc-kpi-value">{{ summary.total_jr }}</div>
            </div>
            <div class="rc-kpi-card">
              <div class="rc-kpi-label">Lượt ứng tuyển</div>
              <div class="rc-kpi-value">{{ summary.total_applications }}</div>
            </div>
            <div class="rc-kpi-card">
              <div class="rc-kpi-label">Đã tuyển</div>
              <div class="rc-kpi-value rc-kpi-success">{{ summary.total_hired }}</div>
            </div>
            <div class="rc-kpi-card">
              <div class="rc-kpi-label">T/g tuyển TB</div>
              <div class="rc-kpi-value">{{ summary.avg_time_to_hire != null ? summary.avg_time_to_hire + ' ngày' : '—' }}</div>
            </div>
            <div class="rc-kpi-card">
              <div class="rc-kpi-label">T/g lấp chỗ TB</div>
              <div class="rc-kpi-value">{{ summary.avg_time_to_fill != null ? summary.avg_time_to_fill + ' ngày' : '—' }}</div>
            </div>
            <div class="rc-kpi-card">
              <div class="rc-kpi-label">Tỷ lệ chấp nhận offer</div>
              <div class="rc-kpi-value">{{ summary.offer_acceptance_rate != null ? summary.offer_acceptance_rate + '%' : '—' }}</div>
            </div>
            <div class="rc-kpi-card">
              <div class="rc-kpi-label">Chi phí / tuyển dụng</div>
              <div class="rc-kpi-value">{{ fmtVnd(summary.cost_per_hire) }}</div>
            </div>
            <div class="rc-kpi-card">
              <div class="rc-kpi-label">Tỷ lệ vượt thử việc</div>
              <div class="rc-kpi-value rc-muted">{{ summary.probation_pass_rate != null ? summary.probation_pass_rate + '%' : 'Chưa có dữ liệu' }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Funnel -->
      <div class="section-card" v-if="funnel">
        <div class="section-header">
          <span class="section-title">Phễu tuyển dụng</span>
        </div>
        <DataTable :value="funnel.stages" size="small" striped-rows>
          <Column field="stage_label" header="Giai đoạn" />
          <Column field="count" header="Số lượt" style="width: 110px; text-align: right">
            <template #body="{ data }">
              <Badge :value="String(data.count)" :severity="data.count > 0 ? 'info' : 'secondary'" />
            </template>
          </Column>
          <Column field="conversion_rate" header="Tỷ lệ chuyển đổi" style="width: 170px">
            <template #body="{ data }">
              <span v-if="data.conversion_rate != null" :class="convClass(data.conversion_rate)">
                {{ data.conversion_rate }}%
              </span>
              <span v-else class="rc-muted">—</span>
            </template>
          </Column>
        </DataTable>
      </div>

      <!-- Channel effectiveness -->
      <div class="section-card" v-if="channels.length">
        <div class="section-header">
          <span class="section-title">Hiệu quả kênh tuyển dụng</span>
        </div>
        <DataTable :value="channels" size="small" striped-rows>
          <Column field="channel_name" header="Kênh" />
          <Column field="total_candidates" header="Ứng viên" style="width: 100px" />
          <Column field="hired_count" header="Đã tuyển" style="width: 100px">
            <template #body="{ data }">
              <Badge :value="String(data.hired_count)" :severity="data.hired_count > 0 ? 'success' : 'secondary'" />
            </template>
          </Column>
          <Column field="hire_rate" header="Tỷ lệ tuyển" style="width: 120px">
            <template #body="{ data }">{{ data.hire_rate }}%</template>
          </Column>
        </DataTable>
      </div>

      <!-- Department breakdown -->
      <div class="section-card" v-if="departments.length">
        <div class="section-header">
          <span class="section-title">Theo phòng ban</span>
        </div>
        <DataTable :value="departments" size="small" striped-rows>
          <Column field="department_name" header="Phòng ban" />
          <Column field="total_jr" header="Tổng JR" style="width: 80px" />
          <Column field="open_jr" header="Đang tuyển" style="width: 100px" />
          <Column field="hired_count" header="Đã tuyển" style="width: 90px">
            <template #body="{ data }">
              <Badge :value="String(data.hired_count)" :severity="data.hired_count > 0 ? 'success' : 'secondary'" />
            </template>
          </Column>
          <Column field="avg_time_to_hire" header="T/g tuyển TB" style="width: 120px">
            <template #body="{ data }">
              {{ data.avg_time_to_hire != null ? data.avg_time_to_hire + ' ngày' : '—' }}
            </template>
          </Column>
          <Column field="offer_acceptance_rate" header="OAR" style="width: 80px">
            <template #body="{ data }">
              {{ data.offer_acceptance_rate != null ? data.offer_acceptance_rate + '%' : '—' }}
            </template>
          </Column>
          <Column field="cost_per_hire" header="Chi phí/người" style="width: 130px">
            <template #body="{ data }">{{ fmtVnd(data.cost_per_hire) }}</template>
          </Column>
        </DataTable>
      </div>

      <!-- Monthly trend -->
      <div class="section-card" v-if="timeMetrics">
        <div class="section-header">
          <span class="section-title">Xu hướng tháng — Năm {{ timeMetrics.year }}</span>
        </div>
        <DataTable :value="timeMetrics.monthly" size="small" striped-rows>
          <Column header="Tháng" style="width: 90px">
            <template #body="{ data }">T{{ String(data.month).padStart(2, '0') }}/{{ data.year }}</template>
          </Column>
          <Column field="applications_count" header="Lượt ứng tuyển" style="width: 140px" />
          <Column field="hired_count" header="Đã tuyển" style="width: 90px">
            <template #body="{ data }">
              <Badge v-if="data.hired_count > 0" :value="String(data.hired_count)" severity="success" />
              <span v-else class="rc-muted">0</span>
            </template>
          </Column>
          <Column field="avg_time_to_hire" header="T/g tuyển TB" style="width: 130px">
            <template #body="{ data }">
              {{ data.avg_time_to_hire != null ? data.avg_time_to_hire + ' ngày' : '—' }}
            </template>
          </Column>
          <Column field="avg_time_to_fill" header="T/g lấp chỗ TB" style="width: 140px">
            <template #body="{ data }">
              {{ data.avg_time_to_fill != null ? data.avg_time_to_fill + ' ngày' : '—' }}
            </template>
          </Column>
        </DataTable>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Badge from 'primevue/badge'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import InputNumber from 'primevue/inputnumber'
import { useToast } from 'primevue/usetoast'

import {
  recruitmentReportService,
  type RecruitmentSummaryReport,
  type FunnelReport,
  type ChannelEffectivenessItem,
  type DepartmentRecruitmentStat,
  type TimeMetricsReport,
} from '@/services/recruitmentService'
import RecruitmentBreadcrumb from './components/RecruitmentBreadcrumb.vue'

const toast = useToast()

// Defaults: current year Jan 1 → today
const now = new Date()
const startDate = ref<Date>(new Date(now.getFullYear(), 0, 1))
const endDate   = ref<Date>(now)
const selectedYear = ref(now.getFullYear())

const loading   = ref(false)
const exporting = ref(false)
const hasLoaded = ref(false)

const summary     = ref<RecruitmentSummaryReport | null>(null)
const funnel      = ref<FunnelReport | null>(null)
const channels    = ref<ChannelEffectivenessItem[]>([])
const departments = ref<DepartmentRecruitmentStat[]>([])
const timeMetrics = ref<TimeMetricsReport | null>(null)

function fmtDate(d: Date): string {
  return d.toISOString().slice(0, 10)
}

function formatDate(s: string): string {
  return new Date(s).toLocaleDateString('vi-VN')
}

function fmtVnd(val: number | null): string {
  if (val == null) return '—'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(val)
}

function convClass(rate: number): string {
  if (rate >= 50) return 'rc-kpi-success'
  if (rate >= 25) return ''
  return 'rc-deadline-near'
}

async function loadAll() {
  if (!startDate.value || !endDate.value) {
    toast.add({ severity: 'warn', summary: 'Thiếu thông tin', detail: 'Vui lòng chọn khoảng thời gian', life: 3000 })
    return
  }
  loading.value = true
  const params = {
    start_date: fmtDate(startDate.value),
    end_date:   fmtDate(endDate.value),
  }
  try {
    const [sum, fun, ch, dept, tm] = await Promise.all([
      recruitmentReportService.getSummary(params),
      recruitmentReportService.getFunnel(params),
      recruitmentReportService.getChannelEffectiveness(params),
      recruitmentReportService.getDepartmentBreakdown(params),
      recruitmentReportService.getTimeMetrics({ year: selectedYear.value }),
    ])
    summary.value     = sum
    funnel.value      = fun
    channels.value    = ch
    departments.value = dept
    timeMetrics.value = tm
    hasLoaded.value   = true
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể tải báo cáo', life: 4000 })
  } finally {
    loading.value = false
  }
}

async function exportExcel() {
  if (!startDate.value || !endDate.value) {
    toast.add({ severity: 'warn', summary: 'Thiếu thông tin', detail: 'Vui lòng chọn khoảng thời gian', life: 3000 })
    return
  }
  exporting.value = true
  try {
    const blob = await recruitmentReportService.exportExcel({
      start_date: fmtDate(startDate.value),
      end_date:   fmtDate(endDate.value),
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `BaoCaoTuyenDung_${fmtDate(startDate.value)}_${fmtDate(endDate.value)}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể xuất Excel', life: 4000 })
  } finally {
    exporting.value = false
  }
}
</script>
