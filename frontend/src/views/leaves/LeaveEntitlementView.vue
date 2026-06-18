<template>
  <div>
    <!-- Page header -->
    <div class="page-header">
      <div>
        <h2>Số ngày phép</h2>
        <span class="subtitle">Phân bổ và theo dõi ngày phép nhân viên</span>
      </div>
      <div class="page-header-actions">
        <Button
          v-can:create="'leaves'"
          icon="pi pi-bolt"
          label="Nạp phép hàng loạt"
          severity="secondary"
          @click="openBulkDialog"
        />
        <Button v-can:create="'leaves'" icon="pi pi-plus" label="Thêm thủ công" @click="openCreateDialog" />
      </div>
    </div>

    <!-- Toolbar -->
    <div class="toolbar">
      <IconField class="toolbar-search">
        <InputIcon class="pi pi-search" />
        <InputText
          v-model="filters.keyword"
          placeholder="Tìm tên nhân viên..."
          class="w-full"
          @keyup.enter="applyFilter"
        />
      </IconField>

      <Select
        v-model="filters.year"
        :options="yearOptions"
        option-label="label"
        option-value="value"
        placeholder="Năm"
        filter
        class="toolbar-filter-sm"
      />

      <Select
        v-model="filters.leave_type_id"
        :options="leaveTypes"
        option-label="name"
        option-value="id"
        placeholder="Loại phép"
        show-clear
        filter
        class="toolbar-filter"
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
    </div>

    <!-- DataTable -->
    <div class="card">
      <DataTable
        :value="items"
        :loading="loading"
        responsive-layout="scroll"
        :rows="pageSize"
        :total-records="total"
        :lazy="true"
        paginator
        paginator-template="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
        current-page-report-template="Hiển thị từ {first} đến {last} trên tổng số {totalRecords} dòng"
        :rows-per-page-options="[20, 50, 100]"
        @page="onPage"
      >
        <Column header="Nhân viên" style="min-width: 180px">
          <template #body="{ data }">
            <div style="font-weight: 500">{{ data.employee_name }}</div>
            <div class="muted-text" style="font-size: 0.78rem">{{ data.employee_code }}</div>
          </template>
        </Column>

        <Column field="leave_type_name" header="Loại phép" style="min-width: 140px" />

        <Column header="Cấp phép" style="width: 95px">
          <template #body="{ data }">
            <span class="right-text">{{ data.allocated_days }}</span>
          </template>
        </Column>

        <Column header="Chuyển dư" style="width: 100px">
          <template #body="{ data }">
            <span v-if="data.carryover_days > 0" class="right-text">{{ data.carryover_days }}</span>
            <span v-else class="muted-text right-text">—</span>
          </template>
        </Column>

        <Column header="Hết hạn dư" style="min-width: 120px">
          <template #body="{ data }">
            <span v-if="data.carryover_expires" class="ent-expires">
              {{ formatDate(data.carryover_expires) }}
            </span>
            <span v-else class="muted-text">—</span>
          </template>
        </Column>

        <Column header="Đã dùng" style="width: 90px">
          <template #body="{ data }">
            <span class="right-text">{{ data.used_days }}</span>
          </template>
        </Column>

        <Column header="Còn lại" style="width: 95px">
          <template #body="{ data }">
            <span :class="['days-badge', remainingClass(data.remaining_days)]">
              {{ data.remaining_days }}
            </span>
          </template>
        </Column>

        <Column header="" style="width: 80px">
          <template #body="{ data }">
            <div class="action-cell">
              <Button
                v-can:edit="'leaves'"
                icon="pi pi-pencil"
                text rounded size="small"
                v-tooltip.top="'Chỉnh sửa'"
                @click="openEditDialog(data)"
              />
              <Button
                v-can:delete="'leaves'"
                icon="pi pi-trash"
                text rounded size="small"
                severity="danger"
                v-tooltip.top="'Xóa'"
                @click="confirmDelete(data)"
              />
            </div>
          </template>
        </Column>

        <template #empty>
          <div class="empty-state">
            <i class="pi pi-calendar" />
            <span>Không có dữ liệu ngày phép</span>
          </div>
        </template>
      </DataTable>
    </div>

    <!-- Create / Edit Dialog -->
    <Dialog
      v-model:visible="showDialog"
      :header="editingId ? 'Chỉnh sửa ngày phép' : 'Thêm ngày phép'"
      modal
      :style="{ width: '520px' }"
    >
      <div class="field">
        <label>Nhân viên <span class="req">*</span></label>
        <Select
          v-model="form.employee_id"
          :options="employees"
          option-label="full_name"
          option-value="id"
          placeholder="Chọn nhân viên..."
          :disabled="!!editingId"
          filter
          class="w-full"
        />
      </div>

      <div class="field">
        <label>Loại phép <span class="req">*</span></label>
        <Select
          v-model="form.leave_type_id"
          :options="leaveTypes"
          option-label="name"
          option-value="id"
          placeholder="Chọn loại phép..."
          :disabled="!!editingId"
          filter
          class="w-full"
        />
      </div>

      <div class="field-row">
        <div class="field">
          <label>Năm <span class="req">*</span></label>
          <InputNumber
            v-model="form.year"
            :min="2020"
            :max="2100"
            :use-grouping="false"
            :disabled="!!editingId"
            class="w-full"
          />
        </div>
        <div class="field">
          <label>Số ngày cấp phép <span class="req">*</span></label>
          <InputNumber
            v-model="form.allocated_days"
            :min="0"
            :max="365"
            :min-fraction-digits="1"
            :max-fraction-digits="1"
            suffix=" ngày"
            class="w-full"
          />
        </div>
      </div>

      <div class="field-row">
        <div class="field">
          <label>Ngày chuyển dư</label>
          <InputNumber
            v-model="form.carryover_days"
            :min="0"
            :max="365"
            :min-fraction-digits="1"
            :max-fraction-digits="1"
            suffix=" ngày"
            class="w-full"
          />
        </div>
        <div class="field">
          <label>Hết hạn dư</label>
          <DatePicker
            v-model="form.carryover_expires_date"
            date-format="dd/mm/yy"
            placeholder="DD/MM/YYYY"
            show-button-bar
            class="w-full"
          />
        </div>
      </div>

      <div class="field">
        <label>Ghi chú</label>
        <InputText v-model="form.note" placeholder="Ghi chú..." class="w-full" />
      </div>

      <p v-if="dialogError" class="error-msg">{{ dialogError }}</p>

      <template #footer>
        <Button label="Hủy" severity="secondary" text @click="showDialog = false" />
        <Button
          v-can="editingId ? 'leaves:edit' : 'leaves:create'"
          :label="editingId ? 'Lưu thay đổi' : 'Thêm'"
          :loading="saving"
          @click="submitForm"
        />
      </template>
    </Dialog>

    <!-- Bulk Allocate Dialog -->
    <Dialog
      v-model:visible="showBulkDialog"
      header="Nạp phép hàng loạt"
      modal
      :style="{ width: '440px' }"
    >
      <div class="field">
        <label>Năm phân bổ <span class="req">*</span></label>
        <InputNumber
          v-model="bulkForm.year"
          :min="2020"
          :max="2100"
          :use-grouping="false"
          class="w-full"
        />
      </div>

      <div class="field">
        <label>Loại phép <span class="field-hint">(để trống = Phép năm)</span></label>
        <Select
          v-model="bulkForm.leave_type_code"
          :options="leaveTypes"
          option-label="name"
          option-value="code"
          placeholder="Phép năm (annual_leave)"
          show-clear
          filter
          class="w-full"
        />
      </div>

      <div class="switch-row" style="margin-bottom: 1rem">
        <Checkbox v-model="bulkForm.overwrite" binary input-id="ent-overwrite" />
        <label for="ent-overwrite" style="cursor: pointer; font-size: 0.875rem">
          Ghi đè nếu đã có bản ghi (kể cả đã có giao dịch)
        </label>
      </div>

      <div v-if="bulkResult" class="ent-bulk-result">
        <div class="ent-bulk-row">
          <i class="pi pi-check-circle ent-bulk-ok" />
          <span>Đã nạp: <strong>{{ bulkResult.allocated }}</strong> bản ghi</span>
        </div>
        <div class="ent-bulk-row">
          <i class="pi pi-forward ent-bulk-muted" />
          <span>Bỏ qua: <strong>{{ bulkResult.skipped }}</strong> bản ghi</span>
        </div>
        <div v-if="bulkResult.errors.length" class="ent-bulk-row">
          <i class="pi pi-exclamation-triangle ent-bulk-warn" />
          <span>{{ bulkResult.errors.join(' · ') }}</span>
        </div>
      </div>

      <p v-if="bulkError" class="error-msg">{{ bulkError }}</p>

      <template #footer>
        <Button label="Đóng" severity="secondary" text @click="closeBulkDialog" />
        <Button
          v-can:create="'leaves'"
          label="Xác nhận nạp phép"
          icon="pi pi-bolt"
          :loading="bulkLoading"
          @click="submitBulk"
        />
      </template>
    </Dialog>

    <ConfirmDialog />
    <Toast />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
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
import Toast from 'primevue/toast'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'

import leaveEntitlementService, {
  type LeaveEntitlementRead,
  type BulkAllocateResult,
} from '@/services/leaveEntitlementService'
import otherBusinessCatalogService, {
  type LeaveTypeRead,
} from '@/services/otherBusinessCatalogService'
import employeeService, { type EmployeeLookupItem } from '@/services/employeeService'

const confirm = useConfirm()
const toast   = useToast()

// ── State ─────────────────────────────────────────────────────────────────────

const loading  = ref(false)
const items    = ref<LeaveEntitlementRead[]>([])
const total    = ref(0)
const page     = ref(1)
const pageSize = ref(20)

const leaveTypes = ref<LeaveTypeRead[]>([])
const employees  = ref<EmployeeLookupItem[]>([])

const currentYear = new Date().getFullYear()
const yearOptions = Array.from({ length: 10 }, (_, i) => {
  const y = currentYear - 2 + i
  return { label: String(y), value: y }
})

const filters = ref({
  keyword:       '',
  year:          currentYear as number | null,
  leave_type_id: null as number | null,
})

// ── Load data ─────────────────────────────────────────────────────────────────

async function load() {
  loading.value = true
  try {
    const params: Record<string, unknown> = {
      page: page.value,
      page_size: pageSize.value,
    }
    if (filters.value.keyword)       params.keyword       = filters.value.keyword
    if (filters.value.year)          params.year          = filters.value.year
    if (filters.value.leave_type_id) params.leave_type_id = filters.value.leave_type_id

    const res = await leaveEntitlementService.list(params)
    items.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

async function loadLeaveTypes() {
  try {
    const res = await otherBusinessCatalogService.lookupLeaveTypes({ limit: 100 })
    leaveTypes.value = res.data
  } catch { /* non-blocking */ }
}

async function loadEmployees() {
  try {
    const res = await employeeService.lookup({ limit: 100 })
    employees.value = res.data
  } catch { /* non-blocking */ }
}

function applyFilter() {
  page.value = 1
  load()
}

function reset() {
  filters.value = { keyword: '', year: currentYear, leave_type_id: null }
  page.value = 1
  load()
}

function onPage(e: { page: number; rows: number }) {
  page.value  = e.page + 1
  pageSize.value = e.rows
  load()
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

function remainingClass(remaining: number): string {
  if (remaining <= 0) return 'expired'
  if (remaining <= 2) return 'warning'
  return 'ok'
}

// ── Create / Edit Dialog ──────────────────────────────────────────────────────

const showDialog  = ref(false)
const editingId   = ref<number | null>(null)
const saving      = ref(false)
const dialogError = ref('')

const form = ref({
  employee_id:            null as number | null,
  leave_type_id:          null as number | null,
  year:                   currentYear as number,
  allocated_days:         12 as number,
  carryover_days:         0 as number,
  carryover_expires_date: null as Date | null,
  note:                   '',
})

function openCreateDialog() {
  editingId.value = null
  dialogError.value = ''
  form.value = {
    employee_id:            null,
    leave_type_id:          null,
    year:                   currentYear,
    allocated_days:         12,
    carryover_days:         0,
    carryover_expires_date: null,
    note:                   '',
  }
  showDialog.value = true
}

function openEditDialog(row: LeaveEntitlementRead) {
  editingId.value   = row.id
  dialogError.value = ''
  form.value = {
    employee_id:            row.employee_id,
    leave_type_id:          row.leave_type_id,
    year:                   row.year,
    allocated_days:         row.allocated_days,
    carryover_days:         row.carryover_days,
    carryover_expires_date: row.carryover_expires ? new Date(row.carryover_expires) : null,
    note:                   row.note ?? '',
  }
  showDialog.value = true
}

function toIsoDate(d: Date | null): string | null {
  if (!d) return null
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

async function submitForm() {
  dialogError.value = ''
  if (!form.value.employee_id && !editingId.value) {
    dialogError.value = 'Vui lòng chọn nhân viên'
    return
  }
  if (!form.value.leave_type_id && !editingId.value) {
    dialogError.value = 'Vui lòng chọn loại phép'
    return
  }

  saving.value = true
  try {
    if (editingId.value) {
      await leaveEntitlementService.update(editingId.value, {
        allocated_days:  form.value.allocated_days,
        carryover_days:  form.value.carryover_days || undefined,
        carryover_expires: toIsoDate(form.value.carryover_expires_date) || undefined,
        note:            form.value.note || undefined,
      })
      toast.add({ severity: 'success', summary: 'Đã cập nhật', life: 2500 })
    } else {
      await leaveEntitlementService.create({
        employee_id:   form.value.employee_id!,
        leave_type_id: form.value.leave_type_id!,
        year:          form.value.year,
        allocated_days: form.value.allocated_days,
        carryover_days: form.value.carryover_days || undefined,
        carryover_expires: toIsoDate(form.value.carryover_expires_date) || undefined,
        note: form.value.note || undefined,
      })
      toast.add({ severity: 'success', summary: 'Đã thêm ngày phép', life: 2500 })
    }
    showDialog.value = false
    load()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    dialogError.value = err?.response?.data?.detail ?? 'Không thể lưu dữ liệu'
  } finally {
    saving.value = false
  }
}

// ── Delete ────────────────────────────────────────────────────────────────────

function confirmDelete(row: LeaveEntitlementRead) {
  confirm.require({
    message: `Xóa bản ghi ngày phép của ${row.employee_name} (${row.leave_type_name} — ${row.year})?`,
    header:  'Xác nhận xóa',
    icon:    'pi pi-exclamation-triangle',
    acceptLabel:  'Xóa',
    rejectLabel:  'Hủy',
    acceptClass:  'p-button-danger',
    accept: async () => {
      try {
        await leaveEntitlementService.remove(row.id)
        toast.add({ severity: 'success', summary: 'Đã xóa', life: 2000 })
        load()
      } catch (e: unknown) {
        const err = e as { response?: { data?: { detail?: string } } }
        toast.add({
          severity: 'error',
          summary:  'Không thể xóa',
          detail:   err?.response?.data?.detail ?? 'Có lỗi xảy ra',
          life: 4000,
        })
      }
    },
  })
}

// ── Bulk Allocate Dialog ──────────────────────────────────────────────────────

const showBulkDialog = ref(false)
const bulkLoading    = ref(false)
const bulkError      = ref('')
const bulkResult     = ref<BulkAllocateResult | null>(null)

const bulkForm = ref({
  year:            currentYear,
  leave_type_code: null as string | null,
  overwrite:       false,
})

function openBulkDialog() {
  bulkError.value  = ''
  bulkResult.value = null
  bulkForm.value   = { year: currentYear, leave_type_code: null, overwrite: false }
  showBulkDialog.value = true
}

function closeBulkDialog() {
  showBulkDialog.value = false
  if (bulkResult.value?.allocated) load()
}

async function submitBulk() {
  bulkError.value  = ''
  bulkResult.value = null
  bulkLoading.value = true
  try {
    const req = {
      year:     bulkForm.value.year,
      overwrite: bulkForm.value.overwrite,
      ...(bulkForm.value.leave_type_code
        ? { leave_type_codes: [bulkForm.value.leave_type_code] }
        : {}),
    }
    const res = await leaveEntitlementService.bulkAllocate(req)
    bulkResult.value = res.data
    toast.add({
      severity: 'success',
      summary:  'Nạp phép xong',
      detail:   `Đã nạp ${res.data.allocated} bản ghi, bỏ qua ${res.data.skipped}`,
      life: 3500,
    })
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    bulkError.value = err?.response?.data?.detail ?? 'Không thể nạp phép'
  } finally {
    bulkLoading.value = false
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────

onMounted(() => {
  loadLeaveTypes()
  loadEmployees()
  load()
})
</script>
