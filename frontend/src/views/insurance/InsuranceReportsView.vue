<template>
  <div class="ins-reports-view">
    <!-- Header -->
    <div class="page-header insurance-header">
      <div>
        <h2 class="page-title">Báo cáo biến động BHXH</h2>
        <span class="page-subtitle">Tổng hợp và duyệt biến động tăng/giảm theo kỳ</span>
      </div>
      <div class="insurance-header-actions">
        <Button v-can:create="'insurance'" label="Tạo báo cáo mới" icon="pi pi-plus" @click="openCreateDialog" />
      </div>
    </div>

    <!-- Filters -->
    <div class="ins-reports-toolbar">
      <Select
        v-model="filterYear"
        :options="yearOptions"
        option-label="label"
        option-value="value"
        filter
        placeholder="Chọn năm"
        style="width: 130px"
        @change="loadReports"
      />
      <Select
        v-model="filterStatus"
        :options="statusOptions"
        option-label="label"
        option-value="value"
        placeholder="Tất cả trạng thái"
        show-clear
        style="width: 190px"
        @change="loadReports"
      />
      <Button icon="pi pi-refresh" text rounded @click="loadReports" :loading="loading" />
    </div>

    <!-- Table -->
    <div class="card">
      <DataTable
        :value="reports"
        :loading="loading"
        responsive-layout="scroll"
        row-hover
        striped-rows
        size="small"
      >
        <template #empty>
          <div class="ins-empty">Chưa có báo cáo nào cho năm {{ filterYear }}</div>
        </template>

        <Column header="Kỳ" style="min-width: 100px">
          <template #body="{ data }">
            <strong>T{{ String(data.period_month).padStart(2, '0') }}/{{ data.period_year }}</strong>
          </template>
        </Column>

        <Column header="Loại" style="min-width: 110px">
          <template #body="{ data }">
            <span>{{ submissionTypeLabel(data.submission_type) }}</span>
          </template>
        </Column>

        <Column header="Trạng thái" style="min-width: 140px">
          <template #body="{ data }">
            <span :class="statusClass(data.status)">{{ statusLabel(data.status) }}</span>
          </template>
        </Column>

        <Column header="Biến động" style="min-width: 110px">
          <template #body="{ data }">
            <span>{{ data.line_item_count }} dòng</span>
            <span v-if="data.adjusted_count" class="ins-adjusted-badge">
              &nbsp;· {{ data.adjusted_count }} điều chỉnh
            </span>
          </template>
        </Column>

        <Column header="Cảnh báo" style="min-width: 130px">
          <template #body="{ data }">
            <span v-if="data.missing_clinic_code_count" class="ins-line-missing-clinic">
              <i class="pi pi-exclamation-triangle" />
              {{ data.missing_clinic_code_count }} thiếu KCB
            </span>
          </template>
        </Column>

        <Column header="Hành động" style="width: 200px; text-align: right">
          <template #body="{ data }">
            <div class="ins-row-actions">
              <Button
                v-can:view="'insurance'"
                label="Xem"
                size="small"
                text
                icon="pi pi-eye"
                @click="goToDetail(data.id)"
              />
              <Button
                v-can:export="'insurance'"
                v-if="data.status === 'approved'"
                label="Xuất D02-TS"
                size="small"
                text
                icon="pi pi-download"
                :loading="exportingId === data.id"
                @click="exportReport(data)"
              />
              <Button
                v-can:delete="'insurance'"
                v-if="data.status === 'draft'"
                icon="pi pi-trash"
                size="small"
                text
                severity="danger"
                :loading="deletingId === data.id"
                @click="confirmDelete(data)"
              />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Create Dialog -->
    <Dialog
      v-model:visible="showCreateDialog"
      header="Tạo báo cáo biến động mới"
      modal
      style="width: 420px"
    >
      <div class="ins-create-form">
        <div class="field">
          <label>Năm</label>
          <Select
            v-model="createForm.period_year"
            :options="yearOptions"
            option-label="label"
            option-value="value"
            class="w-full"
            filter
          />
        </div>
        <div class="field">
          <label>Tháng</label>
          <Select
            v-model="createForm.period_month"
            :options="monthOptions"
            option-label="label"
            option-value="value"
            class="w-full"
          />
        </div>
        <div class="field">
          <label>Loại báo cáo</label>
          <Select
            v-model="createForm.submission_type"
            :options="submissionTypeOptions"
            option-label="label"
            option-value="value"
            class="w-full"
          />
        </div>
        <div class="field">
          <label>Ghi chú</label>
          <InputText v-model="createForm.note" class="w-full" placeholder="Tuỳ chọn" />
        </div>
      </div>
      <template #footer>
        <Button label="Hủy" text @click="showCreateDialog = false" />
        <Button
          v-can:create="'insurance'"
          label="Tạo báo cáo"
          icon="pi pi-check"
          :loading="creating"
          @click="submitCreate"
        />
      </template>
    </Dialog>

    <Toast />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'

import insuranceService, {
  type InsurancePeriodReportRead,
  type ReportStatus,
  type SubmissionType,
} from '@/services/insuranceService'

const router = useRouter()
const toast = useToast()

// ── State ─────────────────────────────────────────────────────────────────────

const reports = ref<InsurancePeriodReportRead[]>([])
const loading = ref(false)
const exportingId = ref<number | null>(null)
const deletingId = ref<number | null>(null)

const currentYear = new Date().getFullYear()
const filterYear = ref(currentYear)
const filterStatus = ref<string | null>(null)

const showCreateDialog = ref(false)
const creating = ref(false)
const createForm = ref({
  period_year: currentYear,
  period_month: new Date().getMonth() + 1,
  submission_type: 'initial' as SubmissionType,
  note: '',
})

// ── Options ───────────────────────────────────────────────────────────────────

const yearOptions = Array.from({ length: 6 }, (_, i) => {
  const y = currentYear - 2 + i
  return { label: String(y), value: y }
})

const monthOptions = Array.from({ length: 12 }, (_, i) => ({
  label: `Tháng ${i + 1}`,
  value: i + 1,
}))

const statusOptions = [
  { label: 'Nháp', value: 'draft' },
  { label: 'Chờ duyệt', value: 'pending_review' },
  { label: 'Đã duyệt', value: 'approved' },
  { label: 'Bị trả lại', value: 'rejected' },
]

const submissionTypeOptions = [
  { label: 'Lần đầu (initial)', value: 'initial' },
  { label: 'Bổ sung (supplement)', value: 'supplement' },
  { label: 'Đính chính (correction)', value: 'correction' },
]

// ── Helpers ───────────────────────────────────────────────────────────────────

function statusClass(s: ReportStatus) {
  const map: Record<ReportStatus, string> = {
    draft: 'ins-report-status-draft',
    pending_review: 'ins-report-status-pending',
    approved: 'ins-report-status-approved',
    rejected: 'ins-report-status-rejected',
  }
  return map[s] ?? ''
}

function statusLabel(s: ReportStatus) {
  const map: Record<ReportStatus, string> = {
    draft: '✎ Nháp',
    pending_review: '◌ Chờ duyệt',
    approved: '● Đã duyệt',
    rejected: '✕ Bị trả lại',
  }
  return map[s] ?? s
}

function submissionTypeLabel(t: SubmissionType) {
  const map: Record<SubmissionType, string> = {
    initial: 'Lần đầu',
    supplement: 'Bổ sung',
    correction: 'Đính chính',
  }
  return map[t] ?? t
}

// ── Data loading ──────────────────────────────────────────────────────────────

async function loadReports() {
  loading.value = true
  try {
    const res = await insuranceService.listReports({
      year: filterYear.value,
      status: filterStatus.value ?? undefined,
      page_size: 50,
    })
    reports.value = res.data.items
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không tải được danh sách báo cáo', life: 3000 })
  } finally {
    loading.value = false
  }
}

// ── Actions ───────────────────────────────────────────────────────────────────

function goToDetail(id: number) {
  router.push({ name: 'insurance-report-detail', params: { id } })
}

function openCreateDialog() {
  createForm.value = {
    period_year: currentYear,
    period_month: new Date().getMonth() + 1,
    submission_type: 'initial',
    note: '',
  }
  showCreateDialog.value = true
}

async function submitCreate() {
  creating.value = true
  try {
    await insuranceService.createReport({
      period_year: createForm.value.period_year,
      period_month: createForm.value.period_month,
      submission_type: createForm.value.submission_type,
      note: createForm.value.note || null,
    })
    showCreateDialog.value = false
    toast.add({ severity: 'success', summary: 'Đã tạo', detail: 'Báo cáo mới đã được tạo và tự nạp biến động', life: 3000 })
    await loadReports()
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Không tạo được báo cáo'
    toast.add({ severity: 'error', summary: 'Lỗi', detail: msg, life: 4000 })
  } finally {
    creating.value = false
  }
}

async function exportReport(report: InsurancePeriodReportRead) {
  exportingId.value = report.id
  try {
    const res = await insuranceService.exportReportD02Ts(report.id)
    const url = URL.createObjectURL(new Blob([res.data]))
    const a = document.createElement('a')
    a.href = url
    a.download = `D02-TS_BaoCao${report.id}_T${String(report.period_month).padStart(2, '0')}_${report.period_year}_VNPT.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi xuất file', detail: 'Không thể xuất D02-TS', life: 3000 })
  } finally {
    exportingId.value = null
  }
}

async function confirmDelete(report: InsurancePeriodReportRead) {
  if (!confirm(`Xóa báo cáo T${String(report.period_month).padStart(2, '0')}/${report.period_year}?`)) return
  deletingId.value = report.id
  try {
    await insuranceService.deleteReport(report.id)
    toast.add({ severity: 'success', summary: 'Đã xóa', detail: 'Báo cáo đã được xóa', life: 3000 })
    await loadReports()
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Không xóa được báo cáo'
    toast.add({ severity: 'error', summary: 'Lỗi', detail: msg, life: 4000 })
  } finally {
    deletingId.value = null
  }
}

onMounted(loadReports)
</script>
