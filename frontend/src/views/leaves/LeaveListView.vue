<template>
  <div>
    <!-- Page header -->
    <div class="page-header">
      <div>
        <h2>Ghi nhận nghỉ phép</h2>
        <span class="subtitle">Quản lý các bản ghi nghỉ phép của nhân viên</span>
      </div>
      <div class="page-header-actions">
        <Button icon="pi pi-plus" label="Thêm bản ghi" @click="openCreateDialog" />
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

      <Select
        v-model="filters.status"
        :options="statusOptions"
        option-label="label"
        option-value="value"
        placeholder="Trạng thái"
        show-clear
        filter
        class="toolbar-filter-sm"
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

        <Column field="leave_type_name" header="Loại phép" style="min-width: 130px" />

        <Column header="Từ ngày" style="width: 110px">
          <template #body="{ data }">
            <span>{{ formatDate(data.start_date) }}</span>
            <span v-if="data.start_half === 'PM'" class="leave-half-tag">chiều</span>
          </template>
        </Column>

        <Column header="Đến ngày" style="width: 110px">
          <template #body="{ data }">
            <span>{{ formatDate(data.end_date) }}</span>
            <span v-if="data.end_half === 'AM'" class="leave-half-tag">sáng</span>
          </template>
        </Column>

        <Column header="Số ngày" style="width: 85px">
          <template #body="{ data }">
            <span class="right-text">{{ data.total_days }}</span>
          </template>
        </Column>

        <Column header="Lý do" style="min-width: 140px">
          <template #body="{ data }">
            <span v-if="data.reason">{{ data.reason }}</span>
            <span v-else class="muted-text">—</span>
          </template>
        </Column>

        <Column header="T.Thái" style="width: 95px">
          <template #body="{ data }">
            <span :class="['leave-status-badge', data.status]">
              {{ data.status === 'active' ? 'Hiệu lực' : 'Đã hủy' }}
            </span>
          </template>
        </Column>

        <Column header="" style="width: 110px">
          <template #body="{ data }">
            <div class="action-cell">
              <Button
                v-if="data.status === 'active'"
                icon="pi pi-pencil"
                text rounded size="small"
                v-tooltip.top="'Chỉnh sửa'"
                @click="openEditDialog(data)"
              />
              <Button
                v-if="data.status === 'active'"
                icon="pi pi-ban"
                text rounded size="small"
                severity="warning"
                v-tooltip.top="'Hủy bản ghi'"
                @click="promptCancel(data)"
              />
              <Button
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
            <i class="pi pi-calendar-times" />
            <span>Không có dữ liệu nghỉ phép</span>
          </div>
        </template>
      </DataTable>
    </div>

    <!-- Create / Edit Dialog -->
    <Dialog
      v-model:visible="showDialog"
      :header="editingId ? 'Chỉnh sửa bản ghi nghỉ phép' : 'Thêm bản ghi nghỉ phép'"
      modal
      :style="{ width: '540px' }"
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
          @change="onEmployeeChange"
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
          @change="onLeaveTypeChange"
        />
      </div>

      <div class="field-row">
        <div class="field">
          <label>Ngày bắt đầu <span class="req">*</span></label>
          <DatePicker
            v-model="form.start_date_obj"
            date-format="dd/mm/yy"
            placeholder="DD/MM/YYYY"
            show-button-bar
            class="w-full"
            @date-select="recalcDays"
          />
          <div v-if="allowHalfDay" class="leave-half-check">
            <Checkbox v-model="form.start_pm" binary input-id="start-pm" @change="recalcDays" />
            <label for="start-pm">Buổi chiều (PM)</label>
          </div>
        </div>

        <div class="field">
          <label>Ngày kết thúc <span class="req">*</span></label>
          <DatePicker
            v-model="form.end_date_obj"
            date-format="dd/mm/yy"
            placeholder="DD/MM/YYYY"
            show-button-bar
            class="w-full"
            @date-select="recalcDays"
          />
          <div v-if="allowHalfDay" class="leave-half-check">
            <Checkbox v-model="form.end_am" binary input-id="end-am" @change="recalcDays" />
            <label for="end-am">Buổi sáng (AM)</label>
          </div>
        </div>
      </div>

      <!-- Tính ngày realtime -->
      <div v-if="computedDays !== null" class="leave-days-summary">
        <span class="leave-days-label">Số ngày nghỉ:</span>
        <span class="leave-days-value">{{ computedDays }} ngày</span>
        <template v-if="currentEntitlement">
          <span class="leave-days-sep">·</span>
          <span class="leave-days-label">Còn lại hiện tại:</span>
          <span class="leave-days-value">{{ currentEntitlement.remaining_days }} ngày</span>
          <span class="leave-days-sep">·</span>
          <span class="leave-days-label">Sau khi trừ:</span>
          <span
            :class="['leave-days-value', remainingAfter < 0 ? 'leave-days-warn' : 'leave-days-ok']"
          >{{ remainingAfter.toFixed(1) }} ngày</span>
        </template>
      </div>

      <div class="field">
        <label>Lý do</label>
        <InputText v-model="form.reason" placeholder="Lý do nghỉ..." class="w-full" />
      </div>

      <div class="field">
        <label>Ghi chú</label>
        <InputText v-model="form.note" placeholder="Ghi chú..." class="w-full" />
      </div>

      <p v-if="dialogError" class="error-msg">{{ dialogError }}</p>

      <template #footer>
        <Button label="Hủy" severity="secondary" text @click="showDialog = false" />
        <Button
          :label="editingId ? 'Lưu thay đổi' : 'Thêm'"
          :loading="saving"
          @click="submitForm"
        />
      </template>
    </Dialog>

    <!-- Cancel Dialog -->
    <Dialog
      v-model:visible="showCancelDialog"
      header="Hủy bản ghi nghỉ phép"
      modal
      :style="{ width: '420px' }"
    >
      <p style="margin-bottom: 1rem">
        Hủy bản ghi nghỉ phép của
        <strong>{{ cancelTarget?.employee_name }}</strong>
        ({{ cancelTarget?.start_date }} — {{ cancelTarget?.total_days }} ngày)?
        Số ngày đã dùng sẽ được hoàn trả vào entitlement.
      </p>
      <div class="field">
        <label>Lý do hủy</label>
        <InputText v-model="cancelReason" placeholder="Lý do hủy (tùy chọn)..." class="w-full" />
      </div>
      <template #footer>
        <Button label="Không" severity="secondary" text @click="showCancelDialog = false" />
        <Button
          label="Xác nhận hủy"
          severity="warning"
          :loading="cancelling"
          @click="submitCancel"
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
import Checkbox from 'primevue/checkbox'
import Column from 'primevue/column'
import ConfirmDialog from 'primevue/confirmdialog'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Toast from 'primevue/toast'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'

import leaveRecordService, { type LeaveRecordRead } from '@/services/leaveRecordService'
import leaveEntitlementService, { type LeaveEntitlementRead } from '@/services/leaveEntitlementService'
import otherBusinessCatalogService, { type LeaveTypeRead } from '@/services/otherBusinessCatalogService'
import employeeService, { type EmployeeLookupItem } from '@/services/employeeService'

const confirm = useConfirm()
const toast   = useToast()

// ── State ─────────────────────────────────────────────────────────────────────

const loading  = ref(false)
const items    = ref<LeaveRecordRead[]>([])
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

const statusOptions = [
  { label: 'Hiệu lực', value: 'active' },
  { label: 'Đã hủy',   value: 'cancelled' },
]

const filters = ref({
  keyword:       '',
  year:          currentYear as number | null,
  leave_type_id: null as number | null,
  status:        null as string | null,
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
    if (filters.value.status)        params.status        = filters.value.status

    const res = await leaveRecordService.list(params)
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
  filters.value = { keyword: '', year: currentYear, leave_type_id: null, status: null }
  page.value = 1
  load()
}

function onPage(e: { page: number; rows: number }) {
  page.value     = e.page + 1
  pageSize.value = e.rows
  load()
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

function toIsoDate(d: Date | null): string | null {
  if (!d) return null
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function computeTotalDays(start: Date, end: Date, startPm: boolean, endAm: boolean): number {
  const calendarDays = Math.round((end.getTime() - start.getTime()) / 86400000) + 1
  return calendarDays - (startPm ? 0.5 : 0) - (endAm ? 0.5 : 0)
}

// ── Create / Edit Dialog ──────────────────────────────────────────────────────

const showDialog  = ref(false)
const editingId   = ref<number | null>(null)
const saving      = ref(false)
const dialogError = ref('')

const form = ref({
  employee_id:   null as number | null,
  leave_type_id: null as number | null,
  start_date_obj: null as Date | null,
  end_date_obj:   null as Date | null,
  start_pm:       false,
  end_am:         false,
  reason: '',
  note:   '',
})

const allowHalfDay = computed(() => {
  if (!form.value.leave_type_id) return true
  const lt = leaveTypes.value.find(l => l.id === form.value.leave_type_id)
  return lt?.allow_half_day ?? true
})

const computedDays = computed<number | null>(() => {
  if (!form.value.start_date_obj || !form.value.end_date_obj) return null
  const v = computeTotalDays(
    form.value.start_date_obj,
    form.value.end_date_obj,
    allowHalfDay.value && form.value.start_pm,
    allowHalfDay.value && form.value.end_am,
  )
  return v > 0 ? v : null
})

const currentEntitlement = ref<LeaveEntitlementRead | null>(null)

const remainingAfter = computed<number>(() => {
  if (!currentEntitlement.value || computedDays.value === null) return 0
  return currentEntitlement.value.remaining_days - computedDays.value
})

async function loadCurrentEntitlement() {
  if (!form.value.employee_id || !form.value.leave_type_id || !form.value.start_date_obj) {
    currentEntitlement.value = null
    return
  }
  const year = form.value.start_date_obj.getFullYear()
  try {
    const res = await leaveEntitlementService.list({
      employee_id:   form.value.employee_id,
      leave_type_id: form.value.leave_type_id,
      year,
      page_size: 1,
    })
    currentEntitlement.value = res.data.items[0] ?? null
  } catch {
    currentEntitlement.value = null
  }
}

function recalcDays() {
  loadCurrentEntitlement()
}

function onEmployeeChange() {
  loadCurrentEntitlement()
}

function onLeaveTypeChange() {
  if (!allowHalfDay.value) {
    form.value.start_pm = false
    form.value.end_am   = false
  }
  loadCurrentEntitlement()
}

function openCreateDialog() {
  editingId.value   = null
  dialogError.value = ''
  currentEntitlement.value = null
  form.value = {
    employee_id:    null,
    leave_type_id:  null,
    start_date_obj: null,
    end_date_obj:   null,
    start_pm:       false,
    end_am:         false,
    reason: '',
    note:   '',
  }
  showDialog.value = true
}

function openEditDialog(row: LeaveRecordRead) {
  editingId.value   = row.id
  dialogError.value = ''
  currentEntitlement.value = null
  form.value = {
    employee_id:    row.employee_id,
    leave_type_id:  row.leave_type_id,
    start_date_obj: new Date(row.start_date),
    end_date_obj:   new Date(row.end_date),
    start_pm:       row.start_half === 'PM',
    end_am:         row.end_half === 'AM',
    reason: row.reason ?? '',
    note:   row.note ?? '',
  }
  loadCurrentEntitlement()
  showDialog.value = true
}

async function submitForm() {
  dialogError.value = ''

  if (!editingId.value) {
    if (!form.value.employee_id)   { dialogError.value = 'Vui lòng chọn nhân viên'; return }
    if (!form.value.leave_type_id) { dialogError.value = 'Vui lòng chọn loại phép'; return }
  }
  if (!form.value.start_date_obj) { dialogError.value = 'Vui lòng chọn ngày bắt đầu'; return }
  if (!form.value.end_date_obj)   { dialogError.value = 'Vui lòng chọn ngày kết thúc'; return }

  const startIso = toIsoDate(form.value.start_date_obj)!
  const endIso   = toIsoDate(form.value.end_date_obj)!
  const startHalf = (allowHalfDay.value && form.value.start_pm) ? 'PM' : null
  const endHalf   = (allowHalfDay.value && form.value.end_am)   ? 'AM' : null

  saving.value = true
  try {
    if (editingId.value) {
      await leaveRecordService.update(editingId.value, {
        start_date: startIso,
        end_date:   endIso,
        start_half: startHalf,
        end_half:   endHalf,
        reason:     form.value.reason || undefined,
        note:       form.value.note || undefined,
      })
      toast.add({ severity: 'success', summary: 'Đã cập nhật', life: 2500 })
    } else {
      const res = await leaveRecordService.create({
        employee_id:   form.value.employee_id!,
        leave_type_id: form.value.leave_type_id!,
        start_date:    startIso,
        end_date:      endIso,
        start_half:    startHalf,
        end_half:      endHalf,
        reason:        form.value.reason || undefined,
        note:          form.value.note || undefined,
      })
      if (res.data.warning) {
        toast.add({ severity: 'warn', summary: 'Lưu ý', detail: res.data.warning, life: 5000 })
      } else {
        toast.add({ severity: 'success', summary: 'Đã thêm bản ghi', life: 2500 })
      }
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

// ── Cancel ────────────────────────────────────────────────────────────────────

const showCancelDialog = ref(false)
const cancelTarget     = ref<LeaveRecordRead | null>(null)
const cancelReason     = ref('')
const cancelling       = ref(false)

function promptCancel(row: LeaveRecordRead) {
  cancelTarget.value = row
  cancelReason.value = ''
  showCancelDialog.value = true
}

async function submitCancel() {
  if (!cancelTarget.value) return
  cancelling.value = true
  try {
    await leaveRecordService.cancel(cancelTarget.value.id, cancelReason.value || null)
    toast.add({ severity: 'success', summary: 'Đã hủy bản ghi', life: 2500 })
    showCancelDialog.value = false
    load()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    toast.add({
      severity: 'error',
      summary:  'Không thể hủy',
      detail:   err?.response?.data?.detail ?? 'Có lỗi xảy ra',
      life: 4000,
    })
  } finally {
    cancelling.value = false
  }
}

// ── Delete ────────────────────────────────────────────────────────────────────

function confirmDelete(row: LeaveRecordRead) {
  confirm.require({
    message: `Xóa bản ghi nghỉ phép của ${row.employee_name} (${row.start_date} — ${row.total_days} ngày)?`,
    header:  'Xác nhận xóa',
    icon:    'pi pi-exclamation-triangle',
    acceptLabel:  'Xóa',
    rejectLabel:  'Hủy',
    acceptClass:  'p-button-danger',
    accept: async () => {
      try {
        await leaveRecordService.remove(row.id)
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

// ── Init ──────────────────────────────────────────────────────────────────────

onMounted(() => {
  loadLeaveTypes()
  loadEmployees()
  load()
})
</script>
