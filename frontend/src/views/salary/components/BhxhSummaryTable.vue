<template>
  <div>
    <!-- Toolbar -->
    <div class="salary-basis-toolbar">
      <Select
        v-model="filterYear"
        :options="yearOptions"
        option-label="label"
        option-value="value"
        placeholder="Năm"
        filter
        style="width: 110px"
      />
      <Select
        v-model="filterMonth"
        :options="monthOptions"
        option-label="label"
        option-value="value"
        placeholder="Tháng"
        filter
        style="width: 130px"
      />
      <Select
        v-model="filterDeptId"
        :options="departments"
        option-label="name"
        option-value="id"
        placeholder="Tất cả phòng ban"
        show-clear
        filter
        style="width: 220px"
      />
      <Button label="Xem" icon="pi pi-search" :loading="loading" @click="loadSummary" />
      <Button
        label="Xuất Excel"
        icon="pi pi-file-excel"
        outlined
        :loading="isExporting"
        :disabled="!summaryData"
        @click="exportExcel"
      />
    </div>

    <!-- Rates banner -->
    <div v-if="summaryData" class="salary-summary-rates-banner">
      <span class="salary-summary-rates-label">Tỷ lệ áp dụng:</span>
      <span class="salary-summary-rates-group">
        <strong>NLĐ:</strong>
        BHXH {{ fmtRate(summaryData.rates.bhxh_employee_rate) }}%
        + BHYT {{ fmtRate(summaryData.rates.bhyt_employee_rate) }}%
        + BHTN {{ fmtRate(summaryData.rates.bhtn_employee_rate) }}%
      </span>
      <span class="salary-summary-rates-sep">|</span>
      <span class="salary-summary-rates-group">
        <strong>NSDLĐ:</strong>
        BHXH {{ fmtRate(summaryData.rates.bhxh_employer_rate) }}%
        + BHYT {{ fmtRate(summaryData.rates.bhyt_employer_rate) }}%
        + BHTN {{ fmtRate(summaryData.rates.bhtn_employer_rate) }}%
      </span>
    </div>

    <!-- Table -->
    <div class="card salary-summary-table-card">
      <DataTable
        :value="summaryData?.items ?? []"
        :loading="loading"
        responsive-layout="scroll"
        striped-rows
        size="small"
      >
        <template #empty>
          <div class="salary-summary-empty">
            <span v-if="summaryData">Không có nhân viên nào đang đóng BHXH trong tháng này</span>
            <span v-else>Chọn năm, tháng và nhấn Xem để tải dữ liệu</span>
          </div>
        </template>

        <Column header="STT" style="min-width: 60px; text-align: center">
          <template #body="{ data }: { data: SalarySummaryRow }">
            <span class="salary-summary-stt">{{ data.stt }}</span>
          </template>
          <template #footer>
            <span class="salary-summary-footer-label">TỔNG CỘNG</span>
          </template>
        </Column>

        <Column header="Mã NV" style="min-width: 100px">
          <template #body="{ data }: { data: SalarySummaryRow }">
            {{ data.employee_code }}
          </template>
          <template #footer>
            <span class="salary-summary-footer-sub">
              {{ summaryData ? `(${summaryData.totals.total_employees} NV)` : '' }}
            </span>
          </template>
        </Column>

        <Column header="Họ và tên" style="min-width: 180px">
          <template #body="{ data }: { data: SalarySummaryRow }">
            {{ data.full_name }}
          </template>
          <template #footer />
        </Column>

        <Column header="Phòng ban" style="min-width: 140px">
          <template #body="{ data }: { data: SalarySummaryRow }">
            {{ data.department_name || '—' }}
          </template>
          <template #footer />
        </Column>

        <Column header="Lương BHXH" style="min-width: 140px; text-align: right">
          <template #body="{ data }: { data: SalarySummaryRow }">
            <span class="salary-summary-col-basis">{{ fmtVND(data.basis_amount) }}</span>
          </template>
          <template #footer>
            <span class="salary-summary-col-basis salary-summary-footer-num">
              {{ summaryData ? fmtVND(summaryData.totals.sum_basis) : '' }}
            </span>
          </template>
        </Column>

        <Column :header="`BHXH NLĐ (${rateLabel('bhxh_employee_rate')}%)`" style="min-width: 130px; text-align: right">
          <template #body="{ data }: { data: SalarySummaryRow }">
            <span class="salary-summary-num">{{ fmtVND(data.bhxh_employee) }}</span>
          </template>
          <template #footer>
            <span class="salary-summary-footer-num">{{ summaryData ? fmtVND(summaryData.totals.sum_bhxh_employee) : '' }}</span>
          </template>
        </Column>

        <Column :header="`BHYT NLĐ (${rateLabel('bhyt_employee_rate')}%)`" style="min-width: 130px; text-align: right">
          <template #body="{ data }: { data: SalarySummaryRow }">
            <span class="salary-summary-num">{{ fmtVND(data.bhyt_employee) }}</span>
          </template>
          <template #footer>
            <span class="salary-summary-footer-num">{{ summaryData ? fmtVND(summaryData.totals.sum_bhyt_employee) : '' }}</span>
          </template>
        </Column>

        <Column :header="`BHTN NLĐ (${rateLabel('bhtn_employee_rate')}%)`" style="min-width: 130px; text-align: right">
          <template #body="{ data }: { data: SalarySummaryRow }">
            <span class="salary-summary-num">{{ fmtVND(data.bhtn_employee) }}</span>
          </template>
          <template #footer>
            <span class="salary-summary-footer-num">{{ summaryData ? fmtVND(summaryData.totals.sum_bhtn_employee) : '' }}</span>
          </template>
        </Column>

        <Column header="Tổng NLĐ" style="min-width: 130px; text-align: right">
          <template #body="{ data }: { data: SalarySummaryRow }">
            <span class="salary-summary-col-subtotal">{{ fmtVND(data.total_employee) }}</span>
          </template>
          <template #footer>
            <span class="salary-summary-col-subtotal salary-summary-footer-num">
              {{ summaryData ? fmtVND(summaryData.totals.sum_total_employee) : '' }}
            </span>
          </template>
        </Column>

        <Column :header="`BHXH NSDLĐ (${rateLabel('bhxh_employer_rate')}%)`" style="min-width: 150px; text-align: right">
          <template #body="{ data }: { data: SalarySummaryRow }">
            <span class="salary-summary-num">{{ fmtVND(data.bhxh_employer) }}</span>
          </template>
          <template #footer>
            <span class="salary-summary-footer-num">{{ summaryData ? fmtVND(summaryData.totals.sum_bhxh_employer) : '' }}</span>
          </template>
        </Column>

        <Column :header="`BHYT NSDLĐ (${rateLabel('bhyt_employer_rate')}%)`" style="min-width: 150px; text-align: right">
          <template #body="{ data }: { data: SalarySummaryRow }">
            <span class="salary-summary-num">{{ fmtVND(data.bhyt_employer) }}</span>
          </template>
          <template #footer>
            <span class="salary-summary-footer-num">{{ summaryData ? fmtVND(summaryData.totals.sum_bhyt_employer) : '' }}</span>
          </template>
        </Column>

        <Column :header="`BHTN NSDLĐ (${rateLabel('bhtn_employer_rate')}%)`" style="min-width: 150px; text-align: right">
          <template #body="{ data }: { data: SalarySummaryRow }">
            <span class="salary-summary-num">{{ fmtVND(data.bhtn_employer) }}</span>
          </template>
          <template #footer>
            <span class="salary-summary-footer-num">{{ summaryData ? fmtVND(summaryData.totals.sum_bhtn_employer) : '' }}</span>
          </template>
        </Column>

        <Column header="Tổng NSDLĐ" style="min-width: 130px; text-align: right">
          <template #body="{ data }: { data: SalarySummaryRow }">
            <span class="salary-summary-col-subtotal">{{ fmtVND(data.total_employer) }}</span>
          </template>
          <template #footer>
            <span class="salary-summary-col-subtotal salary-summary-footer-num">
              {{ summaryData ? fmtVND(summaryData.totals.sum_total_employer) : '' }}
            </span>
          </template>
        </Column>

        <Column header="Tổng cộng" style="min-width: 140px; text-align: right">
          <template #body="{ data }: { data: SalarySummaryRow }">
            <span class="salary-summary-col-grand">{{ fmtVND(data.grand_total) }}</span>
          </template>
          <template #footer>
            <span class="salary-summary-col-grand salary-summary-footer-num">
              {{ summaryData ? fmtVND(summaryData.totals.sum_grand_total) : '' }}
            </span>
          </template>
        </Column>
      </DataTable>

      <div v-if="summaryData" class="salary-summary-footer-info">
        Tổng: {{ summaryData.totals.total_employees }} nhân viên đang đóng BHXH —
        Tháng {{ String(summaryData.month).padStart(2, '0') }}/{{ summaryData.year }}
      </div>
    </div>

    <!-- Progress Dialog for Asynchronous Queue Export -->
    <Dialog v-model:visible="showExportDialog" modal header="Đang chuẩn bị tệp tin..." :closable="false" style="width: 25rem">
      <div class="text-center p-4">
        <ProgressSpinner v-if="exportProgress === 0" style="width: 50px; height: 50px" />
        <ProgressBar v-else :value="exportProgress" style="height: 6px" class="mt-3"></ProgressBar>
        <p class="mt-3">Hệ thống đang chuẩn bị tệp tin của bạn. Vui lòng không đóng trình duyệt hoặc tải lại trang.</p>
        <Button label="Hủy" class="mt-2" severity="secondary" @click="cancelExport" />
      </div>
    </Dialog>

    <Toast />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Select from 'primevue/select'
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'
import Dialog from 'primevue/dialog'
import ProgressSpinner from 'primevue/progressspinner'
import ProgressBar from 'primevue/progressbar'

import { usePermissionGate } from '@/composables/usePermissionGate'
import departmentService, { type DepartmentRead } from '@/services/departmentService'
import salaryService, { type SalarySummaryPage, type SalarySummaryRow } from '@/services/salaryService'
import { useExportQueue } from '@/composables/useExportQueue'

// ── State ─────────────────────────────────────────────────────────────────────

const now = new Date()
const permissionGate = usePermissionGate()
const canLoadDepartments = computed(() => permissionGate.canAccessRoute('/org/departments'))
const filterYear = ref(now.getFullYear())
const filterMonth = ref(now.getMonth() + 1)
const filterDeptId = ref<number | null>(null)
const summaryData = ref<SalarySummaryPage | null>(null)
const loading = ref(false)
const { isExporting, exportProgress, showExportDialog, startExport, cancelExport } = useExportQueue()
const departments = ref<DepartmentRead[]>([])
const toast = useToast()

// ── Options ───────────────────────────────────────────────────────────────────

const currentYear = now.getFullYear()
const yearOptions = Array.from({ length: currentYear - 2019 }, (_, i) => {
  const y = 2020 + i
  return { label: String(y), value: y }
}).reverse()

const monthOptions = Array.from({ length: 12 }, (_, i) => ({
  label: `Tháng ${String(i + 1).padStart(2, '0')}`,
  value: i + 1,
}))

// ── Data loading ──────────────────────────────────────────────────────────────

async function loadSummary() {
  loading.value = true
  try {
    const res = await salaryService.getSalarySummary({
      year: filterYear.value,
      month: filterMonth.value,
      department_id: filterDeptId.value,
      page_size: 500,
    })
    summaryData.value = res.data
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    toast.add({
      severity: 'error',
      summary: 'Lỗi tải dữ liệu',
      detail: typeof msg === 'string' ? msg : 'Không thể tải bảng tổng hợp lương BHXH',
      life: 5000,
    })
    summaryData.value = null
  } finally {
    loading.value = false
  }
}

async function exportExcel() {
  if (!summaryData.value) return
  const filters = {
    year: filterYear.value,
    month: filterMonth.value,
    department_id: filterDeptId.value,
  }
  const filename = `luong_bhxh_${filterYear.value}_${String(filterMonth.value).padStart(2, '0')}.xlsx`
  await startExport('salary-summary', filters, filename)
}

async function loadDepartments() {
  if (!canLoadDepartments.value) {
    departments.value = []
    return
  }
  try {
    const res = await departmentService.getList(true)
    departments.value = res.data
  } catch {
    departments.value = []
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtVND(val: string | number | null | undefined): string {
  if (val === null || val === undefined) return '—'
  return Number(val).toLocaleString('vi-VN') + ' đ'
}

function fmtRate(val: string): string {
  return parseFloat(val).toString()
}

function rateLabel(key: keyof SalarySummaryPage['rates']): string {
  if (!summaryData.value) return ''
  return fmtRate(summaryData.value.rates[key])
}

onMounted(() => {
  loadDepartments()
})
</script>
