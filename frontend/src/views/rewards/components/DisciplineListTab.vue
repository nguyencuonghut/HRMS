<template>
  <div>
    <!-- Toolbar -->
    <div class="rewards-toolbar">
      <IconField class="rewards-search">
        <InputIcon class="pi pi-search" />
        <InputText
          v-model="filterSearch"
          placeholder="Tìm mã NV, tên, số QĐ..."
          @keyup.enter="applyFilter"
        />
      </IconField>

      <Select
        v-model="filterDeptId"
        :options="departments"
        option-label="name"
        option-value="id"
        placeholder="Tất cả phòng ban"
        show-clear
        filter
        style="width: 210px"
      />

      <Select
        v-model="filterForm"
        :options="DISCIPLINE_FORMS"
        option-label="label"
        option-value="value"
        placeholder="Tất cả hình thức"
        show-clear
        filter
        style="width: 220px"
      />

      <DatePicker
        v-model="filterFromDate"
        date-format="dd/mm/yy"
        placeholder="Từ ngày HLực"
        show-button-bar
        style="width: 155px"
      />
      <DatePicker
        v-model="filterToDate"
        date-format="dd/mm/yy"
        placeholder="Đến ngày HLực"
        show-button-bar
        style="width: 155px"
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
        label="Thêm quyết định"
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
          <div class="rewards-empty">Không có dữ liệu</div>
        </template>

        <Column header="Nhân viên" style="min-width: 200px">
          <template #body="{ data }: { data: DisciplineRead }">
            <span class="rewards-emp-code">{{ data.employee_code }}</span>
            <span class="rewards-emp-sep">·</span>
            <span class="rewards-emp-name">{{ data.employee_name }}</span>
            <div v-if="data.department_name" class="rewards-emp-dept">{{ data.department_name }}</div>
          </template>
        </Column>

        <Column header="Hình thức kỷ luật" style="min-width: 180px">
          <template #body="{ data }: { data: DisciplineRead }">
            <Tag
              :value="data.discipline_form_label"
              :severity="formSeverity(data.discipline_form)"
              :class="['rewards-type-tag', data.discipline_form === 'cach_chuc' ? 'disc-tag-cach-chuc' : '']"
            />
          </template>
        </Column>

        <Column header="Tiêu đề" style="min-width: 200px">
          <template #body="{ data }: { data: DisciplineRead }">
            <span>{{ data.title }}</span>
            <div v-if="data.decision_number" class="rewards-decision-num">
              QĐ: {{ data.decision_number }}
            </div>
          </template>
        </Column>

        <Column header="Ngày vi phạm" style="width: 120px">
          <template #body="{ data }: { data: DisciplineRead }">
            {{ fmtDate(data.violation_date) }}
          </template>
        </Column>

        <Column header="Ngày HLực" style="width: 110px">
          <template #body="{ data }: { data: DisciplineRead }">
            {{ fmtDate(data.effective_date) }}
          </template>
        </Column>

        <Column header="Hết HLực" style="width: 110px">
          <template #body="{ data }: { data: DisciplineRead }">
            <span v-if="data.end_date">{{ fmtDate(data.end_date) }}</span>
            <span v-else class="rewards-muted">—</span>
          </template>
        </Column>

        <Column header="File" style="width: 60px; text-align: center">
          <template #body="{ data }: { data: DisciplineRead }">
            <Button
              v-if="data.has_file"
              icon="pi pi-paperclip"
              severity="secondary"
              text
              rounded
              size="small"
              v-tooltip.top="data.file_name ?? 'Tải file'"
              @click="downloadFile(data)"
            />
            <span v-else class="rewards-muted">—</span>
          </template>
        </Column>

        <Column header="" style="width: 90px; text-align: right">
          <template #body="{ data }: { data: DisciplineRead }">
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
      :header="editingId ? 'Sửa quyết định kỷ luật' : 'Thêm quyết định kỷ luật'"
      modal
      :style="{ width: '620px' }"
      :closable="!saving"
    >
      <div class="rewards-form">
        <!-- Nhân viên -->
        <div class="rewards-field">
          <label class="rewards-label">Nhân viên <span class="rewards-req">*</span></label>
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
          >
            <template #option="{ option }">
              <span class="rewards-emp-code">{{ option.display_code }}</span>
              <span class="rewards-emp-sep">·</span>
              {{ option.full_name }}
            </template>
          </Select>
          <span v-if="errors.employee_id" class="rewards-error">{{ errors.employee_id }}</span>
        </div>

        <!-- Hình thức kỷ luật -->
        <div class="rewards-field">
          <label class="rewards-label">Hình thức kỷ luật <span class="rewards-req">*</span></label>
          <Select
            v-model="form.discipline_form"
            :options="DISCIPLINE_FORMS"
            option-label="label"
            option-value="value"
            placeholder="Chọn hình thức..."
            filter
            class="w-full"
            @change="onFormChange"
          />
          <span v-if="errors.discipline_form" class="rewards-error">{{ errors.discipline_form }}</span>
        </div>

        <!-- Ngày vi phạm + Ngày hiệu lực -->
        <div class="rewards-row">
          <div class="rewards-field">
            <label class="rewards-label">Ngày vi phạm <span class="rewards-req">*</span></label>
            <DatePicker
              v-model="form.violation_date_obj"
              date-format="dd/mm/yy"
              placeholder="DD/MM/YYYY"
              show-button-bar
              class="w-full"
            />
            <span v-if="errors.violation_date" class="rewards-error">{{ errors.violation_date }}</span>
          </div>
          <div class="rewards-field">
            <label class="rewards-label">Ngày hiệu lực <span class="rewards-req">*</span></label>
            <DatePicker
              v-model="form.effective_date_obj"
              date-format="dd/mm/yy"
              placeholder="DD/MM/YYYY"
              show-button-bar
              class="w-full"
              @update:model-value="recalcEndDate"
            />
            <span v-if="errors.effective_date" class="rewards-error">{{ errors.effective_date }}</span>
          </div>
        </div>

        <!-- Số tháng KD (chỉ khi keo_dai_nang_luong) -->
        <div v-if="form.discipline_form === 'keo_dai_nang_luong'" class="rewards-row">
          <div class="rewards-field">
            <label class="rewards-label">Số tháng kéo dài <span class="rewards-req">*</span></label>
            <InputNumber
              v-model="form.extended_months"
              :min="1"
              :max="12"
              mode="decimal"
              placeholder="1–12"
              class="w-full"
              @update:model-value="recalcEndDate"
            />
            <span v-if="errors.extended_months" class="rewards-error">{{ errors.extended_months }}</span>
          </div>
          <div class="rewards-field">
            <label class="rewards-label">Hết hiệu lực (tự tính)</label>
            <div class="disc-end-date-preview">
              {{ endDatePreview || '—' }}
            </div>
          </div>
        </div>

        <!-- Tiêu đề -->
        <div class="rewards-field">
          <label class="rewards-label">Tiêu đề vi phạm <span class="rewards-req">*</span></label>
          <InputText v-model="form.title" placeholder="VD: Đi làm muộn liên tục tháng 05/2026" class="w-full" />
          <span v-if="errors.title" class="rewards-error">{{ errors.title }}</span>
        </div>

        <!-- Số QĐ + Đơn vị ký -->
        <div class="rewards-row">
          <div class="rewards-field">
            <label class="rewards-label">Số quyết định <span class="rewards-optional">(tùy chọn)</span></label>
            <InputText v-model="form.decision_number" placeholder="VD: 01/QĐ-KL-2026" class="w-full" />
          </div>
          <div class="rewards-field">
            <label class="rewards-label">Đơn vị/Người ký <span class="rewards-optional">(tùy chọn)</span></label>
            <InputText v-model="form.issued_by" placeholder="VD: Ban Giám đốc" class="w-full" />
          </div>
        </div>

        <!-- Mô tả -->
        <div class="rewards-field">
          <label class="rewards-label">Mô tả chi tiết vi phạm <span class="rewards-optional">(tùy chọn)</span></label>
          <Textarea v-model="form.description" rows="3" class="w-full" placeholder="Mô tả hành vi vi phạm..." auto-resize />
        </div>

        <!-- Ghi chú -->
        <div class="rewards-field">
          <label class="rewards-label">Ghi chú <span class="rewards-optional">(tùy chọn)</span></label>
          <InputText v-model="form.note" class="w-full" placeholder="Ghi chú thêm..." />
        </div>

        <!-- File BB/QĐ -->
        <div class="rewards-field">
          <label class="rewards-label">File biên bản/quyết định <span class="rewards-optional">(PDF/Word/Ảnh, tối đa 10MB)</span></label>
          <div class="rewards-file-row">
            <input
              ref="fileInputRef"
              type="file"
              accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
              style="display: none"
              @change="onFileChange"
            />
            <Button
              icon="pi pi-upload"
              label="Chọn file"
              severity="secondary"
              outlined
              size="small"
              @click="fileInputRef?.click()"
            />
            <span v-if="selectedFile" class="rewards-file-name">{{ selectedFile.name }}</span>
            <span v-else-if="existingFileName" class="rewards-file-name rewards-muted">
              <i class="pi pi-paperclip" style="font-size: 0.8rem" />
              {{ existingFileName }}
            </span>
            <Button
              v-if="selectedFile || existingFileName"
              icon="pi pi-times"
              text rounded size="small" severity="danger"
              v-tooltip.top="'Xóa file'"
              @click="clearFile"
            />
          </div>
        </div>

        <p v-if="dialogError" class="rewards-api-error">
          <i class="pi pi-exclamation-triangle" />
          {{ dialogError }}
        </p>
      </div>

      <template #footer>
        <Button label="Hủy" severity="secondary" text :disabled="saving" @click="showDialog = false" />
        <Button :label="editingId ? 'Lưu thay đổi' : 'Thêm'" :loading="saving" @click="submit" />
      </template>
    </Dialog>

    <ConfirmDialog />
    <Toast />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import ConfirmDialog from 'primevue/confirmdialog'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
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

import disciplineService, {
  DISCIPLINE_FORMS,
  type DisciplineRead,
  type DisciplineCreate,
  type DisciplineFormValue,
} from '@/services/disciplineService'
import departmentService, { type DepartmentRead } from '@/services/departmentService'
import employeeService, { type EmployeeLookupItem } from '@/services/employeeService'

const confirm = useConfirm()
const toast   = useToast()

// ── State ─────────────────────────────────────────────────────────────────────

const loading  = ref(false)
const items    = ref<DisciplineRead[]>([])
const total    = ref(0)
const page     = ref(1)
const pageSize = ref(20)

const departments = ref<DepartmentRead[]>([])
const employees   = ref<EmployeeLookupItem[]>([])

const filterSearch   = ref('')
const filterDeptId   = ref<number | null>(null)
const filterForm     = ref<DisciplineFormValue | null>(null)
const filterFromDate = ref<Date | null>(null)
const filterToDate   = ref<Date | null>(null)

const showDialog       = ref(false)
const saving           = ref(false)
const editingId        = ref<number | null>(null)
const dialogError      = ref('')
const existingFileName = ref<string | null>(null)
const selectedFile     = ref<File | null>(null)
const fileInputRef     = ref<HTMLInputElement | null>(null)
const errors           = ref<Record<string, string>>({})

const form = ref<{
  employee_id: number | null
  discipline_form: DisciplineFormValue | null
  violation_date_obj: Date | null
  effective_date_obj: Date | null
  extended_months: number | null
  title: string
  description: string
  decision_number: string
  issued_by: string
  note: string
}>({
  employee_id: null,
  discipline_form: null,
  violation_date_obj: null,
  effective_date_obj: null,
  extended_months: null,
  title: '',
  description: '',
  decision_number: '',
  issued_by: '',
  note: '',
})

// ── Computed ──────────────────────────────────────────────────────────────────

const endDatePreview = computed(() => {
  if (form.value.discipline_form !== 'keo_dai_nang_luong') return null
  if (!form.value.effective_date_obj || !form.value.extended_months) return null
  const d = new Date(form.value.effective_date_obj)
  d.setMonth(d.getMonth() + form.value.extended_months)
  return fmtDate(toIso(d))
})

// ── Helpers ───────────────────────────────────────────────────────────────────

function formSeverity(form: DisciplineFormValue): 'success' | 'warn' | 'danger' | 'info' {
  if (form === 'khien_trach')        return 'success'
  if (form === 'keo_dai_nang_luong') return 'warn'
  return 'danger'
}

function toIso(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function fmtDate(s: string): string {
  if (!s) return '—'
  const [y, m, d] = s.split('-')
  return `${d}/${m}/${y}`
}

// ── Load ──────────────────────────────────────────────────────────────────────

async function load() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: page.value, page_size: pageSize.value }
    if (filterSearch.value)   params.search          = filterSearch.value
    if (filterDeptId.value)   params.department_id   = filterDeptId.value
    if (filterForm.value)     params.discipline_form  = filterForm.value
    if (filterFromDate.value) params.from_date        = toIso(filterFromDate.value)
    if (filterToDate.value)   params.to_date          = toIso(filterToDate.value)

    const res = await disciplineService.list(params)
    items.value = res.data.items
    total.value = res.data.total
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể tải danh sách kỷ luật', life: 4000 })
  } finally {
    loading.value = false
  }
}

function applyFilter() { page.value = 1; load() }

function reset() {
  filterSearch.value = ''
  filterDeptId.value = null
  filterForm.value   = null
  filterFromDate.value = null
  filterToDate.value   = null
  page.value = 1
  load()
}

function onPage(e: { page: number; rows: number }) {
  page.value = e.page + 1
  pageSize.value = e.rows
  load()
}

// ── Dialog ────────────────────────────────────────────────────────────────────

function openCreate() {
  editingId.value = null
  existingFileName.value = null
  selectedFile.value = null
  dialogError.value = ''
  errors.value = {}
  Object.assign(form.value, {
    employee_id: null, discipline_form: null,
    violation_date_obj: new Date(), effective_date_obj: new Date(),
    extended_months: null, title: '',
    description: '', decision_number: '', issued_by: '', note: '',
  })
  showDialog.value = true
}

function openEdit(row: DisciplineRead) {
  editingId.value = row.id
  existingFileName.value = row.has_file ? (row.file_name ?? 'file') : null
  selectedFile.value = null
  dialogError.value = ''
  errors.value = {}
  Object.assign(form.value, {
    employee_id:        row.employee_id,
    discipline_form:    row.discipline_form,
    violation_date_obj: new Date(row.violation_date),
    effective_date_obj: new Date(row.effective_date),
    extended_months:    row.extended_months ?? null,
    title:              row.title,
    description:        row.description ?? '',
    decision_number:    row.decision_number ?? '',
    issued_by:          row.issued_by ?? '',
    note:               row.note ?? '',
  })
  showDialog.value = true
}

function onFormChange() {
  if (form.value.discipline_form !== 'keo_dai_nang_luong') {
    form.value.extended_months = null
  }
}

function recalcEndDate() { /* endDatePreview is computed, no-op */ }

function onFileChange(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (f) { selectedFile.value = f; existingFileName.value = null }
}

function clearFile() {
  selectedFile.value = null
  existingFileName.value = null
  if (fileInputRef.value) fileInputRef.value.value = ''
}

function validate(): boolean {
  errors.value = {}
  if (!form.value.employee_id)     errors.value.employee_id     = 'Vui lòng chọn nhân viên'
  if (!form.value.discipline_form) errors.value.discipline_form = 'Vui lòng chọn hình thức kỷ luật'
  if (!form.value.violation_date_obj) errors.value.violation_date = 'Vui lòng chọn ngày vi phạm'
  if (!form.value.effective_date_obj) errors.value.effective_date = 'Vui lòng chọn ngày hiệu lực'
  if (!form.value.title.trim())    errors.value.title           = 'Vui lòng nhập tiêu đề'
  if (form.value.discipline_form === 'keo_dai_nang_luong' && !form.value.extended_months)
    errors.value.extended_months = 'Vui lòng nhập số tháng kéo dài'
  return Object.keys(errors.value).length === 0
}

async function submit() {
  if (!validate()) return
  saving.value = true
  dialogError.value = ''
  try {
    const payload: DisciplineCreate = {
      employee_id:     form.value.employee_id!,
      discipline_form: form.value.discipline_form!,
      violation_date:  toIso(form.value.violation_date_obj!),
      effective_date:  toIso(form.value.effective_date_obj!),
      extended_months: form.value.discipline_form === 'keo_dai_nang_luong' ? form.value.extended_months : null,
      title:           form.value.title.trim(),
      description:     form.value.description.trim() || null,
      decision_number: form.value.decision_number.trim() || null,
      issued_by:       form.value.issued_by.trim() || null,
      note:            form.value.note.trim() || null,
    }
    if (editingId.value) {
      await disciplineService.update(editingId.value, payload, selectedFile.value)
      toast.add({ severity: 'success', summary: 'Đã cập nhật', detail: 'Quyết định kỷ luật đã được cập nhật', life: 3000 })
    } else {
      await disciplineService.create(payload, selectedFile.value)
      toast.add({ severity: 'success', summary: 'Đã thêm', detail: 'Quyết định kỷ luật đã được tạo', life: 3000 })
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

function confirmDelete(row: DisciplineRead) {
  confirm.require({
    message: `Xóa quyết định kỷ luật "${row.title}" của ${row.employee_name}?`,
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
    await disciplineService.delete(id)
    toast.add({ severity: 'success', summary: 'Đã xóa', detail: 'Quyết định kỷ luật đã được xóa', life: 3000 })
    load()
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể xóa quyết định', life: 4000 })
  }
}

// ── File download ─────────────────────────────────────────────────────────────

async function downloadFile(row: DisciplineRead) {
  try {
    const res = await disciplineService.downloadFile(row.id)
    const url = URL.createObjectURL(new Blob([res.data as BlobPart]))
    const a = document.createElement('a')
    a.href = url
    a.download = row.file_name ?? `discipline_${row.id}`
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể tải file', life: 3000 })
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
