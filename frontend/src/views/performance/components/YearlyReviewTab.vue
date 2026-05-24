<template>
  <div>
    <!-- Toolbar -->
    <div class="perf-toolbar">
      <Select
        v-model="filterYear"
        :options="yearOptions"
        option-label="label"
        option-value="value"
        placeholder="Năm"
        show-clear
        filter
        style="width: 110px"
        @change="applyFilter"
      />

      <Select
        v-model="filterDeptId"
        :options="departments"
        option-label="name"
        option-value="id"
        placeholder="Tất cả phòng ban"
        show-clear
        filter
        style="width: 200px"
        @change="applyFilter"
      />

      <Select
        v-model="filterRating"
        :options="ratingOptions"
        option-label="label"
        option-value="value"
        placeholder="Tất cả xếp loại"
        show-clear
        filter
        style="width: 190px"
        @change="applyFilter"
      />

      <IconField class="perf-search">
        <InputIcon class="pi pi-search" />
        <InputText
          v-model="filterSearch"
          placeholder="Tên NV, mã NV..."
          @keyup.enter="applyFilter"
        />
      </IconField>

      <Button
        icon="pi pi-refresh"
        severity="secondary"
        text
        rounded
        :loading="loading"
        v-tooltip.top="'Làm mới'"
        @click="reset"
      />

      <Button
        label="Lưu đánh giá"
        icon="pi pi-plus"
        class="ml-auto"
        @click="openCreate"
      />
    </div>

    <!-- Table -->
    <div class="card">
      <DataTable
        :value="items"
        :loading="loading"
        responsive-layout="scroll"
        striped-rows
        size="small"
        :rows="pageSize"
        :total-records="total"
        :lazy="true"
        paginator
        paginator-template="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
        current-page-report-template="{first}–{last} / {totalRecords}"
        :rows-per-page-options="[20, 50, 100]"
        @page="onPage"
      >
        <template #empty>
          <div class="perf-empty">Không có dữ liệu đánh giá cuối năm</div>
        </template>

        <Column header="Mã NV" style="width: 110px">
          <template #body="{ data }: { data: YearlyReviewRead }">
            <span class="perf-emp-code">{{ data.employee_code }}</span>
          </template>
        </Column>

        <Column header="Họ và tên" style="min-width: 160px">
          <template #body="{ data }: { data: YearlyReviewRead }">
            <span>{{ data.employee_name }}</span>
            <div v-if="data.department_name" class="perf-dept-name">{{ data.department_name }}</div>
          </template>
        </Column>

        <Column header="Năm" style="width: 70px; text-align: center">
          <template #body="{ data }: { data: YearlyReviewRead }">{{ data.year }}</template>
        </Column>

        <Column header="Số tháng KPI" style="width: 110px; text-align: center">
          <template #body="{ data }: { data: YearlyReviewRead }">
            <span :class="data.months_count < 6 ? 'perf-muted' : ''">{{ data.months_count }}/12</span>
          </template>
        </Column>

        <Column header="Điểm TB" style="width: 90px; text-align: center">
          <template #body="{ data }: { data: YearlyReviewRead }">
            <span v-if="data.avg_score !== null" :class="scoreClass(data.avg_score)" class="perf-score">
              {{ Number(data.avg_score).toFixed(1) }}
            </span>
            <span v-else class="perf-muted">—</span>
          </template>
        </Column>

        <Column header="Xếp loại" style="width: 140px">
          <template #body="{ data }: { data: YearlyReviewRead }">
            <Tag :value="data.rating_label" :severity="ratingSeverity(data.rating)" />
          </template>
        </Column>

        <Column header="Nhận xét" style="min-width: 160px">
          <template #body="{ data }: { data: YearlyReviewRead }">
            <span class="perf-note">
              {{ data.review_note ? data.review_note.slice(0, 60) + (data.review_note.length > 60 ? '…' : '') : '—' }}
            </span>
          </template>
        </Column>

        <Column header="" style="width: 90px; text-align: right">
          <template #body="{ data }: { data: YearlyReviewRead }">
            <Button
              icon="pi pi-pencil"
              text rounded size="small" severity="secondary"
              v-tooltip.top="'Sửa'"
              @click="openEdit(data)"
            />
            <Button
              icon="pi pi-trash"
              text rounded size="small" severity="danger"
              v-tooltip.top="'Xóa'"
              @click="confirmDelete(data)"
            />
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Dialog lưu/sửa đánh giá -->
    <Dialog
      v-model:visible="showDialog"
      :header="editingId ? 'Sửa đánh giá cuối năm' : 'Lưu đánh giá cuối năm'"
      modal
      :style="{ width: '520px' }"
      :closable="!saving"
    >
      <div class="perf-form">
        <!-- Nhân viên -->
        <div class="perf-field">
          <label class="perf-label">Nhân viên <span class="perf-req">*</span></label>
          <Select
            v-model="form.employee_id"
            :options="employees"
            option-label="full_name"
            option-value="id"
            placeholder="Chọn nhân viên..."
            filter
            :filter-fields="['full_name', 'display_code']"
            :disabled="!!editingId"
            class="w-full"
            @change="onEmployeeOrYearChange"
          >
            <template #option="{ option }">
              <span class="perf-emp-code">{{ option.display_code }}</span>
              <span class="perf-sep">·</span>
              {{ option.full_name }}
            </template>
          </Select>
          <span v-if="errors.employee_id" class="perf-error">{{ errors.employee_id }}</span>
        </div>

        <!-- Năm -->
        <div class="perf-field">
          <label class="perf-label">Năm <span class="perf-req">*</span></label>
          <InputNumber
            v-model="form.year"
            :min="2000"
            :max="2100"
            :use-grouping="false"
            :disabled="!!editingId"
            class="w-full"
            placeholder="VD: 2026"
            @blur="onEmployeeOrYearChange"
          />
          <span v-if="errors.year" class="perf-error">{{ errors.year }}</span>
        </div>

        <!-- KPI summary (read-only) -->
        <div v-if="summaryLoading" class="perf-summary-loading">
          <i class="pi pi-spin pi-spinner" /> Đang tải điểm KPI...
        </div>
        <div v-else-if="summary" class="perf-summary-box">
          <div class="perf-summary-row">
            <span class="perf-summary-label">Số tháng có KPI:</span>
            <strong>{{ summary.months_count }}/12</strong>
          </div>
          <div class="perf-summary-row">
            <span class="perf-summary-label">Điểm trung bình:</span>
            <strong v-if="summary.avg_score !== null" :class="scoreClass(summary.avg_score)">
              {{ Number(summary.avg_score).toFixed(2) }}
            </strong>
            <span v-else class="perf-muted">Chưa có dữ liệu KPI tháng</span>
          </div>
          <div v-if="summary.has_discipline" class="perf-summary-row perf-discipline-warn">
            <i class="pi pi-exclamation-triangle" />
            <span>Có vi phạm kỷ luật trong năm — xếp loại tối đa là <strong>Cần cải thiện</strong></span>
          </div>
          <div class="perf-summary-row">
            <span class="perf-summary-label">Xếp loại gợi ý:</span>
            <Tag
              v-if="summary.suggested_rating"
              :value="ratingLabel(summary.suggested_rating)"
              :severity="ratingSeverity(summary.suggested_rating)"
            />
            <span v-else class="perf-muted">—</span>
          </div>
        </div>

        <!-- Xếp loại -->
        <div class="perf-field">
          <label class="perf-label">Xếp loại <span class="perf-req">*</span></label>
          <Select
            v-model="form.rating"
            :options="ratingOptions"
            option-label="label"
            option-value="value"
            placeholder="Chọn xếp loại..."
            filter
            class="w-full"
          />
          <span v-if="errors.rating" class="perf-error">{{ errors.rating }}</span>
        </div>

        <!-- Nhận xét -->
        <div class="perf-field">
          <label class="perf-label">Nhận xét <span class="perf-optional">(tùy chọn)</span></label>
          <Textarea v-model="form.review_note" rows="3" class="w-full" auto-resize placeholder="Nhận xét đánh giá cuối năm..." />
        </div>

        <p v-if="dialogError" class="perf-api-error">
          <i class="pi pi-exclamation-triangle" />
          {{ dialogError }}
        </p>
      </div>

      <template #footer>
        <Button label="Hủy" severity="secondary" text :disabled="saving" @click="showDialog = false" />
        <Button :label="editingId ? 'Lưu thay đổi' : 'Lưu'" :loading="saving" @click="submit" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'

import performanceService, {
  type YearlyReviewRead,
  type YearlyKpiSummary,
} from '@/services/performanceService'
import departmentService, { type DepartmentRead } from '@/services/departmentService'
import employeeService, { type EmployeeLookupItem } from '@/services/employeeService'

const confirm = useConfirm()
const toast   = useToast()

// ── State ─────────────────────────────────────────────────────────────────────

const loading  = ref(false)
const items    = ref<YearlyReviewRead[]>([])
const total    = ref(0)
const page     = ref(1)
const pageSize = ref(20)

const departments = ref<DepartmentRead[]>([])
const employees   = ref<EmployeeLookupItem[]>([])

// Filters
const filterYear   = ref<number | null>(new Date().getFullYear())
const filterDeptId = ref<number | null>(null)
const filterRating = ref<string | null>(null)
const filterSearch = ref('')

// Dialog
const showDialog    = ref(false)
const saving        = ref(false)
const editingId     = ref<number | null>(null)
const dialogError   = ref('')
const errors        = ref<Record<string, string>>({})
const summary       = ref<YearlyKpiSummary | null>(null)
const summaryLoading = ref(false)

const form = ref<{
  employee_id: number | null
  year: number | null
  rating: string | null
  review_note: string
}>({
  employee_id: null,
  year: new Date().getFullYear(),
  rating: null,
  review_note: '',
})

// ── Constants ─────────────────────────────────────────────────────────────────

const currentYear = new Date().getFullYear()
const yearOptions = Array.from({ length: 10 }, (_, i) => ({
  label: String(currentYear - i),
  value: currentYear - i,
}))

const ratingOptions = [
  { value: 'xuat_sac',      label: 'Xuất sắc' },
  { value: 'tot',           label: 'Tốt' },
  { value: 'dat',           label: 'Đạt' },
  { value: 'can_cai_thien', label: 'Cần cải thiện' },
]

const RATING_LABELS: Record<string, string> = {
  xuat_sac:      'Xuất sắc',
  tot:           'Tốt',
  dat:           'Đạt',
  can_cai_thien: 'Cần cải thiện',
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function ratingSeverity(rating: string): string {
  return { xuat_sac: 'success', tot: 'info', dat: 'secondary', can_cai_thien: 'warn' }[rating] ?? 'secondary'
}

function ratingLabel(rating: string): string {
  return RATING_LABELS[rating] ?? rating
}

function scoreClass(score: string | null): string {
  if (score === null) return ''
  const n = Number(score)
  if (n >= 90) return 'perf-score-high'
  if (n >= 70) return 'perf-score-mid'
  return 'perf-score-low'
}

// ── Load ──────────────────────────────────────────────────────────────────────

async function load() {
  loading.value = true
  try {
    const res = await performanceService.listYearlyReviews({
      year:          filterYear.value ?? undefined,
      department_id: filterDeptId.value ?? undefined,
      rating:        filterRating.value ?? undefined,
      search:        filterSearch.value || undefined,
      page:          page.value,
      page_size:     pageSize.value,
    })
    items.value = res.data.items
    total.value = res.data.total
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể tải danh sách đánh giá', life: 4000 })
  } finally {
    loading.value = false
  }
}

function applyFilter() {
  page.value = 1
  load()
}

function reset() {
  filterYear.value   = new Date().getFullYear()
  filterDeptId.value = null
  filterRating.value = null
  filterSearch.value = ''
  page.value = 1
  load()
}

function onPage(e: { page: number; rows: number }) {
  page.value = e.page + 1
  pageSize.value = e.rows
  load()
}

// ── Summary auto-load ─────────────────────────────────────────────────────────

async function loadSummary() {
  if (!form.value.employee_id || !form.value.year) {
    summary.value = null
    return
  }
  summaryLoading.value = true
  try {
    const res = await performanceService.getYearlySummary(form.value.employee_id, form.value.year)
    summary.value = res.data
    // Pre-fill rating from suggested_rating if creating
    if (!editingId.value && res.data.suggested_rating && !form.value.rating) {
      form.value.rating = res.data.suggested_rating
    }
  } catch {
    summary.value = null
  } finally {
    summaryLoading.value = false
  }
}

function onEmployeeOrYearChange() {
  loadSummary()
}

// ── Dialog ────────────────────────────────────────────────────────────────────

function openCreate() {
  editingId.value = null
  dialogError.value = ''
  errors.value = {}
  summary.value = null
  Object.assign(form.value, {
    employee_id: null,
    year: new Date().getFullYear(),
    rating: null,
    review_note: '',
  })
  showDialog.value = true
}

function openEdit(row: YearlyReviewRead) {
  editingId.value = row.id
  dialogError.value = ''
  errors.value = {}
  Object.assign(form.value, {
    employee_id: row.employee_id,
    year: row.year,
    rating: row.rating,
    review_note: row.review_note ?? '',
  })
  showDialog.value = true
  loadSummary()
}

function validate(): boolean {
  errors.value = {}
  if (!form.value.employee_id) errors.value.employee_id = 'Vui lòng chọn nhân viên'
  if (!form.value.year)        errors.value.year        = 'Vui lòng nhập năm'
  if (!form.value.rating)      errors.value.rating      = 'Vui lòng chọn xếp loại'
  return Object.keys(errors.value).length === 0
}

async function submit() {
  if (!validate()) return
  saving.value = true
  dialogError.value = ''
  try {
    if (editingId.value) {
      await performanceService.updateYearlyReview(editingId.value, {
        rating:      form.value.rating!,
        review_note: form.value.review_note.trim() || null,
      })
      toast.add({ severity: 'success', summary: 'Đã cập nhật', detail: 'Đánh giá cuối năm đã được cập nhật', life: 3000 })
    } else {
      await performanceService.createYearlyReview({
        employee_id: form.value.employee_id!,
        year:        form.value.year!,
        rating:      form.value.rating!,
        review_note: form.value.review_note.trim() || null,
      })
      toast.add({ severity: 'success', summary: 'Đã lưu', detail: 'Đánh giá cuối năm đã được lưu', life: 3000 })
    }
    showDialog.value = false
    load()
  } catch (err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    dialogError.value = typeof detail === 'string' ? detail : 'Có lỗi xảy ra, vui lòng thử lại'
  } finally {
    saving.value = false
  }
}

// ── Delete ────────────────────────────────────────────────────────────────────

function confirmDelete(row: YearlyReviewRead) {
  confirm.require({
    message: `Xóa đánh giá cuối năm ${row.year} của ${row.employee_name}?`,
    header: 'Xác nhận xóa',
    icon: 'pi pi-exclamation-triangle',
    acceptSeverity: 'danger',
    acceptLabel: 'Xóa',
    rejectLabel: 'Hủy',
    accept: () => doDelete(row.id),
  })
}

async function doDelete(id: number) {
  try {
    await performanceService.deleteYearlyReview(id)
    toast.add({ severity: 'success', summary: 'Đã xóa', detail: 'Bản ghi đánh giá đã được xóa', life: 3000 })
    load()
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể xóa bản ghi đánh giá', life: 4000 })
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────

onMounted(async () => {
  try {
    const [deptsRes, empsRes] = await Promise.all([
      departmentService.getList(true),
      employeeService.lookup({ limit: 500 }),
    ])
    departments.value = deptsRes.data
    employees.value   = empsRes.data
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi khởi tạo', detail: 'Không thể tải danh mục dữ liệu', life: 5000 })
  }
  load()
})
</script>
