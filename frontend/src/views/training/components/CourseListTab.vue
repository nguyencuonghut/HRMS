<template>
  <div>
    <!-- Toolbar -->
    <div class="training-toolbar">
      <IconField class="training-search">
        <InputIcon class="pi pi-search" />
        <InputText
          v-model="filterSearch"
          placeholder="Tìm mã, tên, đơn vị tổ chức..."
          @keyup.enter="applyFilter"
        />
      </IconField>

      <Select
        v-model="filterCourseType"
        :options="courseTypeOptions"
        option-label="label"
        option-value="value"
        placeholder="Tất cả loại"
        show-clear
        filter
        style="width: 180px"
      />

      <Select
        v-model="filterMandatory"
        :options="mandatoryOptions"
        option-label="label"
        option-value="value"
        placeholder="Bắt buộc?"
        show-clear
        filter
        style="width: 140px"
      />

      <Select
        v-model="filterActive"
        :options="activeOptions"
        option-label="label"
        option-value="value"
        placeholder="Trạng thái"
        show-clear
        filter
        style="width: 150px"
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
        label="Thêm khóa học"
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
        @page="onPage"
      >
        <template #empty>
          <div class="training-empty">Không có dữ liệu khóa học</div>
        </template>

        <Column header="STT" style="width: 50px; text-align: center">
          <template #body="{ index }">
            {{ (page - 1) * pageSize + index + 1 }}
          </template>
        </Column>

        <Column header="Mã KH" style="width: 110px">
          <template #body="{ data }: { data: CourseRead }">
            <span class="emp-code">{{ data.code }}</span>
          </template>
        </Column>

        <Column header="Tên khóa học" style="min-width: 200px">
          <template #body="{ data }: { data: CourseRead }">
            {{ data.name }}
          </template>
        </Column>

        <Column header="Loại" style="width: 120px">
          <template #body="{ data }: { data: CourseRead }">
            <Tag
              :value="data.course_type_label"
              :severity="courseTypeSeverity(data.course_type)"
              class="training-type-tag"
            />
          </template>
        </Column>

        <Column header="Thời lượng" style="width: 110px; text-align: center">
          <template #body="{ data }: { data: CourseRead }">
            <span v-if="data.duration_hours">{{ data.duration_hours }} giờ</span>
            <span v-else class="muted-text">—</span>
          </template>
        </Column>

        <Column header="Đơn vị tổ chức" style="min-width: 150px">
          <template #body="{ data }: { data: CourseRead }">
            <span v-if="data.organizer">{{ data.organizer }}</span>
            <span v-else class="muted-text">—</span>
          </template>
        </Column>

        <Column header="Chi phí/người" style="width: 130px; text-align: right">
          <template #body="{ data }: { data: CourseRead }">
            <span class="right-text">{{ fmtVND(data.cost_per_person) }}</span>
          </template>
        </Column>

        <Column header="Bắt buộc" style="width: 90px; text-align: center">
          <template #body="{ data }: { data: CourseRead }">
            <Tag
              :value="data.is_mandatory ? 'Có' : 'Không'"
              :severity="data.is_mandatory ? 'danger' : 'secondary'"
              class="training-type-tag"
            />
          </template>
        </Column>

        <Column header="Trạng thái" style="width: 110px; text-align: center">
          <template #body="{ data }: { data: CourseRead }">
            <Tag
              :value="data.is_active ? 'Hoạt động' : 'Ngừng'"
              :severity="data.is_active ? 'success' : 'secondary'"
              class="training-type-tag"
            />
          </template>
        </Column>

        <Column header="" style="width: 90px; text-align: right">
          <template #body="{ data }: { data: CourseRead }">
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

    <!-- Dialog tạo/sửa -->
    <Dialog
      v-model:visible="showDialog"
      :header="editingId ? 'Sửa khóa học' : 'Thêm khóa học'"
      modal
      :style="{ width: '640px' }"
      :closable="!saving"
    >
      <div class="training-form">
        <!-- Row 1: Mã + Tên -->
        <div class="training-row">
          <div class="training-field">
            <label class="training-label">Mã khóa học <span class="training-req">*</span></label>
            <InputText v-model="form.code" placeholder="VD: KH001" class="w-full" />
            <span v-if="errors.code" class="training-error">{{ errors.code }}</span>
          </div>
          <div class="training-field">
            <label class="training-label">Tên khóa học <span class="training-req">*</span></label>
            <InputText v-model="form.name" placeholder="Tên khóa học..." class="w-full" />
            <span v-if="errors.name" class="training-error">{{ errors.name }}</span>
          </div>
        </div>

        <!-- Row 2: Loại + Số giờ -->
        <div class="training-row">
          <div class="training-field">
            <label class="training-label">Loại đào tạo <span class="training-req">*</span></label>
            <Select
              v-model="form.course_type"
              :options="courseTypeOptions"
              option-label="label"
              option-value="value"
              placeholder="Chọn loại..."
              filter
              class="w-full"
            />
            <span v-if="errors.course_type" class="training-error">{{ errors.course_type }}</span>
          </div>
          <div class="training-field">
            <label class="training-label">Số giờ</label>
            <InputNumber
              v-model="form.duration_hours"
              :min="1"
              placeholder="Số giờ học"
              class="w-full"
            />
          </div>
        </div>

        <!-- Row 3: Đơn vị tổ chức + Chi phí -->
        <div class="training-row">
          <div class="training-field">
            <label class="training-label">Đơn vị tổ chức</label>
            <InputText v-model="form.organizer" placeholder="VD: Công ty ABC" class="w-full" />
          </div>
          <div class="training-field">
            <label class="training-label">Chi phí/người (VNĐ)</label>
            <InputNumber
              v-model="form.cost_per_person"
              :min="0"
              mode="decimal"
              :use-grouping="true"
              placeholder="0"
              class="w-full"
            />
          </div>
        </div>

        <!-- Mô tả -->
        <div class="training-field">
          <label class="training-label">Mô tả</label>
          <Textarea v-model="form.description" rows="3" class="w-full" auto-resize placeholder="Mô tả khóa học..." />
        </div>

        <!-- Checkboxes -->
        <div class="training-field">
          <div class="switch-row">
            <Checkbox v-model="form.is_mandatory" binary input-id="chk_mandatory" />
            <label for="chk_mandatory" class="training-label" style="margin: 0; cursor: pointer">Đào tạo bắt buộc</label>
          </div>
        </div>

        <div v-if="editingId" class="training-field">
          <div class="switch-row">
            <Checkbox v-model="form.is_active" binary input-id="chk_active" />
            <label for="chk_active" class="training-label" style="margin: 0; cursor: pointer">Đang hoạt động</label>
          </div>
        </div>

        <p v-if="dialogError" class="training-api-error">
          <i class="pi pi-exclamation-triangle" />
          {{ dialogError }}
        </p>
      </div>

      <template #footer>
        <Button label="Hủy" severity="secondary" text :disabled="saving" @click="showDialog = false" />
        <Button :label="editingId ? 'Lưu thay đổi' : 'Thêm'" :loading="saving" @click="submit" />
      </template>
    </Dialog>

    <Toast />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
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
import Toast from 'primevue/toast'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'

import trainingService, {
  COURSE_TYPES,
  type CourseRead,
  type CourseTypeValue,
} from '@/services/trainingService'

const confirm = useConfirm()
const toast   = useToast()
const courseTypeOptions = COURSE_TYPES.map((option) => ({ ...option }))

// ── Options ───────────────────────────────────────────────────────────────────

const mandatoryOptions = [
  { value: true,  label: 'Có' },
  { value: false, label: 'Không' },
]

const activeOptions = [
  { value: true,  label: 'Hoạt động' },
  { value: false, label: 'Ngừng' },
]

// ── State ─────────────────────────────────────────────────────────────────────

const loading  = ref(false)
const items    = ref<CourseRead[]>([])
const total    = ref(0)
const page     = ref(1)
const pageSize = ref(20)

const filterSearch     = ref('')
const filterCourseType = ref<CourseTypeValue | null>(null)
const filterMandatory  = ref<boolean | null>(null)
const filterActive     = ref<boolean | null>(null)

const showDialog  = ref(false)
const saving      = ref(false)
const editingId   = ref<number | null>(null)
const dialogError = ref('')
const errors      = ref<Record<string, string>>({})

const form = ref<{
  code: string
  name: string
  course_type: CourseTypeValue | null
  duration_hours: number | null
  organizer: string
  description: string
  cost_per_person: number | null
  is_mandatory: boolean
  is_active: boolean
}>({
  code: '',
  name: '',
  course_type: null,
  duration_hours: null,
  organizer: '',
  description: '',
  cost_per_person: null,
  is_mandatory: false,
  is_active: true,
})

// ── Helpers ───────────────────────────────────────────────────────────────────

function courseTypeSeverity(t: CourseTypeValue): 'info' | 'warn' | 'success' {
  if (t === 'noi_bo')    return 'info'
  if (t === 'ben_ngoai') return 'warn'
  return 'success'
}

function fmtVND(val: string | number | null | undefined): string {
  if (val === null || val === undefined) return '—'
  return Number(val).toLocaleString('vi-VN') + ' đ'
}

// ── Load ──────────────────────────────────────────────────────────────────────

async function load() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: page.value, page_size: pageSize.value }
    if (filterSearch.value)          params.search       = filterSearch.value
    if (filterCourseType.value)      params.course_type  = filterCourseType.value
    if (filterMandatory.value !== null) params.is_mandatory = filterMandatory.value
    if (filterActive.value !== null)    params.is_active    = filterActive.value

    const res = await trainingService.listCourses(params)
    items.value = res.data.items
    total.value = res.data.total
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể tải danh sách khóa học', life: 4000 })
  } finally {
    loading.value = false
  }
}

function applyFilter() { page.value = 1; load() }

function reset() {
  filterSearch.value     = ''
  filterCourseType.value = null
  filterMandatory.value  = null
  filterActive.value     = null
  page.value = 1
  load()
}

function onPage(e: { page: number; rows: number }) {
  page.value     = e.page + 1
  pageSize.value = e.rows
  load()
}

// ── Dialog ────────────────────────────────────────────────────────────────────

function openCreate() {
  editingId.value = null
  dialogError.value = ''
  errors.value = {}
  Object.assign(form.value, {
    code: '', name: '', course_type: null,
    duration_hours: null, organizer: '', description: '',
    cost_per_person: null, is_mandatory: false, is_active: true,
  })
  showDialog.value = true
}

function openEdit(row: CourseRead) {
  editingId.value   = row.id
  dialogError.value = ''
  errors.value      = {}
  Object.assign(form.value, {
    code:            row.code,
    name:            row.name,
    course_type:     row.course_type,
    duration_hours:  row.duration_hours,
    organizer:       row.organizer ?? '',
    description:     row.description ?? '',
    cost_per_person: row.cost_per_person !== null ? Number(row.cost_per_person) : null,
    is_mandatory:    row.is_mandatory,
    is_active:       row.is_active,
  })
  showDialog.value = true
}

function validate(): boolean {
  errors.value = {}
  if (!form.value.code.trim())   errors.value.code        = 'Vui lòng nhập mã khóa học'
  if (!form.value.name.trim())   errors.value.name        = 'Vui lòng nhập tên khóa học'
  if (!form.value.course_type)   errors.value.course_type = 'Vui lòng chọn loại đào tạo'
  return Object.keys(errors.value).length === 0
}

async function submit() {
  if (!validate()) return
  saving.value      = true
  dialogError.value = ''
  try {
    if (editingId.value) {
      await trainingService.updateCourse(editingId.value, {
        code:            form.value.code.trim(),
        name:            form.value.name.trim(),
        course_type:     form.value.course_type!,
        duration_hours:  form.value.duration_hours,
        organizer:       form.value.organizer.trim() || null,
        description:     form.value.description.trim() || null,
        cost_per_person: form.value.cost_per_person,
        is_mandatory:    form.value.is_mandatory,
        is_active:       form.value.is_active,
      })
      toast.add({ severity: 'success', summary: 'Đã cập nhật', detail: 'Khóa học đã được cập nhật', life: 3000 })
    } else {
      await trainingService.createCourse({
        code:            form.value.code.trim(),
        name:            form.value.name.trim(),
        course_type:     form.value.course_type!,
        duration_hours:  form.value.duration_hours,
        organizer:       form.value.organizer.trim() || null,
        description:     form.value.description.trim() || null,
        cost_per_person: form.value.cost_per_person,
        is_mandatory:    form.value.is_mandatory,
      })
      toast.add({ severity: 'success', summary: 'Đã thêm', detail: 'Khóa học đã được tạo', life: 3000 })
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

function confirmDelete(row: CourseRead) {
  confirm.require({
    message: `Xóa khóa học "${row.name}" (${row.code})?`,
    header: 'Xác nhận xóa',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Xóa',
    rejectLabel: 'Hủy',
    accept: () => doDelete(row.id),
  })
}

async function doDelete(id: number) {
  try {
    await trainingService.deleteCourse(id)
    toast.add({ severity: 'success', summary: 'Đã xóa', detail: 'Khóa học đã được xóa', life: 3000 })
    load()
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể xóa khóa học', life: 4000 })
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────

onMounted(() => { load() })
</script>
