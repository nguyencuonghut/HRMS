<template>
  <div class="prob-report">
    <!-- Breadcrumb -->
    <nav class="ob-breadcrumb">
      <RouterLink :to="breadcrumbRootTo">{{ breadcrumbRootLabel }}</RouterLink>
      <i class="pi pi-chevron-right" />
      <span>{{ reportTitle }}</span>
    </nav>

    <!-- Filter toolbar -->
    <div class="toolbar">
      <span class="ob-label" style="white-space:nowrap">Lọc theo kỳ:</span>
      <DatePicker
        v-model="filterFrom"
        date-format="dd/mm/yy"
        placeholder="Từ ngày"
        class="toolbar-filter"
        style="width: 145px"
      />
      <span class="ob-muted">—</span>
      <DatePicker
        v-model="filterTo"
        date-format="dd/mm/yy"
        placeholder="Đến ngày"
        class="toolbar-filter"
        style="width: 145px"
      />
      <InputText
        v-model="filterKeyword"
        placeholder="Tên hoặc mã nhân viên..."
        class="toolbar-filter"
        style="width: 210px"
        @keydown.enter="loadAll"
      />
      <Select
        v-model="filterDeptId"
        :options="departments"
        option-label="name"
        option-value="id"
        placeholder="Tất cả phòng ban"
        show-clear
        class="toolbar-filter"
        style="width: 190px"
      />
      <Button
        label="Xem báo cáo"
        icon="pi pi-search"
        :loading="loadingAny"
        v-tooltip.bottom="'Lọc theo kỳ áp dụng cho: bảng nhân viên, checklist và tỷ lệ vượt thử việc. Để trống để xem tất cả.'"
        @click="loadAll"
      />
      <Button
        icon="pi pi-refresh"
        severity="secondary"
        text
        rounded
        v-tooltip.bottom="'Làm mới'"
        :disabled="loadingAny"
        @click="resetFilters"
      />
      <div style="flex:1" />
      <Button
        label="Xuất Excel"
        icon="pi pi-file-excel"
        severity="success"
        outlined
        :disabled="!hasDateRange"
        :loading="isExporting"
        @click="doExport"
      />
    </div>

    <!-- ── Section 1: KPI Summary Cards ──────────────────────────────────── -->
    <div class="prob-kpi-row">
      <!-- Card 1: Khi không có kỳ → đang thử việc real-time; khi có kỳ → tổng trong kỳ -->
      <div class="prob-kpi-card">
        <div class="prob-kpi-value prob-kpi-primary">
          {{ hasDateRange ? (historyReport?.total ?? '—') : (activeProbation?.total ?? '—') }}
        </div>
        <div class="prob-kpi-label">{{ hasDateRange ? 'Thử việc trong kỳ' : 'Đang thử việc' }}</div>
      </div>
      <!-- Card 2: Khi không có kỳ → ngày còn lại TB real-time; khi có kỳ → số người vượt -->
      <div class="prob-kpi-card">
        <div class="prob-kpi-value prob-kpi-info">
          {{ hasDateRange ? (passRate?.overall?.passed ?? '—') : (avgDaysRemaining !== null ? avgDaysRemaining : '—') }}
        </div>
        <div class="prob-kpi-label">{{ hasDateRange ? 'Đã vượt trong kỳ' : 'Ngày còn lại TB' }}</div>
      </div>
      <!-- Card 3: Tỷ lệ vượt — luôn theo effectiveDates() -->
      <div class="prob-kpi-card">
        <div class="prob-kpi-value prob-kpi-success">
          {{ passRate?.overall?.pass_rate !== null && passRate?.overall?.pass_rate !== undefined
            ? passRate.overall.pass_rate.toFixed(1) + '%' : '—' }}
        </div>
        <div class="prob-kpi-label">Tỷ lệ vượt thử việc</div>
      </div>
      <!-- Card 4: Hội nhập TB — luôn theo effectiveDates() -->
      <div class="prob-kpi-card">
        <div class="prob-kpi-value prob-kpi-warn">
          {{ avgChecklistPct !== null ? avgChecklistPct.toFixed(1) + '%' : '—' }}
        </div>
        <div class="prob-kpi-label">Hội nhập hoàn thành TB</div>
      </div>
    </div>

    <!-- ── Section 2: Nhân viên thử việc trong kỳ ──────────────────────── -->
    <div class="ob-card">
      <div class="prob-section-title">
        <i class="pi pi-users" />
        {{ hasDateRange ? 'Nhân viên thử việc trong kỳ' : 'Tất cả nhân viên thử việc' }}
        <Tag v-if="historyReport" :value="String(historyReport.total)" severity="secondary" />
      </div>
      <DataTable
        :value="historyReport?.items ?? []"
        :loading="loadingHistory"
        size="small"
        striped-rows
        lazy
        :total-records="historyTotal"
        :rows="historyPageSize"
        :first="(historyPage - 1) * historyPageSize"
        paginator
        :rows-per-page-options="[10,20,50]"
        @page="onHistoryPage"
      >
        <template #empty>
          <div class="ob-empty">Không có nhân viên thử việc</div>
        </template>

        <Column header="Nhân viên" min-header-width="160px">
          <template #body="{ data }">
            <div>
              <RouterLink :to="`/employees/${data.employee_id}?tab=probation`" class="prob-emp-link">
                {{ data.employee_name }}
              </RouterLink>
              <Tag :value="data.employee_code" severity="secondary" style="font-size:0.7rem; margin-left:0.4rem" />
            </div>
          </template>
        </Column>

        <Column header="Trạng thái" style="width:130px">
          <template #body="{ data }">
            <Tag
              :value="empStatusLabel(data.employee_status)"
              :severity="empStatusSeverity(data.employee_status)"
            />
          </template>
        </Column>

        <Column field="department_name" header="Phòng ban" style="width:150px">
          <template #body="{ data }">{{ data.department_name ?? '—' }}</template>
        </Column>

        <Column header="Bắt đầu TV" style="width:110px">
          <template #body="{ data }">{{ fmtDate(data.probation_start_date) }}</template>
        </Column>

        <Column header="Kết thúc TV" style="width:110px">
          <template #body="{ data }">{{ fmtDate(data.probation_end_date) }}</template>
        </Column>

        <Column header="Còn lại" style="width:90px">
          <template #body="{ data }">
            <span v-if="data.days_remaining !== null" style="font-size:0.85rem">
              {{ data.days_remaining }}d
            </span>
            <span v-else class="ob-muted">—</span>
          </template>
        </Column>

        <Column header="Hội nhập" style="width:160px">
          <template #body="{ data }">
            <div v-if="data.completion_pct !== null" style="display:flex;align-items:center;gap:0.5rem">
              <ProgressBar :value="data.completion_pct" :show-value="false" style="height:7px;flex:1" />
              <span style="font-size:0.78rem;white-space:nowrap">{{ data.completion_pct.toFixed(0) }}%</span>
            </div>
            <span v-else class="ob-muted">—</span>
          </template>
        </Column>

        <Column header="Đánh giá" style="width:120px">
          <template #body="{ data }">
            <Tag
              :value="evalResultLabel(data.evaluation_result)"
              :severity="evalResultSeverity(data.evaluation_result)"
            />
          </template>
        </Column>

        <Column header="Phiếu ĐG" style="width:110px">
          <template #body="{ data }">
            <span v-if="data.evaluation_status" style="font-size:0.8rem">
              {{ evalStatusLabel(data.evaluation_status) }}
            </span>
            <span v-else class="ob-muted">—</span>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- ── Section 3: Checklist hoàn thành theo phòng ban ───────────────── -->
    <div class="ob-card">
      <div class="prob-section-title">
        <i class="pi pi-clipboard" />
        Tỷ lệ hoàn thành checklist hội nhập theo phòng ban
      </div>
      <DataTable
        :value="checklist?.items ?? []"
        :loading="loadingChecklist"
        size="small"
        striped-rows
      >
        <template #empty><div class="ob-empty">Không có dữ liệu</div></template>

        <Column field="department_name" header="Phòng ban" />
        <Column field="total_checklists" header="Tổng" style="width:80px" />
        <Column field="completed_count" header="Hoàn thành" style="width:100px" />
        <Column header="Tỷ lệ xong" style="width:180px">
          <template #body="{ data }">
            <div style="display:flex;align-items:center;gap:0.5rem">
              <ProgressBar :value="data.completion_rate" :show-value="false" style="height:7px;flex:1" />
              <span style="font-size:0.8rem;white-space:nowrap">{{ data.completion_rate.toFixed(1) }}%</span>
            </div>
          </template>
        </Column>
        <Column header="Tiến độ TB" style="width:180px">
          <template #body="{ data }">
            <div style="display:flex;align-items:center;gap:0.5rem">
              <ProgressBar :value="data.avg_completion_pct" :show-value="false" style="height:7px;flex:1" />
              <span style="font-size:0.8rem;white-space:nowrap">{{ data.avg_completion_pct.toFixed(1) }}%</span>
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- ── Section 4: Tỷ lệ vượt thử việc ──────────────────────────────── -->
    <div class="ob-card">
      <div class="prob-section-title">
        <i class="pi pi-chart-bar" />
        Tỷ lệ vượt thử việc theo phòng ban
      </div>

      <!-- Overall -->
      <div v-if="passRate?.overall" class="prob-overall-row">
        <div class="prob-stat-chip">
          <span class="prob-stat-num prob-success">{{ passRate.overall.passed }}</span>
          <span class="prob-stat-lbl">Đạt</span>
        </div>
        <div class="prob-stat-chip">
          <span class="prob-stat-num prob-danger">{{ passRate.overall.failed }}</span>
          <span class="prob-stat-lbl">Không đạt</span>
        </div>
        <div class="prob-stat-chip">
          <span class="prob-stat-num prob-warn">{{ passRate.overall.extended }}</span>
          <span class="prob-stat-lbl">Gia hạn</span>
        </div>
        <div class="prob-stat-chip">
          <span class="prob-stat-num prob-primary">
            {{ passRate.overall.pass_rate !== null ? passRate.overall.pass_rate.toFixed(1) + '%' : '—' }}
          </span>
          <span class="prob-stat-lbl">Tỷ lệ vượt</span>
        </div>
      </div>

      <DataTable
        :value="passRate?.by_department ?? []"
        :loading="loadingPassRate"
        size="small"
        striped-rows
      >
        <template #empty><div class="ob-empty">Chưa có phiếu đánh giá được duyệt trong kỳ</div></template>
        <Column field="group_name" header="Phòng ban" />
        <Column field="passed" header="Đạt" style="width:70px" />
        <Column field="failed" header="Không đạt" style="width:90px" />
        <Column field="extended" header="Gia hạn" style="width:80px" />
        <Column field="total_decided" header="Tổng" style="width:70px" />
        <Column header="Tỷ lệ" style="width:160px">
          <template #body="{ data }">
            <div v-if="data.pass_rate !== null" style="display:flex;align-items:center;gap:0.5rem">
              <ProgressBar :value="data.pass_rate" :show-value="false" style="height:7px;flex:1" />
              <span style="font-size:0.8rem;white-space:nowrap">{{ data.pass_rate.toFixed(1) }}%</span>
            </div>
            <span v-else class="ob-muted">—</span>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- ── Section 5: Xu hướng theo tháng ───────────────────────────────── -->
    <div v-if="passRate?.monthly_trend?.length" class="ob-card">
      <div class="prob-section-title">
        <i class="pi pi-chart-line" />
        Xu hướng thử việc theo tháng
      </div>
      <DataTable :value="passRate.monthly_trend" size="small" striped-rows>
        <Column header="Tháng" style="width:100px">
          <template #body="{ data }">{{ data.month }}/{{ data.year }}</template>
        </Column>
        <Column field="total" header="Tổng" style="width:70px" />
        <Column header="Đạt" style="width:70px">
          <template #body="{ data }">
            <span :class="data.passed > 0 ? 'prob-success' : 'ob-muted'">{{ data.passed }}</span>
          </template>
        </Column>
        <Column header="Không đạt" style="width:90px">
          <template #body="{ data }">
            <span :class="data.failed > 0 ? 'prob-danger' : 'ob-muted'">{{ data.failed }}</span>
          </template>
        </Column>
        <Column header="Gia hạn" style="width:80px">
          <template #body="{ data }">
            <span :class="data.extended > 0 ? 'prob-warn' : 'ob-muted'">{{ data.extended }}</span>
          </template>
        </Column>
        <Column header="Tỷ lệ đạt" style="width:120px">
          <template #body="{ data }">
            <span v-if="data.total > 0">{{ (data.passed / data.total * 100).toFixed(1) }}%</span>
            <span v-else class="ob-muted">—</span>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- ── Section 6: Lý do không đạt ──────────────────────────────────── -->
    <div v-if="(failureReasons?.total_failed ?? 0) > 0" class="ob-card">
      <div class="prob-section-title">
        <i class="pi pi-exclamation-triangle" />
        Lý do không đạt thử việc
        <Tag :value="`${failureReasons!.total_failed} trường hợp`" severity="danger" />
        <span class="ob-muted" style="font-size:0.8rem;margin-left:auto">
          (Thống kê từ khóa — không phân tích tự động)
        </span>
      </div>
      <div class="prob-keyword-grid">
        <div
          v-for="kw in failureReasons!.reasons"
          :key="kw.keyword"
          class="prob-keyword-chip"
        >
          <span class="prob-keyword-name">{{ kw.keyword }}</span>
          <span class="prob-keyword-count">{{ kw.count }}</span>
          <ProgressBar :value="kw.pct" :show-value="false" style="height:5px;margin-top:0.25rem" />
        </div>
      </div>

      <Accordion v-if="failureReasons!.raw_comments.length" style="margin-top:1rem">
        <AccordionPanel value="comments">
          <AccordionHeader>Nhận xét quản lý ({{ failureReasons!.raw_comments.length }})</AccordionHeader>
          <AccordionContent>
            <DataTable :value="failureReasons!.raw_comments" size="small" striped-rows>
              <Column field="employee_name" header="Nhân viên" style="width:180px" />
              <Column header="Ngày đánh giá" style="width:120px">
                <template #body="{ data }">{{ fmtDate(data.evaluation_date) }}</template>
              </Column>
              <Column field="manager_comment" header="Nhận xét">
                <template #body="{ data }">{{ data.manager_comment ?? '—' }}</template>
              </Column>
            </DataTable>
          </AccordionContent>
        </AccordionPanel>
      </Accordion>
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
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Accordion from 'primevue/accordion'
import AccordionContent from 'primevue/accordioncontent'
import AccordionHeader from 'primevue/accordionheader'
import AccordionPanel from 'primevue/accordionpanel'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import InputText from 'primevue/inputtext'
import ProgressBar from 'primevue/progressbar'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import Dialog from 'primevue/dialog'
import ProgressSpinner from 'primevue/progressspinner'
import api from '@/services/api'
import type { DepartmentOption } from '@/services/departmentService'
import { toDepartmentSelectOptions } from '@/utils/departmentOptions'
import probationReportService, {
  type ActiveProbationReport,
  type ChecklistCompletionReport,
  type FailureReasonReport,
  type ProbationHistoryReport,
  type ProbationExportParams,
  type ProbationPassRateReport,
} from '@/services/probationReportService'
import { useExportQueue } from '@/composables/useExportQueue'

withDefaults(defineProps<{
  breadcrumbRootLabel?: string
  breadcrumbRootTo?: string
  reportTitle?: string
}>(), {
  breadcrumbRootLabel: 'Nhân viên',
  breadcrumbRootTo: '/employees',
  reportTitle: 'Báo cáo thử việc',
})

const toast = useToast()

// ── Filters ────────────────────────────────────────────────────────────────────
const filterFrom    = ref<Date | null>(null)
const filterTo      = ref<Date | null>(null)
const filterDeptId  = ref<number | null>(null)
const filterKeyword = ref('')
const departments   = ref<DepartmentOption[]>([])

// ── State ──────────────────────────────────────────────────────────────────────
const loadingActive    = ref(false)
const loadingHistory   = ref(false)
const loadingChecklist = ref(false)
const loadingPassRate  = ref(false)
const loadingFailure   = ref(false)

const { isExporting, exportProgress, showExportDialog, startExport, cancelExport } = useExportQueue()

const activeProbation = ref<ActiveProbationReport | null>(null)
const historyReport   = ref<ProbationHistoryReport | null>(null)
const checklist       = ref<ChecklistCompletionReport | null>(null)
const passRate        = ref<ProbationPassRateReport | null>(null)
const failureReasons  = ref<FailureReasonReport | null>(null)

// ── Pagination (history) ───────────────────────────────────────────────────────
const historyPage     = ref(1)
const historyPageSize = ref(20)
const historyTotal    = ref(0)

// ── Computed ───────────────────────────────────────────────────────────────────
const loadingAny = computed(() =>
  loadingActive.value || loadingHistory.value || loadingChecklist.value || loadingPassRate.value || loadingFailure.value
)

const hasDateRange = computed(() => !!filterFrom.value && !!filterTo.value)

function resetFilters() {
  filterFrom.value    = null
  filterTo.value      = null
  filterKeyword.value = ''
  filterDeptId.value  = null
  loadAll()
}

function toIso(d: Date | null): string {
  if (!d) return ''
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const avgDaysRemaining = computed(() => {
  const items = activeProbation.value?.items ?? []
  const withDays = items.filter(i => i.days_remaining !== null)
  if (!withDays.length) return null
  return Math.round(withDays.reduce((s, i) => s + i.days_remaining!, 0) / withDays.length)
})

const avgChecklistPct = computed(() => {
  const rows = checklist.value?.items ?? []
  if (!rows.length) return null
  return rows.reduce((s, r) => s + r.avg_completion_pct, 0) / rows.length
})

// ── Helpers ────────────────────────────────────────────────────────────────────
function fmtDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

function evalResultLabel(r: string): string {
  const map: Record<string, string> = {
    not_started: 'Chưa đánh giá',
    pending:     'Đang chờ',
    passed:      'Đạt',
    failed:      'Không đạt',
    extended:    'Gia hạn',
  }
  return map[r] ?? r
}

function evalResultSeverity(r: string): 'secondary' | 'success' | 'danger' | 'warn' | 'info' {
  const map: Record<string, 'secondary' | 'success' | 'danger' | 'warn' | 'info'> = {
    not_started: 'secondary',
    pending:     'info',
    passed:      'success',
    failed:      'danger',
    extended:    'warn',
  }
  return map[r] ?? 'secondary'
}

function empStatusLabel(s: string): string {
  const map: Record<string, string> = {
    probation:  'Đang thử việc',
    official:   'Chính thức',
    resigned:   'Đã nghỉ',
    terminated: 'Đã chấm dứt',
    maternity:  'Thai sản',
    suspended:  'Tạm hoãn',
  }
  return map[s] ?? s
}

function empStatusSeverity(s: string): 'info' | 'success' | 'warn' | 'danger' | 'secondary' {
  const map: Record<string, 'info' | 'success' | 'warn' | 'danger' | 'secondary'> = {
    probation:  'info',
    official:   'success',
    resigned:   'warn',
    terminated: 'danger',
  }
  return map[s] ?? 'secondary'
}

function evalStatusLabel(s: string): string {
  const map: Record<string, string> = {
    draft:     'Nháp',
    submitted: 'Đã nộp',
    approved:  'Đã duyệt',
  }
  return map[s] ?? s
}

function apiError(e: unknown): string {
  const err = e as { response?: { data?: { detail?: unknown } } }
  const d = err.response?.data?.detail
  return typeof d === 'string' ? d : 'Đã xảy ra lỗi'
}

// ── Load ───────────────────────────────────────────────────────────────────────
async function loadActive() {
  loadingActive.value = true
  try {
    const params: { department_id?: number; keyword?: string } = {}
    if (filterDeptId.value) params.department_id = filterDeptId.value
    if (filterKeyword.value.trim()) params.keyword = filterKeyword.value.trim()
    const res = await probationReportService.getActive(params)
    activeProbation.value = res.data
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 })
  } finally {
    loadingActive.value = false
  }
}

function effectiveDates() {
  return {
    start_date: filterFrom.value ? toIso(filterFrom.value) : '2000-01-01',
    end_date:   filterTo.value   ? toIso(filterTo.value)   : toIso(new Date()),
  }
}

async function loadHistory() {
  loadingHistory.value = true
  try {
    const params: Record<string, unknown> = {
      page:      historyPage.value,
      page_size: historyPageSize.value,
    }
    if (filterFrom.value)             params.start_date    = toIso(filterFrom.value)
    if (filterTo.value)               params.end_date      = toIso(filterTo.value)
    if (filterDeptId.value)           params.department_id = filterDeptId.value
    if (filterKeyword.value.trim())   params.keyword       = filterKeyword.value.trim()
    const res = await probationReportService.getHistory(params as Parameters<typeof probationReportService.getHistory>[0])
    historyReport.value = res.data
    historyTotal.value  = res.data.total
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 })
  } finally {
    loadingHistory.value = false
  }
}

async function onHistoryPage(event: { page: number; rows: number }) {
  historyPage.value     = event.page + 1  // PrimeVue page is 0-based
  historyPageSize.value = event.rows
  await loadHistory()
}

async function loadChecklist() {
  loadingChecklist.value = true
  try {
    const { start_date, end_date } = effectiveDates()
    const res = await probationReportService.getChecklistCompletion({
      start_date,
      end_date,
      ...(filterDeptId.value ? { department_id: filterDeptId.value } : {}),
    })
    checklist.value = res.data
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 })
  } finally {
    loadingChecklist.value = false
  }
}

async function loadPassRate() {
  loadingPassRate.value = true
  try {
    const { start_date, end_date } = effectiveDates()
    const res = await probationReportService.getPassRate({
      start_date,
      end_date,
      ...(filterDeptId.value ? { department_id: filterDeptId.value } : {}),
    })
    passRate.value = res.data
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 })
  } finally {
    loadingPassRate.value = false
  }
}

async function loadFailureReasons() {
  loadingFailure.value = true
  try {
    const { start_date, end_date } = effectiveDates()
    const res = await probationReportService.getFailureReasons({ start_date, end_date })
    failureReasons.value = res.data
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 })
  } finally {
    loadingFailure.value = false
  }
}

async function loadAll() {
  historyPage.value = 1
  await Promise.all([loadActive(), loadHistory(), loadChecklist(), loadPassRate(), loadFailureReasons()])
}

async function doExport() {
  if (!filterFrom.value || !filterTo.value) return
  const filters: Record<string, any> = {
    start_date: toIso(filterFrom.value),
    end_date:   toIso(filterTo.value),
  }
  if (filterDeptId.value) {
    filters.department_id = filterDeptId.value
  }
  const filename = `bc_thu_viec_${filters.start_date}_${filters.end_date}.xlsx`
  await startExport('probation', filters, filename)
}

onMounted(async () => {
  try {
    const r = await api.get('/departments', { params: { page_size: 200 } })
    const data = r.data
    departments.value = toDepartmentSelectOptions(Array.isArray(data) ? data : (data.items ?? []))
  } catch { /* ignore */ }
  await loadAll()
})
</script>
