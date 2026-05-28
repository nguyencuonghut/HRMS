<template>
  <div>
    <!-- Alert banner: sắp hết hạn -->
    <Message v-if="expiringSoonTotal > 0" severity="warn" :closable="false" class="mb-3">
      Có <strong>{{ expiringSoonTotal }}</strong> chứng chỉ sắp hết hạn trong 30 ngày tới.
      <a class="cert-link" @click="filterByExpiry('expiring_soon')">Xem danh sách</a>
    </Message>

    <!-- Toolbar -->
    <div class="training-toolbar">
      <IconField>
        <InputIcon class="pi pi-search" />
        <InputText
          v-model="searchText"
          placeholder="Tên chứng chỉ / mã NV / tên NV..."
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
        v-model="filterExpiryStatus"
        :options="expiryStatusOptions"
        option-label="label"
        option-value="value"
        placeholder="Trạng thái"
        show-clear
        filter
        style="width: 170px"
        @change="applyFilter"
      />

      <DatePicker
        v-model="filterFromIssued"
        date-format="dd/mm/yy"
        placeholder="Ngày cấp từ"
        show-button-bar
        style="width: 145px"
        @date-select="applyFilter"
        @clear-click="applyFilter"
      />

      <DatePicker
        v-model="filterToIssued"
        date-format="dd/mm/yy"
        placeholder="Ngày cấp đến"
        show-button-bar
        style="width: 145px"
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
        label="Thêm chứng chỉ"
        icon="pi pi-plus"
        class="ml-auto"
        @click="openCreateDialog"
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
          <div class="training-empty">Không có chứng chỉ nào</div>
        </template>

        <Column header="Nhân viên" style="min-width: 180px">
          <template #body="{ data }: { data: CertificateRead }">
            <span class="emp-code" style="margin-right: 0.4rem">{{ data.employee_code }}</span>
            {{ data.employee_name }}
          </template>
        </Column>

        <Column header="Phòng ban" style="min-width: 130px">
          <template #body="{ data }: { data: CertificateRead }">
            <span v-if="data.department_name">{{ data.department_name }}</span>
            <span v-else class="muted-text">—</span>
          </template>
        </Column>

        <Column header="Tên chứng chỉ" style="min-width: 200px">
          <template #body="{ data }: { data: CertificateRead }">
            {{ data.certificate_name }}
          </template>
        </Column>

        <Column header="Tổ chức cấp" style="min-width: 150px">
          <template #body="{ data }: { data: CertificateRead }">
            <span v-if="data.issuing_organization">{{ data.issuing_organization }}</span>
            <span v-else class="muted-text">—</span>
          </template>
        </Column>

        <Column header="Ngày cấp" style="width: 110px">
          <template #body="{ data }: { data: CertificateRead }">
            {{ fmtDate(data.issued_date) }}
          </template>
        </Column>

        <Column header="Hết hạn" style="width: 120px">
          <template #body="{ data }: { data: CertificateRead }">
            <span v-if="data.expiry_date">{{ fmtDate(data.expiry_date) }}</span>
            <span v-else class="muted-text">Vĩnh viễn</span>
          </template>
        </Column>

        <Column header="Trạng thái" style="width: 130px">
          <template #body="{ data }: { data: CertificateRead }">
            <Tag
              :value="expiryLabel(data.expiry_status)"
              :severity="expirySeverity(data.expiry_status)"
              class="training-type-tag"
            />
          </template>
        </Column>

        <Column header="File" style="width: 60px; text-align: center">
          <template #body="{ data }: { data: CertificateRead }">
            <Button
              v-if="data.has_file"
              icon="pi pi-download"
              text
              rounded
              size="small"
              severity="secondary"
              v-tooltip.top="'Tải file'"
              @click="doDownload(data)"
            />
            <span v-else class="muted-text">—</span>
          </template>
        </Column>

        <Column header="" style="width: 80px; text-align: right">
          <template #body="{ data }: { data: CertificateRead }">
            <Button
              icon="pi pi-pencil"
              text rounded size="small" severity="secondary"
              v-tooltip.top="'Sửa'"
              @click="openEditDialog(data)"
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
      :header="editingId ? 'Sửa chứng chỉ' : 'Thêm chứng chỉ'"
      modal
      :style="{ width: '540px' }"
      :closable="!saving"
    >
      <div class="training-form">
        <div class="training-field">
          <label class="training-label">Nhân viên <span class="training-req">*</span></label>
          <Select
            v-model="form.employee_id"
            :options="employeeLookup"
            option-label="full_name"
            option-value="id"
            placeholder="Tìm nhân viên..."
            filter
            :filter-fields="['display_code', 'full_name']"
            class="w-full"
            :disabled="!!editingId"
          >
            <template #option="{ option }: { option: EmployeeLookupItem }">
              <span class="emp-code" style="margin-right: 0.4rem">{{ option.display_code }}</span>
              {{ option.full_name }}
            </template>
          </Select>
          <span v-if="errors.employee_id" class="training-error">{{ errors.employee_id }}</span>
        </div>

        <div class="training-field">
          <label class="training-label">Tên chứng chỉ <span class="training-req">*</span></label>
          <InputText v-model="form.certificate_name" class="w-full" placeholder="Tên chứng chỉ..." />
          <span v-if="errors.certificate_name" class="training-error">{{ errors.certificate_name }}</span>
        </div>

        <div class="training-field">
          <label class="training-label">Tổ chức cấp</label>
          <InputText v-model="form.issuing_organization" class="w-full" placeholder="Tổ chức cấp..." />
        </div>

        <div class="training-row">
          <div class="training-field">
            <label class="training-label">Ngày cấp <span class="training-req">*</span></label>
            <DatePicker v-model="form.issued_date_obj" date-format="dd/mm/yy" placeholder="DD/MM/YYYY" show-button-bar class="w-full" />
            <span v-if="errors.issued_date" class="training-error">{{ errors.issued_date }}</span>
          </div>
          <div class="training-field">
            <label class="training-label">Ngày hết hạn</label>
            <DatePicker v-model="form.expiry_date_obj" date-format="dd/mm/yy" placeholder="Để trống = Vĩnh viễn" show-button-bar class="w-full" />
          </div>
        </div>
        <span v-if="errors.expiry_date" class="training-error">{{ errors.expiry_date }}</span>

        <div class="training-field">
          <label class="training-label">Khóa đào tạo liên quan</label>
          <Select
            v-model="form.related_course_id"
            :options="courses"
            option-label="name"
            option-value="id"
            placeholder="Chọn khóa học..."
            show-clear
            filter
            class="w-full"
          />
        </div>

        <div class="training-field">
          <label class="training-label">Ghi chú</label>
          <Textarea v-model="form.note" rows="2" class="w-full" auto-resize />
        </div>

        <div class="training-field">
          <label class="training-label">File chứng chỉ (PDF, JPG, PNG, tối đa 10MB)</label>
          <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap">
            <input
              ref="fileInput"
              type="file"
              accept=".pdf,.jpg,.jpeg,.png"
              style="display: none"
              @change="onFileChange"
            />
            <Button
              label="Chọn file"
              icon="pi pi-upload"
              severity="secondary"
              size="small"
              @click="fileInput?.click()"
            />
            <span v-if="selectedFile" class="cert-file-name">{{ selectedFile.name }}</span>
            <span v-else-if="editingFileName" class="cert-file-name muted-text">
              <i class="pi pi-paperclip" /> {{ editingFileName }}
            </span>
          </div>
        </div>

        <p v-if="apiError" class="training-api-error">
          <i class="pi pi-exclamation-triangle" />
          {{ apiError }}
        </p>
      </div>

      <template #footer>
        <Button label="Hủy" severity="secondary" text :disabled="saving" @click="showDialog = false" />
        <Button :label="editingId ? 'Lưu' : 'Tạo'" :loading="saving" @click="submitForm" />
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
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import Toast from 'primevue/toast'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'

import trainingService, {
  type CertificateRead,
  type ExpiryStatusValue,
} from '@/services/trainingService'
import departmentService, { type DepartmentRead } from '@/services/departmentService'
import employeeService, { type EmployeeLookupItem } from '@/services/employeeService'

const confirm = useConfirm()
const toast   = useToast()

// ── State ─────────────────────────────────────────────────────────────────────

const loading  = ref(false)
const items    = ref<CertificateRead[]>([])
const total    = ref(0)
const page     = ref(1)
const pageSize = ref(20)

const departments    = ref<DepartmentRead[]>([])
const courses        = ref<{ id: number; name: string }[]>([])
const employeeLookup = ref<EmployeeLookupItem[]>([])

const expiringSoonTotal = ref(0)

const searchText         = ref('')
const filterDeptId       = ref<number | null>(null)
const filterExpiryStatus = ref<string | null>(null)
const filterFromIssued   = ref<Date | null>(null)
const filterToIssued     = ref<Date | null>(null)
let searchTimer: ReturnType<typeof setTimeout> | null = null

const expiryStatusOptions = [
  { label: 'Còn hiệu lực',  value: 'valid' },
  { label: 'Sắp hết hạn',   value: 'expiring_soon' },
  { label: 'Đã hết hạn',    value: 'expired' },
  { label: 'Vĩnh viễn',     value: 'no_expiry' },
]

// Dialog
const showDialog     = ref(false)
const saving         = ref(false)
const apiError       = ref('')
const errors         = ref<Record<string, string>>({})
const editingId      = ref<number | null>(null)
const editingFileName = ref<string | null>(null)
const selectedFile   = ref<File | null>(null)
const fileInput      = ref<HTMLInputElement | null>(null)

const form = ref<{
  employee_id: number | null
  certificate_name: string
  issuing_organization: string
  issued_date_obj: Date | null
  expiry_date_obj: Date | null
  related_course_id: number | null
  note: string
}>({
  employee_id: null,
  certificate_name: '',
  issuing_organization: '',
  issued_date_obj: null,
  expiry_date_obj: null,
  related_course_id: null,
  note: '',
})

// ── Helpers ───────────────────────────────────────────────────────────────────

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

function parseDate(s: string): Date {
  const [y, m, d] = s.split('-').map(Number)
  return new Date(y, m - 1, d)
}

function expiryLabel(s: ExpiryStatusValue): string {
  const map: Record<ExpiryStatusValue, string> = {
    valid: 'Còn hiệu lực',
    expiring_soon: 'Sắp hết hạn',
    expired: 'Đã hết hạn',
    no_expiry: 'Vĩnh viễn',
  }
  return map[s] ?? s
}

function expirySeverity(s: ExpiryStatusValue): 'success' | 'warn' | 'danger' | 'secondary' {
  const map: Record<ExpiryStatusValue, 'success' | 'warn' | 'danger' | 'secondary'> = {
    valid: 'success',
    expiring_soon: 'warn',
    expired: 'danger',
    no_expiry: 'secondary',
  }
  return map[s] ?? 'secondary'
}

// ── Load ──────────────────────────────────────────────────────────────────────

async function load() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: page.value, page_size: pageSize.value }
    if (searchText.value)         params.search        = searchText.value
    if (filterDeptId.value)       params.department_id = filterDeptId.value
    if (filterExpiryStatus.value) params.expiry_status = filterExpiryStatus.value
    if (filterFromIssued.value)   params.from_issued   = toIso(filterFromIssued.value)
    if (filterToIssued.value)     params.to_issued     = toIso(filterToIssued.value)

    const res = await trainingService.getCertificates(params)
    items.value = res.data.items
    total.value = res.data.total
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể tải danh sách chứng chỉ', life: 4000 })
  } finally {
    loading.value = false
  }
}

async function loadExpiringSoonBanner() {
  try {
    const res = await trainingService.getCertificates({ expiry_status: 'expiring_soon', page_size: 1 })
    expiringSoonTotal.value = res.data.total
  } catch { /* silent */ }
}

function applyFilter() { page.value = 1; load() }

function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => applyFilter(), 400)
}

function filterByExpiry(status: string) {
  filterExpiryStatus.value = status
  applyFilter()
}

function reset() {
  searchText.value         = ''
  filterDeptId.value       = null
  filterExpiryStatus.value = null
  filterFromIssued.value   = null
  filterToIssued.value     = null
  page.value = 1
  load()
}

function onPage(e: { page: number; rows: number }) {
  page.value     = e.page + 1
  pageSize.value = e.rows
  load()
}

// ── Dialog ────────────────────────────────────────────────────────────────────

function resetForm() {
  form.value = {
    employee_id: null,
    certificate_name: '',
    issuing_organization: '',
    issued_date_obj: null,
    expiry_date_obj: null,
    related_course_id: null,
    note: '',
  }
  errors.value    = {}
  apiError.value  = ''
  selectedFile.value = null
  editingFileName.value = null
  editingId.value = null
}

async function openCreateDialog() {
  resetForm()
  if (employeeLookup.value.length === 0) {
    try {
      const res = await employeeService.lookup({ limit: 500 })
      employeeLookup.value = res.data
    } catch { /* silent */ }
  }
  showDialog.value = true
}

async function openEditDialog(cert: CertificateRead) {
  resetForm()
  if (employeeLookup.value.length === 0) {
    try {
      const res = await employeeService.lookup({ limit: 500 })
      employeeLookup.value = res.data
    } catch { /* silent */ }
  }
  editingId.value   = cert.id
  editingFileName.value = cert.file_name
  form.value = {
    employee_id:          cert.employee_id,
    certificate_name:     cert.certificate_name,
    issuing_organization: cert.issuing_organization ?? '',
    issued_date_obj:      parseDate(cert.issued_date),
    expiry_date_obj:      cert.expiry_date ? parseDate(cert.expiry_date) : null,
    related_course_id:    cert.related_course_id,
    note:                 cert.note ?? '',
  }
  showDialog.value = true
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  selectedFile.value = input.files?.[0] ?? null
}

function validate(): boolean {
  errors.value = {}
  if (!form.value.employee_id) {
    errors.value.employee_id = 'Vui lòng chọn nhân viên'
  }
  if (!form.value.certificate_name.trim()) {
    errors.value.certificate_name = 'Vui lòng nhập tên chứng chỉ'
  }
  if (!form.value.issued_date_obj) {
    errors.value.issued_date = 'Vui lòng chọn ngày cấp'
  }
  if (form.value.issued_date_obj && form.value.expiry_date_obj) {
    if (form.value.expiry_date_obj <= form.value.issued_date_obj) {
      errors.value.expiry_date = 'Ngày hết hạn phải sau ngày cấp'
    }
  }
  return Object.keys(errors.value).length === 0
}

async function submitForm() {
  if (!validate()) return
  saving.value   = true
  apiError.value = ''
  try {
    if (editingId.value) {
      const body = {
        certificate_name:     form.value.certificate_name.trim(),
        issuing_organization: form.value.issuing_organization.trim() || null,
        issued_date:          toIso(form.value.issued_date_obj!),
        expiry_date:          form.value.expiry_date_obj ? toIso(form.value.expiry_date_obj) : null,
        related_course_id:    form.value.related_course_id,
        note:                 form.value.note.trim() || null,
      }
      await trainingService.updateCertificate(editingId.value, body, selectedFile.value)
      toast.add({ severity: 'success', summary: 'Đã lưu', detail: 'Chứng chỉ đã được cập nhật', life: 3000 })
    } else {
      const body = {
        employee_id:          form.value.employee_id!,
        certificate_name:     form.value.certificate_name.trim(),
        issuing_organization: form.value.issuing_organization.trim() || null,
        issued_date:          toIso(form.value.issued_date_obj!),
        expiry_date:          form.value.expiry_date_obj ? toIso(form.value.expiry_date_obj) : null,
        related_course_id:    form.value.related_course_id,
        note:                 form.value.note.trim() || null,
      }
      await trainingService.createCertificate(body, selectedFile.value)
      toast.add({ severity: 'success', summary: 'Đã tạo', detail: 'Chứng chỉ đã được thêm', life: 3000 })
    }
    showDialog.value = false
    load()
    loadExpiringSoonBanner()
  } catch (err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    apiError.value = typeof detail === 'string' ? detail : 'Có lỗi xảy ra, vui lòng thử lại'
  } finally {
    saving.value = false
  }
}

// ── Download ──────────────────────────────────────────────────────────────────

async function doDownload(cert: CertificateRead) {
  try {
    await trainingService.downloadCertificateFile(cert.id, cert.file_name ?? `certificate_${cert.id}`)
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể tải file', life: 4000 })
  }
}

// ── Delete ────────────────────────────────────────────────────────────────────

function confirmDelete(cert: CertificateRead) {
  confirm.require({
    message: `Xóa chứng chỉ "${cert.certificate_name}" của ${cert.employee_name}?`,
    header: 'Xác nhận xóa',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Xóa',
    rejectLabel: 'Hủy',
    accept: () => doDelete(cert),
  })
}

async function doDelete(cert: CertificateRead) {
  try {
    await trainingService.deleteCertificate(cert.id)
    toast.add({ severity: 'success', summary: 'Đã xóa', detail: 'Chứng chỉ đã được xóa', life: 3000 })
    load()
    loadExpiringSoonBanner()
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể xóa chứng chỉ', life: 4000 })
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
  await Promise.allSettled([load(), loadExpiringSoonBanner()])
})
</script>
