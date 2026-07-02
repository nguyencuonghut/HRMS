<template>
  <div>
    <!-- Bộ lọc chính -->
    <div class="training-report-filters">
      <DatePicker
        v-model="fromDate"
        date-format="dd/mm/yy"
        placeholder="Từ ngày *"
        show-button-bar
        style="width: 150px"
      />
      <DatePicker
        v-model="toDate"
        date-format="dd/mm/yy"
        placeholder="Đến ngày *"
        show-button-bar
        style="width: 150px"
      />
      <Select
        v-model="filterDeptId"
        :options="departments"
        option-label="name"
        option-value="id"
        placeholder="Phòng ban"
        show-clear
        filter
        style="width: 180px"
      />
      <Select
        v-model="filterCourseId"
        :options="courses"
        option-label="name"
        option-value="id"
        placeholder="Khóa học"
        show-clear
        filter
        style="width: 200px"
      />
      <Button
        label="Xem báo cáo"
        icon="pi pi-chart-bar"
        :loading="loadingReport"
        @click="fetchReport"
      />
      <Button
        label="Xuất Excel"
        icon="pi pi-download"
        severity="secondary"
        :loading="exporting"
        :disabled="!summary"
        @click="doExport"
      />
    </div>

    <!-- Placeholder khi chưa fetch -->
    <div v-if="!summary && !loadingReport" class="training-report-placeholder">
      <i class="pi pi-chart-bar" style="font-size: 2.5rem; opacity: 0.3" />
      <span>Chọn khoảng thời gian và bấm <strong>Xem báo cáo</strong></span>
    </div>

    <!-- Loading skeleton -->
    <div v-else-if="loadingReport" class="training-report-cards">
      <Skeleton v-for="n in 4" :key="n" height="80px" border-radius="8px" />
    </div>

    <!-- Summary cards -->
    <div v-else-if="summary" class="training-report-cards">
      <div class="training-report-card">
        <div class="training-report-card-label">Tổng lượt đào tạo</div>
        <div class="training-report-card-value">{{ summary.total_records }}</div>
      </div>
      <div class="training-report-card">
        <div class="training-report-card-label">Hoàn thành</div>
        <div class="training-report-card-value" style="color: var(--p-green-500)">
          {{ summary.total_completed }}
        </div>
      </div>
      <div class="training-report-card">
        <div class="training-report-card-label">Chi phí ước tính</div>
        <div class="training-report-card-value" style="font-size: 1.1rem">
          {{ fmtCurrency(summary.total_cost) }}
        </div>
      </div>
      <div class="training-report-card">
        <div class="training-report-card-label">Tỷ lệ HT trung bình</div>
        <div class="training-report-card-value">{{ summary.avg_completion_rate }}%</div>
      </div>
    </div>

    <!-- Bảng theo khóa học -->
    <template v-if="summary">
      <div class="card card-content-padding" style="margin-bottom: 1rem">
        <div class="training-report-section-title">Theo khóa học</div>
        <DataTable
          :value="summary.by_course"
          size="small"
          striped-rows
          :loading="loadingReport"
          sort-field="completion_rate"
          :sort-order="-1"
        >
          <template #empty>
            <div class="training-empty">Không có dữ liệu trong kỳ này</div>
          </template>
          <Column field="course_name" header="Tên khóa học" sortable style="min-width: 200px" />
          <Column field="course_type_label" header="Loại" style="width: 110px">
            <template #body="{ data }: { data: CourseCompletionStat }">
              <Tag :value="data.course_type_label" severity="secondary" class="training-type-tag" />
            </template>
          </Column>
          <Column field="total_assigned" header="Tổng NV" sortable style="width: 90px; text-align: center" />
          <Column field="completed" header="Hoàn thành" sortable style="width: 110px; text-align: center">
            <template #body="{ data }: { data: CourseCompletionStat }">
              <span style="color: var(--p-green-600); font-weight: 600">{{ data.completed }}</span>
            </template>
          </Column>
          <Column field="not_completed" header="Chưa HT" sortable style="width: 100px; text-align: center">
            <template #body="{ data }: { data: CourseCompletionStat }">
              <span v-if="data.not_completed > 0" style="color: var(--p-red-500)">{{ data.not_completed }}</span>
              <span v-else class="muted-text">0</span>
            </template>
          </Column>
          <Column field="in_progress" header="Đang học" sortable style="width: 100px; text-align: center" />
          <Column field="completion_rate" header="Tỷ lệ HT (%)" sortable style="width: 150px">
            <template #body="{ data }: { data: CourseCompletionStat }">
              <div class="training-rate-bar">
                <ProgressBar :value="data.completion_rate" style="flex: 1; height: 8px" :show-value="false" />
                <span style="min-width: 42px; text-align: right; font-variant-numeric: tabular-nums">
                  {{ data.completion_rate }}%
                </span>
              </div>
            </template>
          </Column>
        </DataTable>
      </div>

      <!-- Bảng theo phòng ban -->
      <div class="card card-content-padding" style="margin-bottom: 1rem">
        <div class="training-report-section-title">Theo phòng ban</div>
        <DataTable
          :value="summary.by_department"
          size="small"
          striped-rows
          :loading="loadingReport"
          sort-field="completion_rate"
          :sort-order="-1"
        >
          <template #empty>
            <div class="training-empty">Không có dữ liệu trong kỳ này</div>
          </template>
          <Column field="department_name" header="Phòng ban" sortable style="min-width: 160px">
            <template #body="{ data }: { data: DepartmentTrainingStat }">
              <span v-if="data.department_name">{{ data.department_name }}</span>
              <span v-else class="muted-text">Chưa phân phòng ban</span>
            </template>
          </Column>
          <Column field="total_records" header="Tổng lượt" sortable style="width: 100px; text-align: center" />
          <Column field="completed" header="Hoàn thành" sortable style="width: 110px; text-align: center">
            <template #body="{ data }: { data: DepartmentTrainingStat }">
              <span style="color: var(--p-green-600); font-weight: 600">{{ data.completed }}</span>
            </template>
          </Column>
          <Column field="completion_rate" header="Tỷ lệ HT (%)" sortable style="width: 150px">
            <template #body="{ data }: { data: DepartmentTrainingStat }">
              <div class="training-rate-bar">
                <ProgressBar :value="data.completion_rate" style="flex: 1; height: 8px" :show-value="false" />
                <span style="min-width: 42px; text-align: right">{{ data.completion_rate }}%</span>
              </div>
            </template>
          </Column>
          <Column field="total_cost" header="Chi phí ước tính" sortable style="width: 160px; text-align: right">
            <template #body="{ data }: { data: DepartmentTrainingStat }">
              <span v-if="data.total_cost !== null" style="font-variant-numeric: tabular-nums">
                {{ fmtCurrency(data.total_cost) }}
              </span>
              <span v-else class="muted-text">—</span>
            </template>
          </Column>
        </DataTable>
      </div>

      <!-- Sub-section: NV chưa HT bắt buộc -->
      <div class="card card-content-padding">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem">
          <div class="training-report-section-title" style="margin-bottom: 0">
            Nhân viên chưa hoàn thành đào tạo bắt buộc
          </div>
          <div class="training-incomplete-toolbar">
            <Select
              v-model="incompleteDeptId"
              :options="departments"
              option-label="name"
              option-value="id"
              placeholder="Phòng ban"
              show-clear
              filter
              style="width: 180px"
            />
            <Button
              label="Xem danh sách"
              icon="pi pi-users"
              severity="secondary"
              :loading="loadingIncomplete"
              @click="fetchIncomplete"
            />
          </div>
        </div>

        <div v-if="incompleteList === null && !loadingIncomplete" class="training-report-placeholder" style="padding: 1.5rem">
          <span>Bấm <strong>Xem danh sách</strong> để tải dữ liệu</span>
        </div>

        <DataTable
          v-else
          :value="incompleteList ?? []"
          :loading="loadingIncomplete"
          size="small"
          striped-rows
          sort-field="incomplete_count"
          :sort-order="-1"
        >
          <template #empty>
            <div class="training-empty">Tất cả nhân viên đã hoàn thành các khóa bắt buộc</div>
          </template>
          <Column field="employee_code" header="Mã NV" style="width: 110px" />
          <Column field="employee_name" header="Họ và tên" sortable style="min-width: 160px" />
          <Column field="department_name" header="Phòng ban" style="width: 160px">
            <template #body="{ data }: { data: IncompleteMandatoryEmployee }">
              <span v-if="data.department_name">{{ data.department_name }}</span>
              <span v-else class="muted-text">—</span>
            </template>
          </Column>
          <Column field="incomplete_count" header="Số khóa chưa HT" sortable style="width: 140px; text-align: center">
            <template #body="{ data }: { data: IncompleteMandatoryEmployee }">
              <Tag :value="String(data.incomplete_count)" severity="danger" />
            </template>
          </Column>
          <Column field="incomplete_courses" header="Danh sách khóa chưa HT" style="min-width: 240px">
            <template #body="{ data }: { data: IncompleteMandatoryEmployee }">
              <div style="display: flex; flex-wrap: wrap; gap: 0.25rem">
                <Tag
                  v-for="course in data.incomplete_courses"
                  :key="course"
                  :value="course"
                  severity="warn"
                  class="training-type-tag"
                />
              </div>
            </template>
          </Column>
        </DataTable>
      </div>
    </template>

    <Toast />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import ProgressBar from 'primevue/progressbar'
import Select from 'primevue/select'
import Skeleton from 'primevue/skeleton'
import Tag from 'primevue/tag'
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'

import trainingReportService, {
  type TrainingReportSummary,
  type CourseCompletionStat,
  type DepartmentTrainingStat,
  type IncompleteMandatoryEmployee,
} from '@/services/trainingReportService'
import trainingService from '@/services/trainingService'
import departmentService, { type DepartmentRead } from '@/services/departmentService'

const toast = useToast()

// ── State ─────────────────────────────────────────────────────────────────────

const departments   = ref<DepartmentRead[]>([])
const courses       = ref<{ id: number; name: string }[]>([])

const fromDate      = ref<Date | null>(new Date(new Date().getFullYear(), 0, 1)) // Jan 1 this year
const toDate        = ref<Date | null>(new Date())
const filterDeptId  = ref<number | null>(null)
const filterCourseId = ref<number | null>(null)

const loadingReport = ref(false)
const summary       = ref<TrainingReportSummary | null>(null)
const exporting     = ref(false)

const incompleteDeptId  = ref<number | null>(null)
const loadingIncomplete = ref(false)
const incompleteList    = ref<IncompleteMandatoryEmployee[] | null>(null)

// ── Helpers ───────────────────────────────────────────────────────────────────

function toIso(d: Date): string {
  const y   = d.getFullYear()
  const m   = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function fmtCurrency(val: string | number | null): string {
  if (val === null || val === undefined) return '—'
  const n = typeof val === 'string' ? parseFloat(val) : val
  if (isNaN(n)) return '—'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(n)
}

function buildParams(): Record<string, unknown> | null {
  if (!fromDate.value || !toDate.value) {
    toast.add({ severity: 'warn', summary: 'Thiếu thông tin', detail: 'Vui lòng chọn Từ ngày và Đến ngày', life: 3000 })
    return null
  }
  const params: Record<string, unknown> = {
    from_date: toIso(fromDate.value),
    to_date:   toIso(toDate.value),
  }
  if (filterDeptId.value)   params.department_id = filterDeptId.value
  if (filterCourseId.value) params.course_id     = filterCourseId.value
  return params
}

// ── Fetch report ──────────────────────────────────────────────────────────────

async function fetchReport() {
  const params = buildParams()
  if (!params) return
  loadingReport.value = true
  try {
    const res = await trainingReportService.getSummary(params)
    summary.value = res.data
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể tải báo cáo', life: 4000 })
  } finally {
    loadingReport.value = false
  }
}

async function doExport() {
  const params = buildParams()
  if (!params) return
  exporting.value = true
  try {
    await trainingReportService.exportExcel(params)
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể xuất file Excel', life: 4000 })
  } finally {
    exporting.value = false
  }
}

// ── Incomplete mandatory ───────────────────────────────────────────────────────

async function fetchIncomplete() {
  loadingIncomplete.value = true
  try {
    const params: Record<string, unknown> = {}
    if (incompleteDeptId.value) params.department_id = incompleteDeptId.value
    const res = await trainingReportService.getIncompleteMandatory(params)
    incompleteList.value = res.data
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể tải danh sách', life: 4000 })
  } finally {
    loadingIncomplete.value = false
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────

onMounted(async () => {
  await Promise.allSettled([
    departmentService.getList(true).then(r => { departments.value = r.data }),
    trainingService.listCourses({ is_active: true, page_size: 500 }).then(r => {
      courses.value = r.data.items.map(c => ({ id: c.id, name: c.name }))
    }),
  ])
})
</script>
