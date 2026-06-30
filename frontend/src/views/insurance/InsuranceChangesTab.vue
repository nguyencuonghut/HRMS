<template>
  <div class="ins-changes-tab">
    <!-- Header with year selector and export buttons -->
    <div class="ins-changes-header">
      <span class="ins-changes-title">Biến động BHXH năm</span>
      <Select
        v-model="selectedYear"
        :options="yearOptions"
        option-label="label"
        option-value="value"
        class="ins-changes-year-select"
        @change="loadEvents"
      />
      <div class="ins-changes-export-group">
        <Button
          v-can:export="'insurance'"
          label="Xuất D02-TS (VNPT)"
          icon="pi pi-file-excel"
          severity="secondary"
          outlined
          :disabled="!selectedMonth"
          @click="exportD02Ts"
        />
      </div>
    </div>

    <!-- Monthly summary table -->
    <div class="card">
      <div class="ins-changes-section-title">Tổng hợp theo tháng</div>
      <DataTable
        :value="monthlySummaries"
        :loading="loading"
        size="small"
        :row-class="summaryRowClass"
        @row-click="onMonthRowClick"
      >
        <Column header="Tháng" style="min-width:90px">
          <template #body="{ data }">
            <span :class="{ 'font-bold': data.month === selectedMonth }">
              T{{ data.month }}/{{ selectedYear }}
            </span>
          </template>
        </Column>
        <Column header="Tăng" style="min-width:65px;text-align:center" header-class="text-center">
          <template #body="{ data }">
            <span v-if="data.increase_count" class="ins-changes-badge-increase">+{{ data.increase_count }}</span>
            <span v-else class="text-muted">0</span>
          </template>
        </Column>
        <Column header="Giảm" style="min-width:65px;text-align:center" header-class="text-center">
          <template #body="{ data }">
            <span v-if="data.decrease_count" class="ins-changes-badge-decrease">-{{ data.decrease_count }}</span>
            <span v-else class="text-muted">0</span>
          </template>
        </Column>
        <Column header="Số dư" style="min-width:65px;text-align:center" header-class="text-center">
          <template #body="{ data }">
            <span :class="data.net >= 0 ? 'ins-changes-net-positive' : 'ins-changes-net-negative'">
              {{ data.net >= 0 ? '+' : '' }}{{ data.net }}
            </span>
          </template>
        </Column>
        <Column header="Thủ công" style="min-width:80px;text-align:center" header-class="text-center">
          <template #body="{ data }">
            <span v-if="data.manual_count" class="text-warning">{{ data.manual_count }}</span>
            <span v-else class="text-muted">—</span>
          </template>
        </Column>
        <Column header="Cảnh báo" style="min-width:180px">
          <template #body="{ data }">
            <span
              v-if="data.missing_clinic_count"
              class="ins-changes-warn"
              :title="`${data.missing_clinic_count} nhân viên tăng chưa có mã KCB (MaBenhVien) — file VNPT D02-TS sẽ bị trống cột này. Vui lòng cập nhật 'Nơi KCB ban đầu' trong hồ sơ bảo hiểm.`"
            >
              ⚠ Thiếu mã KCB ({{ data.missing_clinic_count }})
            </span>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Detail table -->
    <div class="card">
      <div class="ins-changes-detail-toolbar">
        <span class="ins-changes-section-title">
          Chi tiết {{ selectedMonth ? `tháng ${selectedMonth}/${selectedYear}` : `năm ${selectedYear}` }}
          <span v-if="selectedMonth" class="ins-changes-clear-month" @click="selectedMonth = null">(xem cả năm ×)</span>
        </span>
        <div class="ins-changes-detail-actions">
          <Select
            v-model="changeTypeFilter"
            :options="changeTypeOptions"
            option-label="label"
            option-value="value"
            filter
            class="ins-changes-type-filter"
          />
          <Button
            v-can:edit="'insurance'"
            label="+ Thêm thủ công"
            severity="secondary"
            @click="openAddDialog"
          />
        </div>
      </div>

      <DataTable
        :value="filteredEvents"
        :loading="loading"
        responsive-layout="scroll"
        empty-message="Không có biến động nào"
        size="small"
      >
        <Column header="Ngày hiệu lực" style="min-width:110px">
          <template #body="{ data }">{{ formatDate(data.effective_date) }}</template>
        </Column>
        <Column header="Nhân viên" style="min-width:180px">
          <template #body="{ data }">
            <div>{{ data.employee_name_snapshot }}</div>
            <small v-if="data.contract_number_snapshot" class="text-muted">HĐ {{ data.contract_number_snapshot }}</small>
          </template>
        </Column>
        <Column header="Mã BHXH" style="min-width:110px">
          <template #body="{ data }">
            <span v-if="data.bhxh_code_snapshot" class="ins-code">{{ data.bhxh_code_snapshot }}</span>
            <span v-else class="text-muted">—</span>
          </template>
        </Column>
        <Column header="Loại" style="min-width:80px">
          <template #body="{ data }">
            <Tag
              :value="data.change_type === 'increase' ? 'TĂNG' : 'GIẢM'"
              :severity="data.change_type === 'increase' ? 'success' : 'danger'"
            />
          </template>
        </Column>
        <Column header="Lý do" style="min-width:170px">
          <template #body="{ data }">
            <div>{{ changeReasonLabel(data.change_reason) }}</div>
            <small class="text-muted">{{ data.ibhxh_reason_code }}</small>
          </template>
        </Column>
        <Column header="Mức đóng" style="min-width:120px;text-align:right" header-class="text-right">
          <template #body="{ data }">{{ formatCurrency(data.basis_amount) }}</template>
        </Column>
        <Column header="" style="width:48px;text-align:center">
          <template #body="{ data }">
            <Button
              v-can:edit="'insurance'"
              v-if="data.is_manual"
              icon="pi pi-times"
              text
              rounded
              severity="danger"
              size="small"
              title="Xóa biến động thủ công"
              @click="confirmDelete(data)"
            />
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Add manual event dialog -->
    <Dialog
      v-model:visible="showAddDialog"
      header="Thêm biến động thủ công"
      modal
      :style="{ width: '500px' }"
      :closable="!saving"
    >
      <div class="ins-dialog-body">
        <div class="field">
          <label>Nhân viên <span class="req">*</span></label>
          <AutoComplete
            v-model="addForm.employee_selected"
            :suggestions="employeeSuggestions"
            :option-label="empOptionLabel"
            dropdown
            force-selection
            :loading="employeeSearchLoading"
            placeholder="Nhập mã hoặc tên nhân viên..."
            class="w-full"
            @complete="searchEmployees"
            @option-select="onEmployeeSelect"
            @clear="addForm.employee_id = null"
          >
            <template #option="{ option }">
              <span class="ins-emp-code">{{ option.display_code }}</span>
              <span class="ins-emp-name">{{ option.full_name }}</span>
            </template>
          </AutoComplete>
        </div>
        <div class="field-row">
          <div class="field">
            <label>Loại biến động <span class="req">*</span></label>
            <Select
              v-model="addForm.change_type"
              :options="changeTypeCreateOptions"
              option-label="label"
              option-value="value"
              filter
              class="w-full"
              @change="addForm.change_reason = null"
            />
          </div>
          <div class="field">
            <label>Lý do <span class="req">*</span></label>
            <Select
              v-model="addForm.change_reason"
              :options="filteredReasonOptions"
              option-label="label"
              option-value="value"
              filter
              :disabled="!addForm.change_type"
              placeholder="Chọn lý do..."
              class="w-full"
            />
          </div>
        </div>
        <div class="field">
          <label>Ngày hiệu lực <span class="req">*</span></label>
          <DatePicker
            v-model="addForm.effective_date_obj"
            date-format="dd/mm/yy"
            show-button-bar
            class="w-full"
          />
        </div>
        <div class="field">
          <label>Ghi chú</label>
          <InputText
            v-model="addForm.note"
            placeholder="Ghi chú (tùy chọn)..."
            class="w-full"
          />
        </div>
      </div>
      <template #footer>
        <Button label="Hủy" severity="secondary" text :disabled="saving" @click="showAddDialog = false" />
        <Button v-can:edit="'insurance'" label="Lưu" icon="pi pi-save" :loading="saving" @click="submitAdd" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AutoComplete from 'primevue/autocomplete'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import insuranceService, { type InsuranceChangeEventRead } from '@/services/insuranceService'
import employeeService, { type EmployeeLookupItem } from '@/services/employeeService'

const toast = useToast()
const now = new Date()

// ── State ─────────────────────────────────────────────────────────────────────

const selectedYear = ref(now.getFullYear())
const selectedMonth = ref<number | null>(now.getMonth() + 1)
const changeTypeFilter = ref('all')
const loading = ref(false)
const saving = ref(false)
const showAddDialog = ref(false)
const events = ref<InsuranceChangeEventRead[]>([])

// ── Options ───────────────────────────────────────────────────────────────────

const yearOptions = computed(() => {
  const y = now.getFullYear()
  return [y - 2, y - 1, y, y + 1].map(yr => ({ label: `Năm ${yr}`, value: yr }))
})

const changeTypeOptions = [
  { label: 'Tất cả',  value: 'all' },
  { label: 'Tăng',    value: 'increase' },
  { label: 'Giảm',    value: 'decrease' },
]

const changeTypeCreateOptions = [
  { label: 'Tăng', value: 'increase' },
  { label: 'Giảm', value: 'decrease' },
]

const reasonOptionsByType: Record<string, { label: string; value: string }[]> = {
  increase: [
    { label: 'Mới vào làm',              value: 'new_hire' },
    { label: 'Trở lại sau nghỉ',         value: 'return_from_leave' },
    { label: 'Chuyển từ đơn vị khác',    value: 'transfer_in' },
    { label: 'Gia hạn hợp đồng',         value: 'contract_renewal' },
  ],
  decrease: [
    { label: 'Nghỉ việc (tự nguyện)',    value: 'resignation' },
    { label: 'Hết hạn hợp đồng',         value: 'contract_end' },
    { label: 'Thôi việc (sa thải)',       value: 'dismissal' },
    { label: 'Nghỉ không lương',          value: 'unpaid_leave' },
    { label: 'Thai sản không đóng BH',    value: 'maternity_no_contribution' },
    { label: 'Nghỉ ốm dài ngày',          value: 'long_term_sick' },
    { label: 'Chuyển sang đơn vị khác',   value: 'transfer_out' },
    { label: 'Điều chỉnh thủ công',       value: 'manual_correction' },
  ],
}

const allReasonLabels: Record<string, string> = Object.fromEntries(
  [...reasonOptionsByType.increase, ...reasonOptionsByType.decrease].map(o => [o.value, o.label])
)

// ── Add form ──────────────────────────────────────────────────────────────────

interface AddForm {
  employee_id: number | null
  employee_selected: EmployeeLookupItem | null
  change_type: 'increase' | 'decrease' | null
  change_reason: string | null
  effective_date_obj: Date | null
  note: string | null
}

const addForm = ref<AddForm>({
  employee_id: null,
  employee_selected: null,
  change_type: null,
  change_reason: null,
  effective_date_obj: null,
  note: null,
})

const employeeSuggestions = ref<EmployeeLookupItem[]>([])
const employeeSearchLoading = ref(false)

async function searchEmployees(event: { query: string }) {
  employeeSearchLoading.value = true
  try {
    const res = await employeeService.lookup({ keyword: event.query || undefined, limit: 20 })
    employeeSuggestions.value = res.data
  } catch {
    employeeSuggestions.value = []
  } finally {
    employeeSearchLoading.value = false
  }
}

function onEmployeeSelect() {
  addForm.value.employee_id = addForm.value.employee_selected?.id ?? null
}

function empOptionLabel(e: EmployeeLookupItem): string {
  return `${e.display_code} — ${e.full_name}`
}

const filteredReasonOptions = computed(() =>
  addForm.value.change_type ? (reasonOptionsByType[addForm.value.change_type] ?? []) : []
)

// ── Computed ──────────────────────────────────────────────────────────────────

interface MonthlySummary {
  month: number
  increase_count: number
  decrease_count: number
  net: number
  manual_count: number
  missing_clinic_count: number
}

const monthlySummaries = computed((): MonthlySummary[] =>
  Array.from({ length: 12 }, (_, i) => {
    const m = i + 1
    const monthEvents = events.value.filter(e => e.period_month === m)
    const increases = monthEvents.filter(e => e.change_type === 'increase')
    const decreases = monthEvents.filter(e => e.change_type === 'decrease')
    return {
      month: m,
      increase_count: increases.length,
      decrease_count: decreases.length,
      net: increases.length - decreases.length,
      manual_count: monthEvents.filter(e => e.is_manual).length,
      missing_clinic_count: increases.filter(e => !e.bhyt_clinic_code_snapshot).length,
    }
  })
)

const filteredEvents = computed(() => {
  let list = events.value
  if (selectedMonth.value !== null)
    list = list.filter(e => e.period_month === selectedMonth.value)
  if (changeTypeFilter.value !== 'all')
    list = list.filter(e => e.change_type === changeTypeFilter.value)
  return [...list].sort((a, b) =>
    b.period_month !== a.period_month ? b.period_month - a.period_month : b.id - a.id
  )
})

// ── Helpers ───────────────────────────────────────────────────────────────────

function changeReasonLabel(val: string): string {
  return allReasonLabels[val] ?? val
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

function formatCurrency(val: string | number | null): string {
  if (val == null) return '—'
  return new Intl.NumberFormat('vi-VN', {
    style: 'currency',
    currency: 'VND',
    maximumFractionDigits: 0,
  }).format(Number(val))
}

function toIsoDate(d: Date | null): string | null {
  if (!d) return null
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${dd}`
}

function summaryRowClass(row: MonthlySummary) {
  return row.month === selectedMonth.value
    ? 'ins-changes-summary-row is-selected'
    : 'ins-changes-summary-row'
}

// ── Data loading ──────────────────────────────────────────────────────────────

async function loadEvents() {
  loading.value = true
  events.value = []
  try {
    const first = await insuranceService.listChangeEvents({
      period_year: selectedYear.value,
      page: 1,
      page_size: 100,
    })
    let all = [...first.data.items]
    if (first.data.total > 100) {
      const pages = Math.ceil(first.data.total / 100)
      const rest = await Promise.all(
        Array.from({ length: pages - 1 }, (_, i) =>
          insuranceService.listChangeEvents({
            period_year: selectedYear.value,
            page: i + 2,
            page_size: 100,
          })
        )
      )
      for (const r of rest) all = [...all, ...r.data.items]
    }
    events.value = all
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không tải được biến động', life: 3000 })
  } finally {
    loading.value = false
  }
}

// ── Actions ───────────────────────────────────────────────────────────────────

function onMonthRowClick(e: { data: MonthlySummary }) {
  selectedMonth.value = selectedMonth.value === e.data.month ? null : e.data.month
}

function openAddDialog() {
  addForm.value = {
    employee_id: null,
    employee_selected: null,
    change_type: null,
    change_reason: null,
    effective_date_obj: null,
    note: null,
  }
  showAddDialog.value = true
}

async function submitAdd() {
  const f = addForm.value
  if (!f.employee_id || !f.change_type || !f.change_reason || !f.effective_date_obj) {
    toast.add({ severity: 'warn', summary: 'Thiếu thông tin', detail: 'Vui lòng điền đầy đủ các trường bắt buộc', life: 3000 })
    return
  }
  saving.value = true
  try {
    await insuranceService.createManualChangeEvent({
      employee_id: f.employee_id,
      change_type: f.change_type,
      change_reason: f.change_reason,
      effective_date: toIsoDate(f.effective_date_obj)!,
      note: f.note || null,
    })
    toast.add({ severity: 'success', summary: 'Đã lưu', detail: 'Thêm biến động thành công', life: 3000 })
    showAddDialog.value = false
    await loadEvents()
  } catch (err: unknown) {
    const msg =
      (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
      'Không thể thêm biến động'
    toast.add({ severity: 'error', summary: 'Lỗi', detail: msg, life: 4000 })
  } finally {
    saving.value = false
  }
}

async function confirmDelete(event: InsuranceChangeEventRead) {
  if (
    !confirm(
      `Xóa biến động thủ công của ${event.employee_name_snapshot} ngày ${formatDate(event.effective_date)}?`
    )
  )
    return
  try {
    await insuranceService.deleteChangeEvent(event.id)
    toast.add({ severity: 'success', summary: 'Đã xóa', detail: 'Đã xóa biến động thủ công', life: 3000 })
    await loadEvents()
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể xóa biến động', life: 3000 })
  }
}

async function exportD02Ts() {
  if (!selectedMonth.value) return
  try {
    const res = await insuranceService.exportVnptD02Ts(selectedYear.value, selectedMonth.value)
    const url = URL.createObjectURL(new Blob([res.data as BlobPart]))
    const a = document.createElement('a')
    a.href = url
    a.download = `D02-TS_T${String(selectedMonth.value).padStart(2, '0')}_${selectedYear.value}_VNPT.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Không thể xuất file D02-TS'
    toast.add({ severity: 'error', summary: 'Lỗi xuất file', detail: msg, life: 4000 })
  }
}

onMounted(loadEvents)
</script>
