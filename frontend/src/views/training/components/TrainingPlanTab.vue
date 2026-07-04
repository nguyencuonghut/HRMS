<template>
  <div>
    <!-- Toolbar -->
    <div class="training-toolbar">
      <InputNumber
        v-model="filterYear"
        :min="2000"
        :max="2100"
        :use-grouping="false"
        placeholder="Năm"
        style="width: 90px"
        :inputStyle="{ width: '100%' }"
      />

      <Select
        v-model="filterQuarter"
        :options="quarterOptions"
        option-label="label"
        option-value="value"
        placeholder="Quý"
        show-clear
        filter
        style="width: 110px"
      />

      <Select
        v-model="filterDeptId"
        :options="departments"
        option-label="name"
        option-value="id"
        placeholder="Phòng ban"
        show-clear
        filter
        style="width: 200px"
      />

      <Select
        v-model="filterStatus"
        :options="planStatusOptions"
        option-label="label"
        option-value="value"
        placeholder="Trạng thái"
        show-clear
        filter
        style="width: 160px"
      />

      <Button label="Lọc" icon="pi pi-filter" @click="applyFilter" />
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
        label="Tạo kế hoạch"
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
        current-page-report-template="Hiển thị từ {first} đến {last} trên tổng số {totalRecords} dòng"
        :rows-per-page-options="[20, 50, 100]"
        v-model:expandedRows="expandedRows"
        dataKey="id"
        @rowExpand="onRowExpand"
        @page="onPage"
      >
        <template #empty>
          <div class="training-empty">Không có kế hoạch đào tạo</div>
        </template>

        <Column expander style="width: 3rem" />

        <Column header="Tiêu đề kế hoạch" style="min-width: 220px">
          <template #body="{ data }: { data: PlanRead }">
            {{ data.title }}
          </template>
        </Column>

        <Column header="Năm/Quý" style="width: 140px">
          <template #body="{ data }: { data: PlanRead }">
            <span class="training-year-quarter">
              {{ data.quarter ? `${data.year} – Q${data.quarter}` : `${data.year} (Cả năm)` }}
            </span>
          </template>
        </Column>

        <Column header="Phòng ban" style="min-width: 150px">
          <template #body="{ data }: { data: PlanRead }">
            {{ data.department_name ?? 'Toàn công ty' }}
          </template>
        </Column>

        <Column header="Số KH" style="width: 80px; text-align: center">
          <template #body="{ data }: { data: PlanRead }">
            <span class="training-course-count">{{ data.course_count }}</span>
          </template>
        </Column>

        <Column header="Trạng thái" style="width: 120px">
          <template #body="{ data }: { data: PlanRead }">
            <Tag
              :value="data.status_label"
              :severity="planStatusSeverity(data.status)"
              class="training-type-tag"
            />
          </template>
        </Column>

        <Column header="" style="width: 190px; text-align: right">
          <template #body="{ data }: { data: PlanRead }">
            <Button
              v-if="data.status === 'draft'"
              icon="pi pi-pencil"
              text rounded size="small" severity="secondary"
              v-tooltip.top="'Sửa tiêu đề / mô tả'"
              @click="openEdit(data)"
            />
            <Button
              v-if="data.status === 'draft'"
              icon="pi pi-check"
              text rounded size="small" severity="success"
              v-tooltip.top="'Duyệt kế hoạch'"
              @click="approvePlan(data)"
            />
            <Button
              v-if="data.status === 'draft' || data.status === 'approved'"
              icon="pi pi-ban"
              text rounded size="small" severity="warn"
              v-tooltip.top="'Hủy kế hoạch'"
              @click="cancelPlan(data)"
            />
            <Button
              v-if="data.status === 'draft'"
              icon="pi pi-trash"
              text rounded size="small" severity="danger"
              v-tooltip.top="'Xóa'"
              @click="confirmDelete(data)"
            />
          </template>
        </Column>

        <!-- Expand template: plan courses -->
        <template #expansion="{ data }: { data: PlanRead }">
          <div class="training-plan-courses">
            <div class="training-plan-courses-header">
              <span>Danh sách khóa học trong kế hoạch</span>
              <Button
                v-if="data.status !== 'cancelled'"
                label="Thêm khóa học"
                icon="pi pi-plus"
                severity="secondary"
                outlined
                size="small"
                @click="openAddCourse(data.id)"
              />
            </div>

            <div v-if="planCoursesLoading[data.id]" class="loading-state">
              <i class="pi pi-spinner pi-spin" />
              Đang tải...
            </div>

            <DataTable
              v-else
              :value="planCoursesMap[data.id] ?? []"
              size="small"
              striped-rows
            >
              <template #empty>
                <div class="training-empty">Chưa có khóa học nào trong kế hoạch này</div>
              </template>

              <Column header="Tên khóa học" style="min-width: 180px">
                <template #body="{ data: pc }: { data: PlanCourseRead }">
                  <span class="emp-code" style="margin-right: 0.4rem">{{ pc.course_code }}</span>
                  {{ pc.course_name }}
                </template>
              </Column>

              <Column header="Loại" style="width: 100px">
                <template #body="{ data: pc }: { data: PlanCourseRead }">
                  <span class="muted-text">{{ pc.course_type_label }}</span>
                </template>
              </Column>

              <Column header="Số giờ" style="width: 80px; text-align: center">
                <template #body="{ data: pc }: { data: PlanCourseRead }">
                  <span v-if="pc.duration_hours">{{ pc.duration_hours }}h</span>
                  <span v-else class="muted-text">—</span>
                </template>
              </Column>

              <Column header="Số NV dự kiến" style="width: 120px; text-align: center">
                <template #body="{ data: pc }: { data: PlanCourseRead }">
                  <span v-if="pc.target_count !== null">{{ pc.target_count }}</span>
                  <span v-else class="muted-text">—</span>
                </template>
              </Column>

              <Column header="Ngày dự kiến" style="width: 120px">
                <template #body="{ data: pc }: { data: PlanCourseRead }">
                  <span v-if="pc.scheduled_date">{{ fmtDate(pc.scheduled_date) }}</span>
                  <span v-else class="muted-text">—</span>
                </template>
              </Column>

              <Column header="Ghi chú" style="min-width: 140px">
                <template #body="{ data: pc }: { data: PlanCourseRead }">
                  <span v-if="pc.note">{{ pc.note }}</span>
                  <span v-else class="muted-text">—</span>
                </template>
              </Column>

              <Column header="" style="width: 60px; text-align: right">
                <template #body="{ data: pc }: { data: PlanCourseRead }">
                  <Button
                    v-if="data.status !== 'cancelled'"
                    icon="pi pi-trash"
                    text rounded size="small" severity="danger"
                    v-tooltip.top="'Xóa khỏi kế hoạch'"
                    @click="confirmRemoveCourse(data.id, pc)"
                  />
                </template>
              </Column>
            </DataTable>
          </div>
        </template>
      </DataTable>
    </div>

    <!-- Dialog tạo kế hoạch -->
    <Dialog
      v-model:visible="showCreateDialog"
      header="Tạo kế hoạch đào tạo"
      modal
      :style="{ width: '560px' }"
      :closable="!saving"
    >
      <div class="training-form">
        <div class="training-field">
          <label class="training-label">Tiêu đề <span class="training-req">*</span></label>
          <InputText v-model="planForm.title" placeholder="Tiêu đề kế hoạch..." class="w-full" />
          <span v-if="planErrors.title" class="training-error">{{ planErrors.title }}</span>
        </div>

        <div class="training-row">
          <div class="training-field">
            <label class="training-label">Năm <span class="training-req">*</span></label>
            <InputNumber
              v-model="planForm.year"
              :min="2000"
              :max="2100"
              :use-grouping="false"
              class="w-full"
            />
            <span v-if="planErrors.year" class="training-error">{{ planErrors.year }}</span>
          </div>
          <div class="training-field">
            <label class="training-label">Quý (tùy chọn)</label>
            <Select
              v-model="planForm.quarter"
              :options="quarterOptions"
              option-label="label"
              option-value="value"
              placeholder="Cả năm"
              show-clear
              filter
              class="w-full"
            />
          </div>
        </div>

        <div class="training-field">
          <label class="training-label">Phòng ban (tùy chọn)</label>
          <Select
            v-model="planForm.department_id"
            :options="departments"
            option-label="name"
            option-value="id"
            placeholder="Toàn công ty"
            show-clear
            filter
            class="w-full"
          />
        </div>

        <div class="training-field">
          <label class="training-label">Mô tả</label>
          <Textarea v-model="planForm.description" rows="2" class="w-full" auto-resize placeholder="Mô tả kế hoạch..." />
        </div>

        <p v-if="createPlanError" class="training-api-error">
          <i class="pi pi-exclamation-triangle" />
          {{ createPlanError }}
        </p>
      </div>

      <template #footer>
        <Button label="Hủy" severity="secondary" text :disabled="saving" @click="showCreateDialog = false" />
        <Button label="Tạo kế hoạch" :loading="saving" @click="submitPlan" />
      </template>
    </Dialog>

    <!-- Dialog sửa kế hoạch -->
    <Dialog
      v-model:visible="showEditDialog"
      header="Sửa kế hoạch đào tạo"
      modal
      :style="{ width: '480px' }"
      :closable="!savingEdit"
    >
      <div class="training-form">
        <div class="training-field">
          <label class="training-label">Tiêu đề <span class="training-req">*</span></label>
          <InputText v-model="editForm.title" class="w-full" placeholder="Tiêu đề kế hoạch" />
          <span v-if="editErrors.title" class="training-error">{{ editErrors.title }}</span>
        </div>
        <div class="training-field">
          <label class="training-label">Mô tả</label>
          <Textarea v-model="editForm.description" rows="3" class="w-full" auto-resize placeholder="Mô tả kế hoạch..." />
        </div>
        <p v-if="editError" class="training-api-error">
          <i class="pi pi-exclamation-triangle" />
          {{ editError }}
        </p>
      </div>
      <template #footer>
        <Button label="Hủy" severity="secondary" text :disabled="savingEdit" @click="showEditDialog = false" />
        <Button label="Lưu thay đổi" :loading="savingEdit" @click="submitEdit" />
      </template>
    </Dialog>

    <!-- Dialog thêm khóa học vào kế hoạch -->
    <Dialog
      v-model:visible="showAddCourseDialog"
      header="Thêm khóa học vào kế hoạch"
      modal
      :style="{ width: '520px' }"
      :closable="!savingCourse"
    >
      <div class="training-form">
        <div class="training-field">
          <label class="training-label">Chọn khóa học <span class="training-req">*</span></label>
          <Select
            v-model="addCourseForm.course_id"
            :options="activeCourses"
            option-label="name"
            option-value="id"
            placeholder="Tìm và chọn khóa học..."
            filter
            :filter-fields="['code', 'name']"
            class="w-full"
          >
            <template #option="{ option }: { option: CourseRead }">
              <span class="emp-code" style="margin-right: 0.4rem">{{ option.code }}</span>
              {{ option.name }}
            </template>
            <template #value="{ value }">
              <template v-if="value">
                {{ activeCourses.find(c => c.id === value)?.name ?? value }}
              </template>
              <template v-else>Tìm và chọn khóa học...</template>
            </template>
          </Select>
          <span v-if="addCourseErrors.course_id" class="training-error">{{ addCourseErrors.course_id }}</span>
        </div>

        <div class="training-row">
          <div class="training-field">
            <label class="training-label">Số NV dự kiến</label>
            <InputNumber
              v-model="addCourseForm.target_count"
              :min="1"
              placeholder="Số nhân viên"
              class="w-full"
            />
          </div>
          <div class="training-field">
            <label class="training-label">Ngày dự kiến</label>
            <DatePicker
              v-model="addCourseForm.scheduled_date_obj"
              date-format="dd/mm/yy"
              placeholder="DD/MM/YYYY"
              show-button-bar
              class="w-full"
            />
          </div>
        </div>

        <div class="training-field">
          <label class="training-label">Ghi chú</label>
          <InputText v-model="addCourseForm.note" placeholder="Ghi chú thêm..." class="w-full" />
        </div>

        <p v-if="addCourseError" class="training-api-error">
          <i class="pi pi-exclamation-triangle" />
          {{ addCourseError }}
        </p>
      </div>

      <template #footer>
        <Button label="Hủy" severity="secondary" text :disabled="savingCourse" @click="showAddCourseDialog = false" />
        <Button label="Thêm" :loading="savingCourse" @click="submitAddCourse" />
      </template>
    </Dialog>

    <Toast />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import Toast from 'primevue/toast'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'

import trainingService, {
  PLAN_STATUSES,
  type PlanRead,
  type PlanCourseRead,
  type PlanStatusValue,
  type CourseRead,
} from '@/services/trainingService'
import departmentService, { type DepartmentRead } from '@/services/departmentService'

const confirm = useConfirm()
const toast   = useToast()
const planStatusOptions = PLAN_STATUSES.map((option) => ({ ...option }))

// ── Options ───────────────────────────────────────────────────────────────────

const quarterOptions = [
  { value: 1, label: 'Q1' },
  { value: 2, label: 'Q2' },
  { value: 3, label: 'Q3' },
  { value: 4, label: 'Q4' },
]

// ── State ─────────────────────────────────────────────────────────────────────

const loading    = ref(false)
const items      = ref<PlanRead[]>([])
const total      = ref(0)
const page       = ref(1)
const pageSize   = ref(20)
const departments = ref<DepartmentRead[]>([])

const filterYear    = ref<number>(new Date().getFullYear())
const filterQuarter = ref<number | null>(null)
const filterDeptId  = ref<number | null>(null)
const filterStatus  = ref<PlanStatusValue | null>(null)

// Expand rows
const expandedRows      = ref<PlanRead[]>([])
const planCoursesMap    = ref<Record<number, PlanCourseRead[]>>({})
const planCoursesLoading = ref<Record<number, boolean>>({})

// Create plan dialog
const showCreateDialog = ref(false)
const saving           = ref(false)
const createPlanError  = ref('')
const planErrors       = ref<Record<string, string>>({})

const planForm = ref<{
  title: string
  year: number
  quarter: number | null
  department_id: number | null
  description: string
}>({
  title: '',
  year: new Date().getFullYear(),
  quarter: null,
  department_id: null,
  description: '',
})

// Edit plan dialog
const showEditDialog  = ref(false)
const editingPlanId   = ref<number | null>(null)
const savingEdit      = ref(false)
const editError       = ref('')
const editErrors      = ref<Record<string, string>>({})
const editForm        = ref({ title: '', description: '' })

// Add course dialog
const showAddCourseDialog  = ref(false)
const addCourseTargetPlanId = ref<number | null>(null)
const activeCourses        = ref<CourseRead[]>([])
const savingCourse         = ref(false)
const addCourseError       = ref('')
const addCourseErrors      = ref<Record<string, string>>({})

const addCourseForm = ref<{
  course_id: number | null
  target_count: number | null
  scheduled_date_obj: Date | null
  note: string
}>({
  course_id: null,
  target_count: null,
  scheduled_date_obj: null,
  note: '',
})

// ── Helpers ───────────────────────────────────────────────────────────────────

function planStatusSeverity(s: PlanStatusValue): 'secondary' | 'success' | 'danger' {
  if (s === 'approved')  return 'success'
  if (s === 'cancelled') return 'danger'
  return 'secondary'
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
    if (filterYear.value)    params.year          = filterYear.value
    if (filterQuarter.value) params.quarter       = filterQuarter.value
    if (filterDeptId.value)  params.department_id = filterDeptId.value
    if (filterStatus.value)  params.status        = filterStatus.value

    const res = await trainingService.listPlans(params)
    items.value = res.data.items
    total.value = res.data.total
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể tải danh sách kế hoạch', life: 4000 })
  } finally {
    loading.value = false
  }
}

function applyFilter() { page.value = 1; load() }

function reset() {
  filterYear.value    = new Date().getFullYear()
  filterQuarter.value = null
  filterDeptId.value  = null
  filterStatus.value  = null
  page.value = 1
  load()
}

function onPage(e: { page: number; rows: number }) {
  page.value     = e.page + 1
  pageSize.value = e.rows
  load()
}

// ── Expand rows ───────────────────────────────────────────────────────────────

async function onRowExpand({ data }: { data: PlanRead }) {
  if (planCoursesMap.value[data.id]) return  // already loaded
  planCoursesLoading.value[data.id] = true
  try {
    const res = await trainingService.listPlanCourses(data.id)
    planCoursesMap.value[data.id] = res.data
  } finally {
    planCoursesLoading.value[data.id] = false
  }
}

// ── Create plan dialog ────────────────────────────────────────────────────────

function openCreate() {
  createPlanError.value = ''
  planErrors.value = {}
  Object.assign(planForm.value, {
    title: '',
    year: new Date().getFullYear(),
    quarter: null,
    department_id: null,
    description: '',
  })
  showCreateDialog.value = true
}

function validatePlan(): boolean {
  planErrors.value = {}
  if (!planForm.value.title.trim()) planErrors.value.title = 'Vui lòng nhập tiêu đề'
  if (!planForm.value.year)         planErrors.value.year  = 'Vui lòng nhập năm'
  return Object.keys(planErrors.value).length === 0
}

async function submitPlan() {
  if (!validatePlan()) return
  saving.value = true
  createPlanError.value = ''
  try {
    await trainingService.createPlan({
      title:         planForm.value.title.trim(),
      year:          planForm.value.year,
      quarter:       planForm.value.quarter,
      department_id: planForm.value.department_id,
      description:   planForm.value.description.trim() || null,
    })
    toast.add({ severity: 'success', summary: 'Đã tạo', detail: 'Kế hoạch đào tạo đã được tạo', life: 3000 })
    showCreateDialog.value = false
    load()
  } catch (err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    createPlanError.value = typeof detail === 'string' ? detail : 'Có lỗi xảy ra, vui lòng thử lại'
  } finally {
    saving.value = false
  }
}

// ── Edit plan ─────────────────────────────────────────────────────────────────

function openEdit(plan: PlanRead) {
  editingPlanId.value = plan.id
  editError.value = ''
  editErrors.value = {}
  editForm.value = { title: plan.title, description: plan.description ?? '' }
  showEditDialog.value = true
}

async function submitEdit() {
  editErrors.value = {}
  if (!editForm.value.title.trim()) {
    editErrors.value.title = 'Vui lòng nhập tiêu đề'
    return
  }
  savingEdit.value = true
  editError.value = ''
  try {
    const updated = await trainingService.updatePlan(editingPlanId.value!, {
      title: editForm.value.title.trim(),
      description: editForm.value.description.trim() || null,
    })
    const idx = items.value.findIndex(p => p.id === editingPlanId.value)
    if (idx !== -1) items.value[idx] = updated.data
    toast.add({ severity: 'success', summary: 'Đã lưu', detail: 'Kế hoạch đã được cập nhật', life: 3000 })
    showEditDialog.value = false
  } catch (err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    editError.value = typeof detail === 'string' ? detail : 'Có lỗi xảy ra, vui lòng thử lại'
  } finally {
    savingEdit.value = false
  }
}

// ── Approve / Cancel / Delete ─────────────────────────────────────────────────

function approvePlan(plan: PlanRead) {
  confirm.require({
    message: `Duyệt kế hoạch "${plan.title}"?`,
    header: 'Xác nhận duyệt',
    icon: 'pi pi-check-circle',
    acceptLabel: 'Duyệt',
    rejectLabel: 'Hủy',
    accept: () => doApprovePlan(plan),
  })
}

async function doApprovePlan(plan: PlanRead) {
  try {
    await trainingService.approvePlan(plan.id)
    toast.add({ severity: 'success', summary: 'Đã duyệt', detail: 'Kế hoạch đã được duyệt', life: 3000 })
    delete planCoursesMap.value[plan.id]
    load()
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể duyệt kế hoạch', life: 4000 })
  }
}

function cancelPlan(plan: PlanRead) {
  confirm.require({
    message: `Hủy kế hoạch "${plan.title}"?`,
    header: 'Xác nhận hủy',
    icon: 'pi pi-ban',
    acceptLabel: 'Hủy KH',
    rejectLabel: 'Đóng',
    accept: () => doCancelPlan(plan),
  })
}

async function doCancelPlan(plan: PlanRead) {
  try {
    await trainingService.cancelPlan(plan.id)
    toast.add({ severity: 'success', summary: 'Đã hủy', detail: 'Kế hoạch đã được hủy', life: 3000 })
    delete planCoursesMap.value[plan.id]
    load()
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể hủy kế hoạch', life: 4000 })
  }
}

function confirmDelete(plan: PlanRead) {
  confirm.require({
    message: `Xóa kế hoạch "${plan.title}"?`,
    header: 'Xác nhận xóa',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Xóa',
    rejectLabel: 'Hủy',
    accept: () => doDeletePlan(plan),
  })
}

async function doDeletePlan(plan: PlanRead) {
  try {
    await trainingService.deletePlan(plan.id)
    toast.add({ severity: 'success', summary: 'Đã xóa', detail: 'Kế hoạch đã được xóa', life: 3000 })
    delete planCoursesMap.value[plan.id]
    load()
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể xóa kế hoạch', life: 4000 })
  }
}

// ── Add course to plan dialog ─────────────────────────────────────────────────

async function openAddCourse(planId: number) {
  addCourseTargetPlanId.value = planId
  addCourseError.value = ''
  addCourseErrors.value = {}
  Object.assign(addCourseForm.value, {
    course_id: null,
    target_count: null,
    scheduled_date_obj: null,
    note: '',
  })
  // Load active courses if not loaded yet
  if (activeCourses.value.length === 0) {
    try {
      const res = await trainingService.listCourses({ is_active: true, page_size: 500 })
      activeCourses.value = res.data.items
    } catch {
      toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể tải danh sách khóa học', life: 4000 })
      return
    }
  }
  showAddCourseDialog.value = true
}

function validateAddCourse(): boolean {
  addCourseErrors.value = {}
  if (!addCourseForm.value.course_id) addCourseErrors.value.course_id = 'Vui lòng chọn khóa học'
  return Object.keys(addCourseErrors.value).length === 0
}

async function submitAddCourse() {
  if (!validateAddCourse()) return
  savingCourse.value = true
  addCourseError.value = ''
  try {
    const planId = addCourseTargetPlanId.value!
    const newCourse = await trainingService.addCourseToPlan(planId, {
      course_id:      addCourseForm.value.course_id!,
      target_count:   addCourseForm.value.target_count,
      scheduled_date: addCourseForm.value.scheduled_date_obj
        ? toIso(addCourseForm.value.scheduled_date_obj)
        : null,
      note: addCourseForm.value.note.trim() || null,
    })
    // Update cached courses for this plan
    if (planCoursesMap.value[planId]) {
      planCoursesMap.value[planId] = [...planCoursesMap.value[planId], newCourse.data]
    }
    // Update course_count in items
    const planIdx = items.value.findIndex(p => p.id === planId)
    if (planIdx !== -1) {
      items.value[planIdx] = { ...items.value[planIdx], course_count: items.value[planIdx].course_count + 1 }
    }
    toast.add({ severity: 'success', summary: 'Đã thêm', detail: 'Khóa học đã được thêm vào kế hoạch', life: 3000 })
    showAddCourseDialog.value = false
  } catch (err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    addCourseError.value = typeof detail === 'string' ? detail : 'Có lỗi xảy ra, vui lòng thử lại'
  } finally {
    savingCourse.value = false
  }
}

function confirmRemoveCourse(planId: number, pc: PlanCourseRead) {
  confirm.require({
    message: `Xóa khóa học "${pc.course_name}" khỏi kế hoạch?`,
    header: 'Xác nhận xóa',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Xóa',
    rejectLabel: 'Hủy',
    accept: async () => {
      try {
        await trainingService.removeFromPlan(planId, pc.course_id)
        // Update cached list
        if (planCoursesMap.value[planId]) {
          planCoursesMap.value[planId] = planCoursesMap.value[planId].filter(c => c.id !== pc.id)
        }
        // Update course_count
        const planIdx = items.value.findIndex(p => p.id === planId)
        if (planIdx !== -1) {
          items.value[planIdx] = { ...items.value[planIdx], course_count: Math.max(0, items.value[planIdx].course_count - 1) }
        }
        toast.add({ severity: 'success', summary: 'Đã xóa', detail: 'Đã xóa khóa học khỏi kế hoạch', life: 3000 })
      } catch {
        toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể xóa khóa học khỏi kế hoạch', life: 4000 })
      }
    },
  })
}

// ── Init ──────────────────────────────────────────────────────────────────────

onMounted(async () => {
  try {
    const deptsRes = await departmentService.getList(true)
    departments.value = deptsRes.data
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể tải danh sách phòng ban', life: 4000 })
  }
  load()
})
</script>
