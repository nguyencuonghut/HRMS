<template>
  <div>
    <!-- Toolbar -->
    <div class="training-toolbar">
      <IconField>
        <InputIcon class="pi pi-search" />
        <InputText
          v-model="searchText"
          placeholder="Tìm mã NV, tên NV, tên khóa học..."
          class="training-search"
          @input="onSearchInput"
        />
      </IconField>

      <Select
        v-model="filterDeptId"
        :options="departments"
        option-label="name"
        option-value="id"
        placeholder="Phòng ban"
        show-clear
        filter
        style="width: 180px"
        @change="applyFilter"
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
        @change="applyFilter"
      />

      <Select
        v-model="filterStatus"
        :options="recordStatusOptions"
        option-label="label"
        option-value="value"
        placeholder="Trạng thái"
        show-clear
        filter
        style="width: 170px"
        @change="applyFilter"
      />

      <Select
        v-model="filterResult"
        :options="resultFilterOptions"
        option-label="label"
        option-value="value"
        placeholder="Kết quả"
        show-clear
        filter
        style="width: 150px"
        @change="applyFilter"
      />

      <DatePicker
        v-model="filterFromDate"
        date-format="dd/mm/yy"
        placeholder="Từ ngày"
        show-button-bar
        style="width: 140px"
        @date-select="applyFilter"
        @clear-click="applyFilter"
      />

      <DatePicker
        v-model="filterToDate"
        date-format="dd/mm/yy"
        placeholder="Đến ngày"
        show-button-bar
        style="width: 140px"
        @date-select="applyFilter"
        @clear-click="applyFilter"
      />

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
        label="Gán vào khóa học"
        icon="pi pi-user-plus"
        class="ml-auto"
        @click="openAssignDialog"
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
          <div class="training-empty">Không có bản ghi đào tạo</div>
        </template>

        <Column header="Nhân viên" style="min-width: 180px">
          <template #body="{ data }: { data: TrainingRecordRead }">
            <span class="emp-code" style="margin-right: 0.4rem">{{ data.employee_code }}</span>
            {{ data.employee_name }}
          </template>
        </Column>

        <Column header="Phòng ban" style="min-width: 140px">
          <template #body="{ data }: { data: TrainingRecordRead }">
            <span v-if="data.department_name">{{ data.department_name }}</span>
            <span v-else class="muted-text">—</span>
          </template>
        </Column>

        <Column header="Khóa học" style="min-width: 180px">
          <template #body="{ data }: { data: TrainingRecordRead }">
            {{ data.course_name }}
          </template>
        </Column>

        <Column header="Loại" style="width: 100px">
          <template #body="{ data }: { data: TrainingRecordRead }">
            <Tag :value="data.course_type_label" severity="secondary" class="training-type-tag" />
          </template>
        </Column>

        <Column header="Trạng thái" style="width: 140px">
          <template #body="{ data }: { data: TrainingRecordRead }">
            <Tag
              :value="data.status_label"
              :severity="statusSeverity(data.status)"
              class="training-type-tag"
            />
          </template>
        </Column>

        <Column header="Kết quả" style="width: 120px">
          <template #body="{ data }: { data: TrainingRecordRead }">
            <Tag
              v-if="data.result"
              :value="data.result_label ?? data.result"
              :severity="data.result === 'dat' ? 'success' : 'danger'"
              class="training-type-tag"
            />
            <span v-else class="muted-text">Chưa đánh giá</span>
          </template>
        </Column>

        <Column header="Điểm" style="width: 70px; text-align: right">
          <template #body="{ data }: { data: TrainingRecordRead }">
            <span v-if="data.score !== null" class="record-score">{{ data.score }}</span>
            <span v-else class="muted-text">—</span>
          </template>
        </Column>

        <Column header="Bắt đầu" style="width: 110px">
          <template #body="{ data }: { data: TrainingRecordRead }">
            <span v-if="data.start_date">{{ fmtDate(data.start_date) }}</span>
            <span v-else class="muted-text">—</span>
          </template>
        </Column>

        <Column header="Kết thúc" style="width: 110px">
          <template #body="{ data }: { data: TrainingRecordRead }">
            <span v-if="data.end_date">{{ fmtDate(data.end_date) }}</span>
            <span v-else class="muted-text">—</span>
          </template>
        </Column>

        <Column header="" style="width: 90px; text-align: right">
          <template #body="{ data }: { data: TrainingRecordRead }">
            <Button
              icon="pi pi-pencil"
              text rounded size="small" severity="secondary"
              v-tooltip.top="'Cập nhật kết quả'"
              @click="openUpdateDialog(data)"
            />
            <Button
              icon="pi pi-trash"
              text rounded size="small" severity="danger"
              v-tooltip.top="'Xóa'"
              @click="confirmDeleteRecord(data)"
            />
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Dialog gán vào khóa học -->
    <Dialog
      v-model:visible="showAssignDialog"
      header="Gán nhân viên vào khóa học"
      modal
      :style="{ width: '560px' }"
      :closable="!saving"
    >
      <div class="training-form">
        <!-- Mode toggle -->
        <div class="training-field">
          <SelectButton
            v-model="assignMode"
            :options="assignModeOptions"
            option-label="label"
            option-value="value"
            class="w-full"
          />
        </div>

        <div class="training-field">
          <label class="training-label">Kế hoạch (tùy chọn)</label>
          <Select
            v-model="assignForm.plan_id"
            :options="plans"
            option-label="title"
            option-value="id"
            placeholder="Chọn kế hoạch..."
            show-clear
            filter
            class="w-full"
            @change="onPlanChange"
          >
            <template #option="{ option }: { option: PlanRead }">
              {{ option.title }}
              <span class="muted-text" style="margin-left: 0.4rem">
                ({{ option.year }}{{ option.quarter ? ` Q${option.quarter}` : '' }})
              </span>
            </template>
          </Select>
        </div>

        <div class="training-field">
          <label class="training-label">Khóa học <span class="training-req">*</span></label>
          <Select
            v-model="assignForm.course_id"
            :options="assignCourseOptions"
            option-label="name"
            option-value="id"
            placeholder="Chọn khóa học..."
            filter
            :filter-fields="['code', 'name']"
            class="w-full"
          >
            <template #option="{ option }: { option: AssignCourseOption }">
              <span class="emp-code" style="margin-right: 0.4rem">{{ option.code }}</span>
              {{ option.name }}
            </template>
          </Select>
          <span v-if="assignErrors.course_id" class="training-error">{{ assignErrors.course_id }}</span>
        </div>

        <!-- Chọn từng NV -->
        <div v-if="assignMode === 'employees'" class="training-field">
          <label class="training-label">Nhân viên <span class="training-req">*</span></label>
          <MultiSelect
            v-model="assignForm.employee_ids"
            :options="employeeLookup"
            option-label="full_name"
            option-value="id"
            placeholder="Tìm và chọn nhân viên..."
            filter
            :filter-fields="['display_code', 'full_name']"
            class="w-full assign-dialog-multiselect"
            display="chip"
            :max-selected-labels="3"
          >
            <template #option="{ option }: { option: EmployeeLookupItem }">
              <span class="emp-code" style="margin-right: 0.4rem">{{ option.display_code }}</span>
              {{ option.full_name }}
            </template>
          </MultiSelect>
          <span v-if="assignErrors.employee_ids" class="training-error">{{ assignErrors.employee_ids }}</span>
        </div>

        <!-- Gán theo phòng ban -->
        <div v-else class="training-field">
          <label class="training-label">Phòng ban <span class="training-req">*</span></label>
          <MultiSelect
            v-model="assignForm.department_ids"
            :options="departments"
            option-label="name"
            option-value="id"
            placeholder="Chọn phòng ban..."
            filter
            display="chip"
            class="w-full"
          />
          <span v-if="assignErrors.department_ids" class="training-error">{{ assignErrors.department_ids }}</span>
          <small class="muted-text">Toàn bộ nhân viên thuộc các phòng ban được chọn sẽ được gán vào khóa học này.</small>
        </div>

        <div class="training-field">
          <label class="training-label">Ghi chú</label>
          <Textarea v-model="assignForm.note" rows="2" class="w-full" auto-resize placeholder="Ghi chú..." />
        </div>

        <p v-if="assignError" class="training-api-error">
          <i class="pi pi-exclamation-triangle" />
          {{ assignError }}
        </p>
      </div>

      <template #footer>
        <Button label="Hủy" severity="secondary" text :disabled="saving" @click="showAssignDialog = false" />
        <Button label="Gán" :loading="saving" @click="submitAssign" />
      </template>
    </Dialog>

    <!-- Dialog cập nhật kết quả -->
    <Dialog
      v-model:visible="showUpdateDialog"
      header="Cập nhật kết quả đào tạo"
      modal
      :style="{ width: '480px' }"
      :closable="!savingUpdate"
    >
      <div class="training-form">
        <div class="training-field">
          <label class="training-label">Trạng thái <span class="training-req">*</span></label>
          <Select
            v-model="updateForm.status"
            :options="recordStatusOptions"
            option-label="label"
            option-value="value"
            filter
            class="w-full"
          />
        </div>

        <div v-if="showResultField" class="training-field">
          <label class="training-label">Kết quả</label>
          <Select
            v-model="updateForm.result"
            :options="recordResultOptions"
            option-label="label"
            option-value="value"
            placeholder="Chưa đánh giá"
            show-clear
            filter
            class="w-full"
          />
        </div>

        <div class="training-field">
          <label class="training-label">Điểm số (0–100)</label>
          <InputNumber
            v-model="updateForm.score"
            :min="0"
            :max="100"
            :fraction-digits="2"
            placeholder="Điểm số"
            class="w-full"
          />
          <span v-if="updateErrors.score" class="training-error">{{ updateErrors.score }}</span>
        </div>

        <div class="training-row">
          <div class="training-field">
            <label class="training-label">Ngày bắt đầu</label>
            <DatePicker
              v-model="updateForm.start_date_obj"
              date-format="dd/mm/yy"
              placeholder="DD/MM/YYYY"
              show-button-bar
              class="w-full"
            />
          </div>
          <div class="training-field">
            <label class="training-label">Ngày kết thúc</label>
            <DatePicker
              v-model="updateForm.end_date_obj"
              date-format="dd/mm/yy"
              placeholder="DD/MM/YYYY"
              show-button-bar
              class="w-full"
            />
          </div>
        </div>
        <span v-if="updateErrors.dates" class="training-error">{{ updateErrors.dates }}</span>

        <div class="training-field">
          <label class="training-label">Ghi chú</label>
          <Textarea v-model="updateForm.note" rows="2" class="w-full" auto-resize />
        </div>

        <p v-if="updateError" class="training-api-error">
          <i class="pi pi-exclamation-triangle" />
          {{ updateError }}
        </p>
      </div>

      <template #footer>
        <Button label="Hủy" severity="secondary" text :disabled="savingUpdate" @click="showUpdateDialog = false" />
        <Button label="Lưu" :loading="savingUpdate" @click="submitUpdate" />
      </template>
    </Dialog>

    <Toast />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import MultiSelect from 'primevue/multiselect'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import Toast from 'primevue/toast'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'

import trainingService, {
  RECORD_STATUSES,
  RECORD_RESULTS,
  type TrainingRecordRead,
  type RecordStatusValue,
  type RecordResultValue,
  type CourseRead,
  type PlanRead,
} from '@/services/trainingService'
import departmentService, { type DepartmentRead } from '@/services/departmentService'
import employeeService, { type EmployeeLookupItem } from '@/services/employeeService'

const confirm = useConfirm()
const toast   = useToast()
const recordStatusOptions = RECORD_STATUSES.map((option) => ({ ...option }))
const recordResultOptions = RECORD_RESULTS.map((option) => ({ ...option }))

// ── State ─────────────────────────────────────────────────────────────────────

const loading  = ref(false)
const items    = ref<TrainingRecordRead[]>([])
const total    = ref(0)
const page     = ref(1)
const pageSize = ref(20)

const departments     = ref<DepartmentRead[]>([])
const courses         = ref<CourseRead[]>([])
const plans           = ref<PlanRead[]>([])
const employeeLookup  = ref<EmployeeLookupItem[]>([])

// Filters
const searchText    = ref('')
const filterDeptId  = ref<number | null>(null)
const filterCourseId = ref<number | null>(null)
const filterStatus  = ref<RecordStatusValue | null>(null)
const filterResult  = ref<string | null>(null)
const filterFromDate = ref<Date | null>(null)
const filterToDate   = ref<Date | null>(null)

let searchTimer: ReturnType<typeof setTimeout> | null = null

const resultFilterOptions = [
  ...recordResultOptions,
  { value: 'null', label: 'Chưa đánh giá' },
]

// Assign dialog
const showAssignDialog = ref(false)
const saving           = ref(false)
const assignError      = ref('')
const assignErrors     = ref<Record<string, string>>({})

type AssignMode = 'employees' | 'department'
const assignMode = ref<AssignMode>('employees')
const assignModeOptions = [
  { value: 'employees', label: 'Chọn từng nhân viên' },
  { value: 'department', label: 'Theo phòng ban' },
]

const assignForm = ref<{
  plan_id: number | null
  course_id: number | null
  employee_ids: number[]
  department_ids: number[]
  note: string
}>({
  plan_id: null,
  course_id: null,
  employee_ids: [],
  department_ids: [],
  note: '',
})

// Courses shown in assign dialog — all active if no plan, filtered by plan if plan selected
type AssignCourseOption = Pick<CourseRead, 'id' | 'code' | 'name'>

const planCoursesForAssign = ref<AssignCourseOption[]>([])
const assignCourseOptions = computed(() =>
  assignForm.value.plan_id ? planCoursesForAssign.value : courses.value
)

// Update dialog
const showUpdateDialog = ref(false)
const updatingRecord   = ref<TrainingRecordRead | null>(null)
const savingUpdate     = ref(false)
const updateError      = ref('')
const updateErrors     = ref<Record<string, string>>({})

const updateForm = ref<{
  status: RecordStatusValue
  result: RecordResultValue | null
  score: number | null
  start_date_obj: Date | null
  end_date_obj: Date | null
  note: string
}>({
  status: 'chua_bat_dau',
  result: null,
  score: null,
  start_date_obj: null,
  end_date_obj: null,
  note: '',
})

const showResultField = computed(() =>
  updateForm.value.status === 'hoan_thanh' || updateForm.value.status === 'khong_hoan_thanh'
)

// ── Helpers ───────────────────────────────────────────────────────────────────

function statusSeverity(s: RecordStatusValue): 'secondary' | 'info' | 'success' | 'danger' | 'warn' {
  const map: Record<RecordStatusValue, 'secondary' | 'info' | 'success' | 'danger' | 'warn'> = {
    chua_bat_dau:     'secondary',
    dang_hoc:         'info',
    hoan_thanh:       'success',
    khong_hoan_thanh: 'danger',
    vang_mat:         'warn',
  }
  return map[s] ?? 'secondary'
}

function fmtDate(s: string): string {
  if (!s) return '—'
  const [y, m, d] = s.split('-')
  return `${d}/${m}/${y}`
}

function toIso(d: Date): string {
  const y   = d.getFullYear()
  const m   = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

// ── Load ──────────────────────────────────────────────────────────────────────

async function load() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: page.value, page_size: pageSize.value }
    if (searchText.value)    params.search        = searchText.value
    if (filterDeptId.value)  params.department_id = filterDeptId.value
    if (filterCourseId.value) params.course_id    = filterCourseId.value
    if (filterStatus.value)  params.status        = filterStatus.value
    if (filterResult.value)  params.result        = filterResult.value
    if (filterFromDate.value) params.from_date     = toIso(filterFromDate.value)
    if (filterToDate.value)   params.to_date       = toIso(filterToDate.value)

    const res = await trainingService.getRecords(params)
    items.value = res.data.items
    total.value = res.data.total
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể tải danh sách bản ghi', life: 4000 })
  } finally {
    loading.value = false
  }
}

function applyFilter() { page.value = 1; load() }

function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => applyFilter(), 400)
}

function reset() {
  searchText.value    = ''
  filterDeptId.value  = null
  filterCourseId.value = null
  filterStatus.value  = null
  filterResult.value  = null
  filterFromDate.value = null
  filterToDate.value   = null
  page.value = 1
  load()
}

function onPage(e: { page: number; rows: number }) {
  page.value     = e.page + 1
  pageSize.value = e.rows
  load()
}

// ── Assign dialog ─────────────────────────────────────────────────────────────

async function openAssignDialog() {
  assignError.value  = ''
  assignErrors.value = {}
  assignMode.value   = 'employees'
  Object.assign(assignForm.value, {
    plan_id: null,
    course_id: null,
    employee_ids: [],
    department_ids: [],
    note: '',
  })
  planCoursesForAssign.value = []

  // Load employees if not loaded
  if (employeeLookup.value.length === 0) {
    try {
      const res = await employeeService.lookup({ limit: 500 })
      employeeLookup.value = res.data
    } catch {
      toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể tải danh sách nhân viên', life: 4000 })
    }
  }

  showAssignDialog.value = true
}

async function onPlanChange() {
  assignForm.value.course_id = null
  planCoursesForAssign.value = []
  if (!assignForm.value.plan_id) return
  try {
    const res = await trainingService.listPlanCourses(assignForm.value.plan_id)
    // Map plan courses to the minimal shape Select needs.
    planCoursesForAssign.value = res.data.map(pc => ({
      id: pc.course_id,
      code: pc.course_code,
      name: pc.course_name,
    }))
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể tải khóa học của kế hoạch', life: 4000 })
  }
}

function validateAssign(): boolean {
  assignErrors.value = {}
  if (!assignForm.value.course_id) {
    assignErrors.value.course_id = 'Vui lòng chọn khóa học'
  }
  if (assignMode.value === 'employees' && !assignForm.value.employee_ids.length) {
    assignErrors.value.employee_ids = 'Vui lòng chọn ít nhất 1 nhân viên'
  }
  if (assignMode.value === 'department') {
    if (!assignForm.value.department_ids.length) {
      assignErrors.value.department_ids = 'Vui lòng chọn ít nhất 1 phòng ban'
    }
    if (!assignForm.value.plan_id) {
      assignErrors.value.department_ids = (assignErrors.value.department_ids ? assignErrors.value.department_ids + '. ' : '') + 'Gán theo phòng ban yêu cầu chọn Kế hoạch'
    }
  }
  return Object.keys(assignErrors.value).length === 0
}

async function submitAssign() {
  if (!validateAssign()) return
  saving.value = true
  assignError.value = ''
  try {
    const planId   = assignForm.value.plan_id
    const courseId = assignForm.value.course_id!
    const note     = assignForm.value.note.trim() || null

    if (planId) {
      // Bulk assign via plan endpoint (supports both employee_ids and department_id)
      const body = assignMode.value === 'department'
        ? { plan_id: planId, course_id: courseId, department_ids: assignForm.value.department_ids, note }
        : { plan_id: planId, course_id: courseId, employee_ids: assignForm.value.employee_ids, note }

      const res = await trainingService.bulkAssign(planId, body)
      const { created, skipped } = res.data
      toast.add({
        severity: 'success',
        summary: 'Đã gán',
        detail: `Đã gán ${created} nhân viên${skipped > 0 ? `, bỏ qua ${skipped} (đã tồn tại)` : ''}`,
        life: 4000,
      })
    } else {
      // Không có plan — gán từng NV hoặc theo phòng ban qua records endpoint
      // Với mode phòng ban mà không có plan: cần planId (bắt buộc cho bulk assign)
      // → tạo records riêng lẻ
      const empIds = assignMode.value === 'employees'
        ? assignForm.value.employee_ids
        : []  // department mode yêu cầu plan (đã validate)

      let created = 0
      let errCount = 0
      for (const empId of empIds) {
        try {
          await trainingService.createRecord({ employee_id: empId, course_id: courseId, note })
          created++
        } catch {
          errCount++
        }
      }
      toast.add({
        severity: errCount === 0 ? 'success' : 'warn',
        summary: 'Kết quả',
        detail: `Đã gán ${created} nhân viên${errCount > 0 ? `, lỗi ${errCount}` : ''}`,
        life: 4000,
      })
    }

    showAssignDialog.value = false
    load()
  } catch (err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    assignError.value = typeof detail === 'string' ? detail : 'Có lỗi xảy ra, vui lòng thử lại'
  } finally {
    saving.value = false
  }
}

// ── Update dialog ─────────────────────────────────────────────────────────────

function openUpdateDialog(rec: TrainingRecordRead) {
  updatingRecord.value = rec
  updateError.value    = ''
  updateErrors.value   = {}
  updateForm.value = {
    status:        rec.status,
    result:        rec.result,
    score:         rec.score !== null ? parseFloat(rec.score) : null,
    start_date_obj: rec.start_date ? parseDate(rec.start_date) : null,
    end_date_obj:   rec.end_date   ? parseDate(rec.end_date)   : null,
    note:          rec.note ?? '',
  }
  showUpdateDialog.value = true
}

function parseDate(s: string): Date {
  const [y, m, d] = s.split('-').map(Number)
  return new Date(y, m - 1, d)
}

function validateUpdate(): boolean {
  updateErrors.value = {}
  const start = updateForm.value.start_date_obj
  const end   = updateForm.value.end_date_obj
  if (start && end && end < start) {
    updateErrors.value.dates = 'Ngày kết thúc phải >= ngày bắt đầu'
    return false
  }
  if (updateForm.value.score !== null && (updateForm.value.score < 0 || updateForm.value.score > 100)) {
    updateErrors.value.score = 'Điểm phải trong khoảng 0–100'
    return false
  }
  return true
}

async function submitUpdate() {
  if (!validateUpdate()) return
  savingUpdate.value = true
  updateError.value  = ''
  try {
    const id = updatingRecord.value!.id
    const payload: Record<string, unknown> = {
      status: updateForm.value.status,
    }
    if (showResultField.value) payload.result = updateForm.value.result
    if (updateForm.value.score !== null) payload.score = updateForm.value.score
    if (updateForm.value.start_date_obj) payload.start_date = toIso(updateForm.value.start_date_obj)
    if (updateForm.value.end_date_obj)   payload.end_date   = toIso(updateForm.value.end_date_obj)
    if (updateForm.value.note.trim())    payload.note       = updateForm.value.note.trim()

    const res = await trainingService.updateRecord(id, payload)
    const idx = items.value.findIndex(r => r.id === id)
    if (idx !== -1) items.value[idx] = res.data
    toast.add({ severity: 'success', summary: 'Đã lưu', detail: 'Bản ghi đào tạo đã được cập nhật', life: 3000 })
    showUpdateDialog.value = false
  } catch (err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    updateError.value = typeof detail === 'string' ? detail : 'Có lỗi xảy ra, vui lòng thử lại'
  } finally {
    savingUpdate.value = false
  }
}

// ── Delete ────────────────────────────────────────────────────────────────────

function confirmDeleteRecord(rec: TrainingRecordRead) {
  confirm.require({
    message: `Xóa bản ghi đào tạo của "${rec.employee_name}" — "${rec.course_name}"?`,
    header: 'Xác nhận xóa',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Xóa',
    rejectLabel: 'Hủy',
    accept: () => doDeleteRecord(rec),
  })
}

async function doDeleteRecord(rec: TrainingRecordRead) {
  try {
    await trainingService.deleteRecord(rec.id)
    toast.add({ severity: 'success', summary: 'Đã xóa', detail: 'Bản ghi đào tạo đã được xóa', life: 3000 })
    load()
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể xóa bản ghi', life: 4000 })
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────

onMounted(async () => {
  await Promise.allSettled([
    departmentService.getList(true).then(r => { departments.value = r.data }),
    trainingService.listCourses({ is_active: true, page_size: 500 }).then(r => { courses.value = r.data.items }),
    trainingService.listPlans({ page_size: 200 }).then(r => { plans.value = r.data.items.filter(p => p.status !== 'cancelled') }),
  ])
  load()
})
</script>
