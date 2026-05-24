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
        v-model="filterMonth"
        :options="monthOptions"
        option-label="label"
        option-value="value"
        placeholder="Tháng"
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
        label="Nhập KPI"
        icon="pi pi-plus"
        class="ml-auto"
        @click="openCreate"
      />
      <Button
        label="Import Excel"
        icon="pi pi-upload"
        severity="secondary"
        outlined
        @click="showImportDialog = true"
      />
      <Button
        icon="pi pi-download"
        severity="secondary"
        text
        rounded
        v-tooltip.top="'Tải file mẫu'"
        :loading="downloadingTemplate"
        @click="downloadTemplate"
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
          <div class="perf-empty">Không có dữ liệu KPI</div>
        </template>

        <Column header="Mã NV" style="width: 110px">
          <template #body="{ data }: { data: KpiMonthlyRead }">
            <span class="perf-emp-code">{{ data.employee_code }}</span>
          </template>
        </Column>

        <Column header="Họ và tên" style="min-width: 160px">
          <template #body="{ data }: { data: KpiMonthlyRead }">
            <span>{{ data.employee_name }}</span>
            <div v-if="data.department_name" class="perf-dept-name">{{ data.department_name }}</div>
          </template>
        </Column>

        <Column header="Năm" style="width: 70px; text-align: center">
          <template #body="{ data }: { data: KpiMonthlyRead }">{{ data.year }}</template>
        </Column>

        <Column header="Tháng" style="width: 70px; text-align: center">
          <template #body="{ data }: { data: KpiMonthlyRead }">{{ data.month }}</template>
        </Column>

        <Column header="Điểm KPI" style="width: 100px; text-align: center">
          <template #body="{ data }: { data: KpiMonthlyRead }">
            <span :class="scoreClass(data.score)" class="perf-score">
              {{ Number(data.score).toFixed(1) }}
            </span>
          </template>
        </Column>

        <Column header="Ghi chú" style="min-width: 140px">
          <template #body="{ data }: { data: KpiMonthlyRead }">
            <span class="perf-note">{{ data.note ? data.note.slice(0, 50) + (data.note.length > 50 ? '…' : '') : '—' }}</span>
          </template>
        </Column>

        <Column header="Người nhập" style="min-width: 120px">
          <template #body="{ data }: { data: KpiMonthlyRead }">
            <span class="perf-muted">{{ data.created_by_name ?? '—' }}</span>
          </template>
        </Column>

        <Column header="" style="width: 90px; text-align: right">
          <template #body="{ data }: { data: KpiMonthlyRead }">
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

    <!-- Dialog tạo/sửa KPI -->
    <Dialog
      v-model:visible="showDialog"
      :header="editingId ? 'Sửa điểm KPI' : 'Nhập điểm KPI'"
      modal
      :style="{ width: '480px' }"
      :closable="!saving"
    >
      <div class="perf-form">
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
          >
            <template #option="{ option }">
              <span class="perf-emp-code">{{ option.display_code }}</span>
              <span class="perf-sep">·</span>
              {{ option.full_name }}
            </template>
          </Select>
          <span v-if="errors.employee_id" class="perf-error">{{ errors.employee_id }}</span>
        </div>

        <div class="perf-row">
          <div class="perf-field">
            <label class="perf-label">Năm <span class="perf-req">*</span></label>
            <InputNumber
              v-model="form.year"
              :min="2000"
              :max="2100"
              :use-grouping="false"
              class="w-full"
              placeholder="VD: 2026"
            />
            <span v-if="errors.year" class="perf-error">{{ errors.year }}</span>
          </div>
          <div class="perf-field">
            <label class="perf-label">Tháng <span class="perf-req">*</span></label>
            <Select
              v-model="form.month"
              :options="monthOptions"
              option-label="label"
              option-value="value"
              placeholder="Chọn tháng"
              filter
              class="w-full"
            />
            <span v-if="errors.month" class="perf-error">{{ errors.month }}</span>
          </div>
        </div>

        <div class="perf-field">
          <label class="perf-label">Điểm KPI <span class="perf-req">*</span></label>
          <InputNumber
            v-model="form.score"
            :min="0"
            :max="100"
            :max-fraction-digits="2"
            :step="0.1"
            mode="decimal"
            class="w-full"
            placeholder="0 – 100"
          />
          <span v-if="errors.score" class="perf-error">{{ errors.score }}</span>
        </div>

        <div class="perf-field">
          <label class="perf-label">Ghi chú <span class="perf-optional">(tùy chọn)</span></label>
          <Textarea v-model="form.note" rows="2" class="w-full" auto-resize placeholder="Ghi chú..." />
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

    <!-- Dialog import Excel -->
    <Dialog
      v-model:visible="showImportDialog"
      header="Import KPI từ Excel"
      modal
      :style="{ width: '460px' }"
      :closable="!importing"
    >
      <div class="perf-import-body">
        <p class="perf-import-hint">
          Chọn file <strong>.xlsx</strong> theo mẫu. Dòng trùng (nhân viên + năm + tháng) sẽ được cập nhật.
        </p>

        <div class="perf-import-file-row">
          <input
            ref="importFileRef"
            type="file"
            accept=".xlsx"
            style="display: none"
            @change="onImportFileChange"
          />
          <Button
            icon="pi pi-upload"
            label="Chọn file .xlsx"
            severity="secondary"
            outlined
            @click="importFileRef?.click()"
          />
          <span v-if="importFile" class="perf-import-filename">{{ importFile.name }}</span>
        </div>

        <div v-if="importResult" class="perf-import-result">
          <div class="perf-import-counts">
            <span class="perf-import-created">Tạo mới: <strong>{{ importResult.created }}</strong></span>
            <span class="perf-import-updated">Cập nhật: <strong>{{ importResult.updated }}</strong></span>
            <span class="perf-import-skipped">Bỏ qua: <strong>{{ importResult.skipped }}</strong></span>
          </div>
          <div v-if="importResult.errors.length" class="perf-import-errors">
            <p class="perf-import-errors-title"><i class="pi pi-exclamation-triangle" /> Các dòng lỗi:</p>
            <ul>
              <li v-for="(e, i) in importResult.errors" :key="i">{{ e }}</li>
            </ul>
          </div>
        </div>

        <p v-if="importError" class="perf-api-error">
          <i class="pi pi-exclamation-triangle" />
          {{ importError }}
        </p>
      </div>

      <template #footer>
        <Button label="Đóng" severity="secondary" text :disabled="importing" @click="closeImportDialog" />
        <Button
          label="Import"
          icon="pi pi-upload"
          :loading="importing"
          :disabled="!importFile"
          @click="doImport"
        />
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
import Textarea from 'primevue/textarea'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'

import performanceService, { type KpiMonthlyRead, type KpiImportResult } from '@/services/performanceService'
import departmentService, { type DepartmentRead } from '@/services/departmentService'
import employeeService, { type EmployeeLookupItem } from '@/services/employeeService'

const confirm = useConfirm()
const toast   = useToast()

// ── State ─────────────────────────────────────────────────────────────────────

const loading  = ref(false)
const items    = ref<KpiMonthlyRead[]>([])
const total    = ref(0)
const page     = ref(1)
const pageSize = ref(20)

const departments = ref<DepartmentRead[]>([])
const employees   = ref<EmployeeLookupItem[]>([])

// Filters
const filterYear   = ref<number | null>(new Date().getFullYear())
const filterMonth  = ref<number | null>(null)
const filterDeptId = ref<number | null>(null)
const filterSearch = ref('')

// Dialog tạo/sửa
const showDialog  = ref(false)
const saving      = ref(false)
const editingId   = ref<number | null>(null)
const dialogError = ref('')
const errors      = ref<Record<string, string>>({})

const form = ref<{
  employee_id: number | null
  year: number | null
  month: number | null
  score: number | null
  note: string
}>({
  employee_id: null,
  year: new Date().getFullYear(),
  month: new Date().getMonth() + 1,
  score: null,
  note: '',
})

// Dialog import
const showImportDialog = ref(false)
const importing        = ref(false)
const importFile       = ref<File | null>(null)
const importFileRef    = ref<HTMLInputElement | null>(null)
const importResult     = ref<KpiImportResult | null>(null)
const importError      = ref('')

const downloadingTemplate = ref(false)

// ── Options ───────────────────────────────────────────────────────────────────

const currentYear = new Date().getFullYear()
const yearOptions = Array.from({ length: 10 }, (_, i) => ({
  label: String(currentYear - i),
  value: currentYear - i,
}))

const monthOptions = Array.from({ length: 12 }, (_, i) => ({
  label: `Tháng ${i + 1}`,
  value: i + 1,
}))

// ── Score coloring ────────────────────────────────────────────────────────────

function scoreClass(score: string): string {
  const n = Number(score)
  if (n >= 90) return 'perf-score-high'
  if (n >= 70) return 'perf-score-mid'
  return 'perf-score-low'
}

// ── Load ──────────────────────────────────────────────────────────────────────

async function load() {
  loading.value = true
  try {
    const res = await performanceService.list({
      year:          filterYear.value ?? undefined,
      month:         filterMonth.value ?? undefined,
      department_id: filterDeptId.value ?? undefined,
      search:        filterSearch.value || undefined,
      page:          page.value,
      page_size:     pageSize.value,
    })
    items.value = res.data.items
    total.value = res.data.total
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể tải danh sách KPI', life: 4000 })
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
  filterMonth.value  = null
  filterDeptId.value = null
  filterSearch.value = ''
  page.value = 1
  load()
}

function onPage(e: { page: number; rows: number }) {
  page.value = e.page + 1
  pageSize.value = e.rows
  load()
}

// ── Dialog tạo/sửa ───────────────────────────────────────────────────────────

function openCreate() {
  editingId.value = null
  dialogError.value = ''
  errors.value = {}
  Object.assign(form.value, {
    employee_id: null,
    year: new Date().getFullYear(),
    month: new Date().getMonth() + 1,
    score: null,
    note: '',
  })
  showDialog.value = true
}

function openEdit(row: KpiMonthlyRead) {
  editingId.value = row.id
  dialogError.value = ''
  errors.value = {}
  Object.assign(form.value, {
    employee_id: row.employee_id,
    year: row.year,
    month: row.month,
    score: Number(row.score),
    note: row.note ?? '',
  })
  showDialog.value = true
}

function validate(): boolean {
  errors.value = {}
  if (!form.value.employee_id)                    errors.value.employee_id = 'Vui lòng chọn nhân viên'
  if (!form.value.year)                           errors.value.year        = 'Vui lòng nhập năm'
  if (!form.value.month)                          errors.value.month       = 'Vui lòng chọn tháng'
  if (form.value.score === null || form.value.score === undefined)
                                                  errors.value.score       = 'Vui lòng nhập điểm KPI'
  return Object.keys(errors.value).length === 0
}

async function submit() {
  if (!validate()) return
  saving.value = true
  dialogError.value = ''
  try {
    if (editingId.value) {
      await performanceService.update(editingId.value, {
        score: form.value.score!,
        note:  form.value.note.trim() || null,
      })
      toast.add({ severity: 'success', summary: 'Đã cập nhật', detail: 'Điểm KPI đã được cập nhật', life: 3000 })
    } else {
      await performanceService.create({
        employee_id: form.value.employee_id!,
        year:        form.value.year!,
        month:       form.value.month!,
        score:       form.value.score!,
        note:        form.value.note.trim() || null,
      })
      toast.add({ severity: 'success', summary: 'Đã lưu', detail: 'Điểm KPI đã được nhập', life: 3000 })
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

function confirmDelete(row: KpiMonthlyRead) {
  confirm.require({
    message: `Xóa điểm KPI tháng ${row.month}/${row.year} của ${row.employee_name}?`,
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
    await performanceService.delete(id)
    toast.add({ severity: 'success', summary: 'Đã xóa', detail: 'Bản ghi KPI đã được xóa', life: 3000 })
    load()
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể xóa bản ghi KPI', life: 4000 })
  }
}

// ── Import ────────────────────────────────────────────────────────────────────

function onImportFileChange(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (f) {
    importFile.value = f
    importResult.value = null
    importError.value = ''
  }
}

function closeImportDialog() {
  showImportDialog.value = false
  importFile.value = null
  importResult.value = null
  importError.value = ''
  if (importFileRef.value) importFileRef.value.value = ''
}

async function doImport() {
  if (!importFile.value) return
  importing.value = true
  importError.value = ''
  importResult.value = null
  try {
    const res = await performanceService.importExcel(importFile.value)
    importResult.value = res.data
    if (res.data.created > 0 || res.data.updated > 0) {
      load()
    }
  } catch (err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    importError.value = typeof detail === 'string' ? detail : 'Import thất bại, vui lòng kiểm tra lại file'
  } finally {
    importing.value = false
    importFile.value = null
    if (importFileRef.value) importFileRef.value.value = ''
  }
}

// ── Download template ─────────────────────────────────────────────────────────

async function downloadTemplate() {
  downloadingTemplate.value = true
  try {
    const res = await performanceService.downloadTemplate()
    const url = URL.createObjectURL(new Blob([res.data as BlobPart]))
    const a = document.createElement('a')
    a.href = url
    a.download = 'mau_import_kpi.xlsx'
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể tải file mẫu', life: 3000 })
  } finally {
    downloadingTemplate.value = false
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
