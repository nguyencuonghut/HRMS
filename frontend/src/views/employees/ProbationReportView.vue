<template>
  <div class="prob-report">
    <!-- Breadcrumb -->
    <nav class="ob-breadcrumb">
      <RouterLink to="/employees">Nhân viên</RouterLink>
      <i class="pi pi-chevron-right" />
      <span>Báo cáo thử việc</span>
    </nav>

    <!-- Filter toolbar -->
    <div class="toolbar">
      <span class="ob-label" style="white-space:nowrap">Kỳ báo cáo:</span>
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
        @keydown.enter="loadActive"
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
        v-tooltip.bottom="'Kỳ báo cáo áp dụng cho: ngày vào làm (checklist) và ngày đánh giá (tỷ lệ vượt thử việc)'"
        @click="loadAll"
      />
      <div style="flex:1" />
      <Button
        label="Xuất Excel"
        icon="pi pi-file-excel"
        severity="success"
        outlined
        :disabled="!hasDateRange"
        :loading="exporting"
        @click="doExport"
      />
    </div>

    <!-- ── Section 1: KPI Summary Cards ──────────────────────────────────── -->
    <div class="prob-kpi-row">
      <div class="prob-kpi-card">
        <div class="prob-kpi-value prob-kpi-primary">{{ activeProbation?.total ?? '—' }}</div>
        <div class="prob-kpi-label">Đang thử việc</div>
      </div>
      <div class="prob-kpi-card">
        <div class="prob-kpi-value prob-kpi-info">
          {{ avgDaysRemaining !== null ? avgDaysRemaining : '—' }}
        </div>
        <div class="prob-kpi-label">Ngày còn lại TB</div>
      </div>
      <div class="prob-kpi-card">
        <div class="prob-kpi-value prob-kpi-success">
          {{ passRate?.overall?.pass_rate !== null && passRate?.overall?.pass_rate !== undefined
            ? passRate.overall.pass_rate.toFixed(1) + '%' : '—' }}
        </div>
        <div class="prob-kpi-label">Tỷ lệ vượt thử việc</div>
      </div>
      <div class="prob-kpi-card">
        <div class="prob-kpi-value prob-kpi-warn">
          {{ avgChecklistPct !== null ? avgChecklistPct.toFixed(1) + '%' : '—' }}
        </div>
        <div class="prob-kpi-label">Checklist hoàn thành TB</div>
      </div>
    </div>

    <!-- ── Section 2: Nhân viên đang thử việc ───────────────────────────── -->
    <div class="ob-card">
      <div class="prob-section-title">
        <i class="pi pi-users" />
        Nhân viên đang thử việc
        <Tag v-if="activeProbation" :value="String(activeProbation.total)" severity="secondary" />
      </div>
      <DataTable
        :value="activeProbation?.items ?? []"
        :loading="loadingActive"
        size="small"
        striped-rows
        :rows="20"
        paginator
        :rows-per-page-options="[10,20,50]"
      >
        <template #empty><div class="ob-empty">Không có nhân viên đang thử việc</div></template>

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

        <Column field="department_name" header="Phòng ban" style="width:150px">
          <template #body="{ data }">{{ data.department_name ?? '—' }}</template>
        </Column>

        <Column header="Kết thúc TV" style="width:120px">
          <template #body="{ data }">{{ fmtDate(data.probation_end_date) }}</template>
        </Column>

        <Column header="Còn lại" style="width:100px">
          <template #body="{ data }">
            <Badge
              v-if="data.days_remaining !== null"
              :value="`${data.days_remaining}d`"
              :severity="urgencySeverity(data.urgency)"
            />
            <span v-else class="ob-muted">—</span>
          </template>
        </Column>

        <Column header="Onboarding" style="width:160px">
          <template #body="{ data }">
            <div v-if="data.completion_pct !== null" style="display:flex;align-items:center;gap:0.5rem">
              <ProgressBar :value="data.completion_pct" style="height:7px;flex:1" />
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
      </DataTable>
    </div>

    <!-- ── Section 3: Checklist hoàn thành theo phòng ban ───────────────── -->
    <div v-if="hasDateRange" class="ob-card">
      <div class="prob-section-title">
        <i class="pi pi-clipboard" />
        Tỷ lệ hoàn thành Checklist onboarding theo phòng ban
      </div>
      <DataTable
        :value="checklist?.items ?? []"
        :loading="loadingChecklist"
        size="small"
        striped-rows
      >
        <template #empty><div class="ob-empty">Không có dữ liệu trong kỳ này</div></template>

        <Column field="department_name" header="Phòng ban" />
        <Column field="total_checklists" header="Tổng" style="width:80px" />
        <Column field="completed_count" header="Hoàn thành" style="width:100px" />
        <Column header="Tỷ lệ xong" style="width:180px">
          <template #body="{ data }">
            <div style="display:flex;align-items:center;gap:0.5rem">
              <ProgressBar :value="data.completion_rate" style="height:7px;flex:1" />
              <span style="font-size:0.8rem;white-space:nowrap">{{ data.completion_rate.toFixed(1) }}%</span>
            </div>
          </template>
        </Column>
        <Column header="Tiến độ TB" style="width:180px">
          <template #body="{ data }">
            <div style="display:flex;align-items:center;gap:0.5rem">
              <ProgressBar :value="data.avg_completion_pct" style="height:7px;flex:1" />
              <span style="font-size:0.8rem;white-space:nowrap">{{ data.avg_completion_pct.toFixed(1) }}%</span>
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- ── Section 4: Tỷ lệ vượt thử việc ──────────────────────────────── -->
    <div v-if="hasDateRange" class="ob-card">
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
              <ProgressBar :value="data.pass_rate" style="height:7px;flex:1" />
              <span style="font-size:0.8rem;white-space:nowrap">{{ data.pass_rate.toFixed(1) }}%</span>
            </div>
            <span v-else class="ob-muted">—</span>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- ── Section 5: Xu hướng theo tháng ───────────────────────────────── -->
    <div v-if="hasDateRange && passRate?.monthly_trend?.length" class="ob-card">
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
    <div v-if="hasDateRange && (failureReasons?.total_failed ?? 0) > 0" class="ob-card">
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
          <ProgressBar :value="kw.pct" style="height:5px;margin-top:0.25rem" />
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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Accordion from 'primevue/accordion'
import AccordionContent from 'primevue/accordioncontent'
import AccordionHeader from 'primevue/accordionheader'
import AccordionPanel from 'primevue/accordionpanel'
import Badge from 'primevue/badge'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import InputText from 'primevue/inputtext'
import ProgressBar from 'primevue/progressbar'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import api from '@/services/api'
import probationReportService, {
  type ActiveProbationReport,
  type ChecklistCompletionReport,
  type FailureReasonReport,
  type ProbationPassRateReport,
} from '@/services/probationReportService'

const toast = useToast()

// ── Filters ────────────────────────────────────────────────────────────────────
// Mặc định: đầu năm hiện tại → hôm nay
const now = new Date()
const defaultFrom = new Date(now.getFullYear(), 0, 1)   // 1/1/năm nay
const defaultTo   = new Date(now.getFullYear(), now.getMonth(), now.getDate()) // hôm nay

const filterFrom    = ref<Date | null>(defaultFrom)
const filterTo      = ref<Date | null>(defaultTo)
const filterDeptId  = ref<number | null>(null)
const filterKeyword = ref('')
const departments   = ref<{ id: number; name: string }[]>([])

// ── State ──────────────────────────────────────────────────────────────────────
const loadingActive    = ref(false)
const loadingChecklist = ref(false)
const loadingPassRate  = ref(false)
const loadingFailure   = ref(false)
const exporting        = ref(false)

const activeProbation = ref<ActiveProbationReport | null>(null)
const checklist       = ref<ChecklistCompletionReport | null>(null)
const passRate        = ref<ProbationPassRateReport | null>(null)
const failureReasons  = ref<FailureReasonReport | null>(null)

// ── Computed ───────────────────────────────────────────────────────────────────
const loadingAny = computed(() =>
  loadingActive.value || loadingChecklist.value || loadingPassRate.value || loadingFailure.value
)

const hasDateRange = computed(() => !!filterFrom.value && !!filterTo.value)

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

function urgencySeverity(urgency: string): 'danger' | 'warn' | 'success' {
  if (urgency === 'critical') return 'danger'
  if (urgency === 'warning')  return 'warn'
  return 'success'
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

async function loadChecklist() {
  if (!filterFrom.value || !filterTo.value) return
  loadingChecklist.value = true
  try {
    const res = await probationReportService.getChecklistCompletion({
      start_date: toIso(filterFrom.value),
      end_date:   toIso(filterTo.value),
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
  if (!filterFrom.value || !filterTo.value) return
  loadingPassRate.value = true
  try {
    const res = await probationReportService.getPassRate({
      start_date: toIso(filterFrom.value),
      end_date:   toIso(filterTo.value),
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
  if (!filterFrom.value || !filterTo.value) return
  loadingFailure.value = true
  try {
    const res = await probationReportService.getFailureReasons({
      start_date: toIso(filterFrom.value),
      end_date:   toIso(filterTo.value),
    })
    failureReasons.value = res.data
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 })
  } finally {
    loadingFailure.value = false
  }
}

async function loadAll() {
  await Promise.all([loadActive(), loadChecklist(), loadPassRate(), loadFailureReasons()])
}

async function doExport() {
  if (!filterFrom.value || !filterTo.value) return
  exporting.value = true
  try {
    const token = localStorage.getItem('access_token') ?? ''
    const params: Record<string, string> = {
      start_date: toIso(filterFrom.value),
      end_date:   toIso(filterTo.value),
    }
    if (filterDeptId.value) params.department_id = String(filterDeptId.value)
    const qs = new URLSearchParams(params)
    const res = await fetch(`/api/v1/reports/probation/export?${qs}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error((body as { detail?: string }).detail ?? 'Lỗi xuất file')
    }
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `bc_thu_viec_${params.start_date}_${params.end_date}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e: unknown) {
    toast.add({ severity: 'error', summary: 'Lỗi xuất file', detail: String((e as Error).message), life: 5000 })
  } finally {
    exporting.value = false
  }
}

onMounted(async () => {
  try {
    const r = await api.get('/departments', { params: { page_size: 200 } })
    const data = r.data
    departments.value = Array.isArray(data) ? data : (data.items ?? [])
  } catch { /* ignore */ }
  await loadAll()
})
</script>
