<template>
  <div>
    <!-- Toolbar -->
    <div class="rewards-toolbar">
      <IconField class="rewards-search">
        <InputIcon class="pi pi-search" />
        <InputText
          v-model="filterSearch"
          placeholder="Tìm mã NV, tên, số QĐ..."
          @keyup.enter="load"
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
        v-model="filterTypeId"
        :options="rewardTypes"
        option-label="name"
        option-value="id"
        placeholder="Tất cả loại"
        show-clear
        filter
        style="width: 180px"
      />

      <DatePicker
        v-model="filterFromDate"
        date-format="dd/mm/yy"
        placeholder="Từ ngày"
        show-button-bar
        style="width: 145px"
      />
      <DatePicker
        v-model="filterToDate"
        date-format="dd/mm/yy"
        placeholder="Đến ngày"
        show-button-bar
        style="width: 145px"
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
        v-can:create="'rewards'"
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
        current-page-report-template="Hiển thị từ {first} đến {last} trên tổng số {totalRecords} dòng"
        :rows-per-page-options="[20, 50, 100]"
        @page="onPage"
      >
        <template #empty>
          <div class="rewards-empty">Không có dữ liệu</div>
        </template>

        <Column header="Nhân viên" style="min-width: 200px">
          <template #body="{ data }: { data: RewardRead }">
            <span class="rewards-emp-code">{{ data.employee_code }}</span>
            <span class="rewards-emp-sep">·</span>
            <span class="rewards-emp-name">{{ data.employee_name }}</span>
            <div v-if="data.department_name" class="rewards-emp-dept">{{ data.department_name }}</div>
          </template>
        </Column>

        <Column header="Loại khen thưởng" style="min-width: 150px">
          <template #body="{ data }: { data: RewardRead }">
            <Tag
              :value="data.reward_type_name"
              :severity="data.reward_type_is_monetary ? 'success' : 'info'"
              class="rewards-type-tag"
            />
          </template>
        </Column>

        <Column header="Tiêu đề" style="min-width: 200px">
          <template #body="{ data }: { data: RewardRead }">
            <span>{{ data.title }}</span>
            <div v-if="data.decision_number" class="rewards-decision-num">
              QĐ: {{ data.decision_number }}
            </div>
          </template>
        </Column>

        <Column header="Ngày KT" style="width: 110px">
          <template #body="{ data }: { data: RewardRead }">
            {{ fmtDate(data.reward_date) }}
          </template>
        </Column>

        <Column header="Giá trị" style="width: 130px; text-align: right">
          <template #body="{ data }: { data: RewardRead }">
            <span v-if="data.value !== null" class="rewards-value">
              {{ fmtVND(data.value) }}
            </span>
            <span v-else class="rewards-muted">—</span>
          </template>
        </Column>

        <Column header="File" style="width: 60px; text-align: center">
          <template #body="{ data }: { data: RewardRead }">
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
          <template #body="{ data }: { data: RewardRead }">
            <Button
              v-can:edit="'rewards'"
              icon="pi pi-pencil"
              text
              rounded
              size="small"
              severity="secondary"
              v-tooltip.top="'Sửa'"
              @click="openEdit(data)"
            />
            <Button
              v-can:delete="'rewards'"
              icon="pi pi-trash"
              text
              rounded
              size="small"
              severity="danger"
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
      :header="editingId ? 'Sửa quyết định khen thưởng' : 'Thêm quyết định khen thưởng'"
      modal
      :style="{ width: '600px' }"
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

        <!-- Loại khen thưởng -->
        <div class="rewards-field">
          <label class="rewards-label">Loại khen thưởng <span class="rewards-req">*</span></label>
          <Select
            v-model="form.reward_type_id"
            :options="rewardTypes"
            option-label="name"
            option-value="id"
            placeholder="Chọn loại..."
            filter
            class="w-full"
            @change="onTypeChange"
          />
          <span v-if="errors.reward_type_id" class="rewards-error">{{ errors.reward_type_id }}</span>
        </div>

        <!-- Tiêu đề -->
        <div class="rewards-field">
          <label class="rewards-label">Tiêu đề <span class="rewards-req">*</span></label>
          <InputText v-model="form.title" placeholder="VD: Khen thưởng tháng 05/2026" class="w-full" />
          <span v-if="errors.title" class="rewards-error">{{ errors.title }}</span>
        </div>

        <!-- Ngày + Số QĐ -->
        <div class="rewards-row">
          <div class="rewards-field">
            <label class="rewards-label">Ngày khen thưởng <span class="rewards-req">*</span></label>
            <DatePicker
              v-model="form.reward_date_obj"
              date-format="dd/mm/yy"
              placeholder="DD/MM/YYYY"
              show-button-bar
              class="w-full"
            />
            <span v-if="errors.reward_date" class="rewards-error">{{ errors.reward_date }}</span>
          </div>
          <div class="rewards-field">
            <label class="rewards-label">Số quyết định <span class="rewards-optional">(tùy chọn)</span></label>
            <InputText v-model="form.decision_number" placeholder="VD: 01/QĐ-2026" class="w-full" />
          </div>
        </div>

        <!-- Đơn vị khen thưởng -->
        <div class="rewards-field">
          <label class="rewards-label">Đơn vị/Người khen thưởng <span class="rewards-optional">(tùy chọn)</span></label>
          <InputText v-model="form.issued_by" placeholder="VD: Ban Giám đốc" class="w-full" />
        </div>

        <!-- Giá trị (chỉ hiện khi is_monetary) -->
        <div v-if="selectedTypeIsMonetary" class="rewards-field">
          <label class="rewards-label">Giá trị (VND) <span class="rewards-req">*</span></label>
          <InputNumber
            v-model="form.value"
            :min="0"
            mode="decimal"
            locale="vi-VN"
            placeholder="500.000"
            class="w-full"
          />
          <span v-if="errors.value" class="rewards-error">{{ errors.value }}</span>
        </div>

        <!-- Nội dung -->
        <div class="rewards-field">
          <label class="rewards-label">Nội dung <span class="rewards-optional">(tùy chọn)</span></label>
          <Textarea v-model="form.description" rows="3" class="w-full" placeholder="Mô tả chi tiết..." auto-resize />
        </div>

        <!-- Ghi chú -->
        <div class="rewards-field">
          <label class="rewards-label">Ghi chú <span class="rewards-optional">(tùy chọn)</span></label>
          <InputText v-model="form.note" class="w-full" placeholder="Ghi chú..." />
        </div>

        <!-- File -->
        <div class="rewards-field">
          <label class="rewards-label">File quyết định <span class="rewards-optional">(PDF/Word/Ảnh, tối đa 10MB)</span></label>
          <div class="rewards-file-row">
            <input
              ref="fileInputRef"
              type="file"
              accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
              style="display: none"
              @change="onFileChange"
            />
            <Button
              v-if="canMutateReward"
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
              v-if="canMutateReward && (selectedFile || existingFileName)"
              icon="pi pi-times"
              text
              rounded
              size="small"
              severity="danger"
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
        <Button
          v-if="canMutateReward"
          :label="editingId ? 'Lưu thay đổi' : 'Thêm'"
          :loading="saving"
          @click="submit"
        />
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

import rewardService, { type RewardRead, type RewardCreate, type RewardTypeRead } from '@/services/rewardService'
import departmentService, { type DepartmentRead } from '@/services/departmentService'
import employeeService, { type EmployeeLookupItem } from '@/services/employeeService'
import { usePermissionGate } from '@/composables/usePermissionGate'

const confirm = useConfirm()
const toast   = useToast()
const permissionGate = usePermissionGate()

// ── State ─────────────────────────────────────────────────────────────────────

const loading  = ref(false)
const items    = ref<RewardRead[]>([])
const total    = ref(0)
const page     = ref(1)
const pageSize = ref(20)

const rewardTypes  = ref<RewardTypeRead[]>([])
const departments  = ref<DepartmentRead[]>([])
const employees    = ref<EmployeeLookupItem[]>([])

// Filters
const filterSearch   = ref('')
const filterDeptId   = ref<number | null>(null)
const filterTypeId   = ref<number | null>(null)
const filterFromDate = ref<Date | null>(null)
const filterToDate   = ref<Date | null>(null)

// Dialog
const showDialog      = ref(false)
const saving          = ref(false)
const editingId       = ref<number | null>(null)
const dialogError     = ref('')
const existingFileName = ref<string | null>(null)
const selectedFile    = ref<File | null>(null)
const fileInputRef    = ref<HTMLInputElement | null>(null)
const errors          = ref<Record<string, string>>({})

const form = ref<{
  employee_id: number | null
  reward_type_id: number | null
  title: string
  description: string
  reward_date_obj: Date | null
  decision_number: string
  issued_by: string
  value: number | null
  note: string
}>({
  employee_id: null,
  reward_type_id: null,
  title: '',
  description: '',
  reward_date_obj: null,
  decision_number: '',
  issued_by: '',
  value: null,
  note: '',
})

// ── Computed ──────────────────────────────────────────────────────────────────

const selectedTypeIsMonetary = computed(() => {
  const t = rewardTypes.value.find(t => t.id === form.value.reward_type_id)
  return t?.is_monetary ?? false
})
const canMutateReward = computed(() => permissionGate.canCreate('rewards') || permissionGate.canEdit('rewards'))

// ── Load ──────────────────────────────────────────────────────────────────────

async function load() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: page.value, page_size: pageSize.value }
    if (filterSearch.value)      params.search        = filterSearch.value
    if (filterDeptId.value)      params.department_id = filterDeptId.value
    if (filterTypeId.value)      params.reward_type_id = filterTypeId.value
    if (filterFromDate.value)    params.from_date     = toIso(filterFromDate.value)
    if (filterToDate.value)      params.to_date       = toIso(filterToDate.value)

    const res = await rewardService.list(params)
    items.value = res.data.items
    total.value = res.data.total
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể tải danh sách khen thưởng', life: 4000 })
  } finally {
    loading.value = false
  }
}

function applyFilter() {
  page.value = 1
  load()
}

function reset() {
  filterSearch.value = ''
  filterDeptId.value = null
  filterTypeId.value = null
  filterFromDate.value = null
  filterToDate.value = null
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
    employee_id: null, reward_type_id: null, title: '',
    description: '', reward_date_obj: new Date(),
    decision_number: '', issued_by: '', value: null, note: '',
  })
  showDialog.value = true
}

function openEdit(row: RewardRead) {
  editingId.value = row.id
  existingFileName.value = row.has_file ? (row.file_name ?? 'file') : null
  selectedFile.value = null
  dialogError.value = ''
  errors.value = {}
  Object.assign(form.value, {
    employee_id: row.employee_id,
    reward_type_id: row.reward_type_id,
    title: row.title,
    description: row.description ?? '',
    reward_date_obj: new Date(row.reward_date),
    decision_number: row.decision_number ?? '',
    issued_by: row.issued_by ?? '',
    value: row.value !== null ? Number(row.value) : null,
    note: row.note ?? '',
  })
  showDialog.value = true
}

function onTypeChange() {
  if (!selectedTypeIsMonetary.value) form.value.value = null
}

function onFileChange(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (f) {
    selectedFile.value = f
    existingFileName.value = null
  }
}

function clearFile() {
  selectedFile.value = null
  existingFileName.value = null
  if (fileInputRef.value) fileInputRef.value.value = ''
}

function validate(): boolean {
  errors.value = {}
  if (!form.value.employee_id)    errors.value.employee_id    = 'Vui lòng chọn nhân viên'
  if (!form.value.reward_type_id) errors.value.reward_type_id = 'Vui lòng chọn loại khen thưởng'
  if (!form.value.title.trim())   errors.value.title          = 'Vui lòng nhập tiêu đề'
  if (!form.value.reward_date_obj) errors.value.reward_date   = 'Vui lòng chọn ngày khen thưởng'
  if (selectedTypeIsMonetary.value && (form.value.value === null || form.value.value === undefined))
    errors.value.value = 'Loại tiền mặt phải nhập giá trị'
  return Object.keys(errors.value).length === 0
}

async function submit() {
  if (!validate()) return
  saving.value = true
  dialogError.value = ''
  try {
    const payload: RewardCreate = {
      employee_id:     form.value.employee_id!,
      reward_type_id:  form.value.reward_type_id!,
      title:           form.value.title.trim(),
      description:     form.value.description.trim() || null,
      reward_date:     toIso(form.value.reward_date_obj!)!,
      decision_number: form.value.decision_number.trim() || null,
      issued_by:       form.value.issued_by.trim() || null,
      value:           selectedTypeIsMonetary.value ? form.value.value : null,
      note:            form.value.note.trim() || null,
    }

    if (editingId.value) {
      await rewardService.update(editingId.value, payload, selectedFile.value)
      toast.add({ severity: 'success', summary: 'Đã cập nhật', detail: 'Quyết định khen thưởng đã được cập nhật', life: 3000 })
    } else {
      await rewardService.create(payload, selectedFile.value)
      toast.add({ severity: 'success', summary: 'Đã thêm', detail: 'Quyết định khen thưởng đã được tạo', life: 3000 })
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

function confirmDelete(row: RewardRead) {
  confirm.require({
    message: `Xóa quyết định khen thưởng "${row.title}" của ${row.employee_name}?`,
    header: 'Xác nhận xóa',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Xóa',
    rejectLabel: 'Hủy',
    accept: () => doDelete(row.id),
  })
}

async function doDelete(id: number) {
  try {
    await rewardService.delete(id)
    toast.add({ severity: 'success', summary: 'Đã xóa', detail: 'Quyết định khen thưởng đã được xóa', life: 3000 })
    load()
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể xóa quyết định', life: 4000 })
  }
}

// ── File download ─────────────────────────────────────────────────────────────

async function downloadFile(row: RewardRead) {
  try {
    const res = await rewardService.downloadFile(row.id)
    const url = URL.createObjectURL(new Blob([res.data as BlobPart]))
    const a = document.createElement('a')
    a.href = url
    a.download = row.file_name ?? `reward_${row.id}`
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể tải file', life: 3000 })
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

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

function fmtVND(val: string | number | null | undefined): string {
  if (val === null || val === undefined) return '—'
  return Number(val).toLocaleString('vi-VN') + ' đ'
}

// ── Init ──────────────────────────────────────────────────────────────────────

onMounted(async () => {
  try {
    const [typesRes, deptsRes, empsRes] = await Promise.all([
      rewardService.listTypes(),
      departmentService.getList(true),
      employeeService.lookup({ limit: 500 }),
    ])
    rewardTypes.value = typesRes.data
    departments.value = deptsRes.data
    employees.value   = empsRes.data
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi khởi tạo', detail: 'Không thể tải danh mục dữ liệu', life: 5000 })
  }
  load()
})
</script>
