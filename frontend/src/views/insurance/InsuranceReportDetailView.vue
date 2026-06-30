<template>
  <div class="ins-report-detail-view">
    <!-- Back + Header -->
    <div class="page-header insurance-header">
      <div class="ins-detail-title-row">
        <Button icon="pi pi-arrow-left" text rounded @click="router.push({ name: 'insurance-reports' })" />
        <div>
          <h2 class="page-title" v-if="report">
            Báo cáo T{{ String(report.period_month).padStart(2, '0') }}/{{ report.period_year }}
            — {{ submissionTypeLabel(report.submission_type) }}
          </h2>
          <h2 class="page-title" v-else>Đang tải...</h2>
          <span v-if="report" :class="statusClass(report.status)" class="ins-detail-status">
            {{ statusLabel(report.status) }}
          </span>
        </div>
      </div>
      <div class="insurance-header-actions" v-if="report">
        <!-- Draft actions -->
        <template v-if="report.status === 'draft' || report.status === 'rejected'">
          <Button
            v-can:edit="'insurance'"
            label="Thêm biến động"
            icon="pi pi-plus"
            text
            @click="openAddItemDialog"
          />
          <Button
            v-can:edit="'insurance'"
            v-if="report.status === 'draft'"
            label="Nộp duyệt"
            icon="pi pi-send"
            :loading="actioning"
            @click="submitReport"
          />
        </template>
        <!-- Pending actions -->
        <template v-if="report.status === 'pending_review' && canReviewInsuranceReport">
          <Button
            v-can:edit="'insurance'"
            label="Trả lại"
            severity="secondary"
            icon="pi pi-undo"
            @click="openRejectDialog"
          />
          <Button
            v-can:edit="'insurance'"
            label="Phê duyệt"
            icon="pi pi-check"
            severity="success"
            :loading="actioning"
            @click="openApproveDialog"
          />
        </template>
        <!-- Approved actions -->
        <template v-if="report.status === 'approved'">
          <Button
            v-can:export="'insurance'"
            label="Xuất D02-TS"
            icon="pi pi-download"
            :loading="exporting"
            @click="exportReport"
          />
        </template>
      </div>
    </div>

    <!-- Warning banners -->
    <div v-if="report && report.missing_clinic_code_count > 0" class="insurance-note ins-note-warn">
      <i class="pi pi-exclamation-triangle" />
      <strong>{{ report.missing_clinic_code_count }} dòng tăng thiếu mã KCB</strong>
      — file VNPT D02-TS sẽ bị trống cột MaBenhVien. Vui lòng cập nhật "Nơi KCB ban đầu" trong hồ sơ bảo hiểm.
    </div>

    <div v-if="report && report.adjusted_count > 0" class="insurance-note ins-note-info">
      <i class="pi pi-info-circle" />
      {{ report.adjusted_count }} dòng đã được điều chỉnh tháng kê khai so với gợi ý hệ thống.
    </div>

    <!-- Review note (when rejected) -->
    <div v-if="report && report.status === 'rejected' && report.review_note" class="insurance-note ins-note-error">
      <strong>Lý do trả lại:</strong> {{ report.review_note }}
    </div>

    <!-- Preparer / Reviewer info -->
    <div v-if="report" class="ins-report-meta-row">
      <span v-if="report.prepared_by_name" class="ins-report-meta-item">
        <i class="pi pi-user" />
        <strong>Người lập:</strong> {{ report.prepared_by_name }}
        <template v-if="report.prepared_at">
          — {{ formatDateTime(report.prepared_at) }}
        </template>
      </span>
      <span v-if="report.reviewed_by_name" class="ins-report-meta-item">
        <i class="pi pi-check-circle" />
        <strong>Người xác nhận:</strong> {{ report.reviewed_by_name }}
        <template v-if="report.reviewed_at">
          — {{ formatDateTime(report.reviewed_at) }}
        </template>
      </span>
    </div>

    <!-- Line items table -->
    <div class="card">
      <DataTable
        :value="lineItems"
        :loading="loading"
        responsive-layout="scroll"
        row-hover
        size="small"
        :row-class="lineItemRowClass"
      >
        <template #empty>
          <div class="ins-empty">Báo cáo chưa có dòng biến động nào</div>
        </template>

        <Column header="#" style="width: 50px; text-align: center">
          <template #body="{ index }">{{ index + 1 }}</template>
        </Column>

        <Column header="Nhân viên" style="min-width: 180px">
          <template #body="{ data }">
            <div>
              <span class="ins-emp-code">{{ data.employee_code }}</span>
              <span class="ins-emp-name">&nbsp;{{ data.employee_name }}</span>
            </div>
          </template>
        </Column>

        <Column header="Mã BHXH" style="min-width: 110px">
          <template #body="{ data }">
            <span v-if="data.bhxh_code">{{ data.bhxh_code }}</span>
            <span v-else class="ins-text-muted">—</span>
          </template>
        </Column>

        <Column header="Loại" style="min-width: 80px">
          <template #body="{ data }">
            <Tag
              :value="data.change_type === 'increase' ? 'TĂNG' : 'GIẢM'"
              :severity="data.change_type === 'increase' ? 'success' : 'danger'"
              size="small"
            />
          </template>
        </Column>

        <Column header="Ngày hiệu lực" style="min-width: 120px">
          <template #body="{ data }">{{ fmtDate(data.effective_date) }}</template>
        </Column>

        <Column header="Tháng kê khai" style="min-width: 150px">
          <template #body="{ data }">
            <span
              :class="isEditable ? 'ins-declared-month-editable' : ''"
              :title="isEditable ? 'Click để điều chỉnh tháng kê khai' : ''"
              @click="isEditable && openAdjustDialog(data)"
            >
              {{ String(data.declared_month).padStart(2, '0') }}/{{ data.declared_year }}
              <i v-if="data.is_adjusted" class="pi pi-pencil ins-adjusted-icon" />
            </span>
            <div v-if="data.is_adjusted" class="ins-suggested-hint">
              gợi ý: {{ String(data.suggested_month).padStart(2, '0') }}/{{ data.suggested_year }}
            </div>
          </template>
        </Column>

        <Column header="" style="width: 50px; text-align: center">
          <template #body="{ data }">
            <span v-if="!data.bhyt_clinic_code" title="Thiếu mã KCB">
              <i class="pi pi-exclamation-triangle ins-line-missing-clinic" />
            </span>
          </template>
        </Column>

        <Column v-if="isEditable" header="" style="width: 60px">
          <template #body="{ data }">
            <Button
              v-can:delete="'insurance'"
              icon="pi pi-trash"
              text
              rounded
              severity="danger"
              size="small"
              @click="removeItem(data)"
            />
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Adjust declared month dialog -->
    <Dialog
      v-model:visible="adjustDialog.visible"
      header="Điều chỉnh tháng kê khai"
      modal
      style="width: 400px"
    >
      <div v-if="adjustDialog.item" class="ins-adjust-form">
        <div class="ins-adjust-info">
          <strong>Biến động:</strong>
          {{ adjustDialog.item.employee_code }} — {{ adjustDialog.item.employee_name }}<br />
          <strong>Gợi ý hệ thống:</strong>
          T{{ String(adjustDialog.item.suggested_month).padStart(2, '0') }}/{{ adjustDialog.item.suggested_year }}
        </div>
        <div class="field">
          <label>Tháng kê khai chính thức</label>
          <div class="ins-month-year-row">
            <Select
              v-model="adjustDialog.declared_month"
              :options="monthOptions"
              option-label="label"
              option-value="value"
              style="flex: 1"
            />
            <Select
              v-model="adjustDialog.declared_year"
              :options="yearOptions"
              option-label="label"
              option-value="value"
              style="flex: 1"
              filter
            />
          </div>
        </div>
        <div class="field">
          <label>Lý do điều chỉnh <span class="ins-required">*</span></label>
          <InputText
            v-model="adjustDialog.adjustment_note"
            class="w-full"
            placeholder="Bắt buộc nhập"
          />
        </div>
      </div>
      <template #footer>
        <Button label="Hủy" text @click="adjustDialog.visible = false" />
        <Button
          v-can:edit="'insurance'"
          label="Lưu điều chỉnh"
          icon="pi pi-check"
          :loading="adjustDialog.saving"
          @click="saveAdjust"
        />
      </template>
    </Dialog>

    <!-- Add line item dialog -->
    <Dialog
      v-model:visible="addItemDialog.visible"
      header="Thêm biến động vào báo cáo"
      modal
      style="width: 560px"
    >
      <div class="ins-add-item-form">
        <p class="ins-text-muted" style="margin: 0 0 0.75rem">
          Danh sách biến động trong kỳ chưa có trong báo cáo approved nào:
        </p>
        <DataTable
          :value="addItemDialog.availableEvents"
          :loading="addItemDialog.loadingEvents"
          selection-mode="single"
          v-model:selection="addItemDialog.selectedEvent"
          size="small"
          style="max-height: 320px; overflow-y: auto"
        >
          <template #empty>
            <div class="ins-empty">Không có biến động nào để thêm</div>
          </template>
          <Column header="Nhân viên" style="min-width: 150px">
            <template #body="{ data }">
              <span class="ins-emp-code">{{ data.employee_code }}</span>
              {{ data.employee_name }}
            </template>
          </Column>
          <Column header="Loại">
            <template #body="{ data }">
              <Tag
                :value="data.change_type === 'increase' ? 'TĂNG' : 'GIẢM'"
                :severity="data.change_type === 'increase' ? 'success' : 'danger'"
                size="small"
              />
            </template>
          </Column>
          <Column header="Ngày h/l">
            <template #body="{ data }">{{ fmtDate(data.effective_date) }}</template>
          </Column>
        </DataTable>
      </div>
      <template #footer>
        <Button label="Hủy" text @click="addItemDialog.visible = false" />
        <Button
          v-can:edit="'insurance'"
          label="Thêm vào báo cáo"
          icon="pi pi-plus"
          :disabled="!addItemDialog.selectedEvent"
          :loading="addItemDialog.saving"
          @click="saveAddItem"
        />
      </template>
    </Dialog>

    <!-- Approve dialog -->
    <Dialog
      v-model:visible="approveDialog.visible"
      header="Phê duyệt báo cáo"
      modal
      style="width: 400px"
    >
      <div class="field">
        <label>Ghi chú duyệt (tuỳ chọn)</label>
        <InputText v-model="approveDialog.note" class="w-full" />
      </div>
      <template #footer>
        <Button label="Hủy" text @click="approveDialog.visible = false" />
        <Button
          v-can:edit="'insurance'"
          label="Phê duyệt"
          icon="pi pi-check"
          severity="success"
          :loading="actioning"
          @click="doApprove"
        />
      </template>
    </Dialog>

    <!-- Reject dialog -->
    <Dialog
      v-model:visible="rejectDialog.visible"
      header="Trả lại báo cáo"
      modal
      style="width: 400px"
    >
      <div class="field">
        <label>Lý do trả lại <span class="ins-required">*</span></label>
        <InputText v-model="rejectDialog.review_note" class="w-full" />
      </div>
      <template #footer>
        <Button label="Hủy" text @click="rejectDialog.visible = false" />
        <Button
          v-can:edit="'insurance'"
          label="Trả lại"
          icon="pi pi-undo"
          severity="danger"
          :loading="actioning"
          @click="doReject"
        />
      </template>
    </Dialog>

    <Toast />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'

import insuranceService, {
  type InsurancePeriodReportDetail,
  type InsuranceReportLineItemRead,
  type InsuranceChangeEventRead,
  type ReportStatus,
  type SubmissionType,
} from '@/services/insuranceService'
import { usePermissionGate } from '@/composables/usePermissionGate'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const permissionGate = usePermissionGate()

const reportId = computed(() => Number(route.params.id))

// ── State ─────────────────────────────────────────────────────────────────────

const report = ref<InsurancePeriodReportDetail | null>(null)
const lineItems = ref<InsuranceReportLineItemRead[]>([])
const loading = ref(false)
const actioning = ref(false)
const exporting = ref(false)

const canEditInsurance = computed(() => permissionGate.canEdit('insurance'))
const isEditable = computed(() =>
  canEditInsurance.value && (report.value?.status === 'draft' || report.value?.status === 'rejected'),
)
const canReviewInsuranceReport = computed(() => {
  return canEditInsurance.value
})

// Adjust dialog
const adjustDialog = reactive<{
  visible: boolean
  item: InsuranceReportLineItemRead | null
  declared_year: number
  declared_month: number
  adjustment_note: string
  saving: boolean
}>({
  visible: false,
  item: null,
  declared_year: new Date().getFullYear(),
  declared_month: new Date().getMonth() + 1,
  adjustment_note: '',
  saving: false,
})

// Add item dialog
const addItemDialog = reactive<{
  visible: boolean
  availableEvents: InsuranceChangeEventRead[]
  loadingEvents: boolean
  selectedEvent: InsuranceChangeEventRead | null
  saving: boolean
}>({
  visible: false,
  availableEvents: [],
  loadingEvents: false,
  selectedEvent: null,
  saving: false,
})

// Approve dialog
const approveDialog = reactive({ visible: false, note: '' })

// Reject dialog
const rejectDialog = reactive({ visible: false, review_note: '' })

// ── Options ───────────────────────────────────────────────────────────────────

const currentYear = new Date().getFullYear()
const yearOptions = Array.from({ length: 6 }, (_, i) => {
  const y = currentYear - 2 + i
  return { label: String(y), value: y }
})
const monthOptions = Array.from({ length: 12 }, (_, i) => ({
  label: `Tháng ${i + 1}`,
  value: i + 1,
}))

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtDate(d: string | null) {
  if (!d) return '—'
  const [y, m, day] = d.split('-')
  return `${day}/${m}/${y}`
}

function formatDateTime(iso: string | null) {
  if (!iso) return ''
  // BE lưu naive UTC (không có Z suffix) — thêm Z để browser parse đúng là UTC rồi convert sang giờ local
  const utc = iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z'
  const d = new Date(utc)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

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

function lineItemRowClass(data: InsuranceReportLineItemRead) {
  const classes: string[] = []
  if (data.is_adjusted) classes.push('ins-line-adjusted')
  return classes.join(' ')
}

// ── Data loading ──────────────────────────────────────────────────────────────

async function loadReport() {
  loading.value = true
  try {
    const res = await insuranceService.getReport(reportId.value)
    report.value = res.data
    lineItems.value = res.data.line_items
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không tải được báo cáo', life: 3000 })
  } finally {
    loading.value = false
  }
}

// ── Adjust declared month ─────────────────────────────────────────────────────

function openAdjustDialog(item: InsuranceReportLineItemRead) {
  adjustDialog.item = item
  adjustDialog.declared_year = item.declared_year
  adjustDialog.declared_month = item.declared_month
  adjustDialog.adjustment_note = item.adjustment_note ?? ''
  adjustDialog.visible = true
}

async function saveAdjust() {
  if (!adjustDialog.item || !adjustDialog.adjustment_note.trim()) {
    toast.add({ severity: 'warn', summary: 'Thiếu thông tin', detail: 'Vui lòng nhập lý do điều chỉnh', life: 3000 })
    return
  }
  adjustDialog.saving = true
  try {
    const updated = await insuranceService.updateLineItem(
      reportId.value,
      adjustDialog.item.id,
      {
        declared_year: adjustDialog.declared_year,
        declared_month: adjustDialog.declared_month,
        adjustment_note: adjustDialog.adjustment_note,
      },
    )
    const idx = lineItems.value.findIndex((i: InsuranceReportLineItemRead) => i.id === adjustDialog.item!.id)
    if (idx !== -1) lineItems.value[idx] = updated.data
    adjustDialog.visible = false
    toast.add({ severity: 'success', summary: 'Đã lưu', detail: 'Tháng kê khai đã được điều chỉnh', life: 3000 })
    await loadReport()
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Không lưu được điều chỉnh'
    toast.add({ severity: 'error', summary: 'Lỗi', detail: msg, life: 4000 })
  } finally {
    adjustDialog.saving = false
  }
}

// ── Add line item ─────────────────────────────────────────────────────────────

async function openAddItemDialog() {
  addItemDialog.visible = true
  addItemDialog.selectedEvent = null
  addItemDialog.availableEvents = []
  addItemDialog.loadingEvents = true

  try {
    const currentEventIds = new Set(lineItems.value.map((i: InsuranceReportLineItemRead) => i.event_id))
    const res = await insuranceService.listChangeEvents({
      period_year: report.value?.period_year,
      period_month: report.value?.period_month,
      page_size: 200,
    })
    // Filter out events already in this report
    addItemDialog.availableEvents = res.data.items.filter((e: InsuranceChangeEventRead) => !currentEventIds.has(e.id))
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không tải được danh sách biến động', life: 3000 })
  } finally {
    addItemDialog.loadingEvents = false
  }
}

async function saveAddItem() {
  if (!addItemDialog.selectedEvent) return
  addItemDialog.saving = true
  try {
    await insuranceService.addLineItem(reportId.value, { event_id: addItemDialog.selectedEvent.id })
    addItemDialog.visible = false
    toast.add({ severity: 'success', summary: 'Đã thêm', detail: 'Biến động đã được thêm vào báo cáo', life: 3000 })
    await loadReport()
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Không thêm được dòng'
    toast.add({ severity: 'error', summary: 'Lỗi', detail: msg, life: 4000 })
  } finally {
    addItemDialog.saving = false
  }
}

// ── Remove line item ──────────────────────────────────────────────────────────

async function removeItem(item: InsuranceReportLineItemRead) {
  if (!confirm(`Xóa dòng "${item.employee_name}" khỏi báo cáo?`)) return
  try {
    await insuranceService.removeLineItem(reportId.value, item.id)
    lineItems.value = lineItems.value.filter((i: InsuranceReportLineItemRead) => i.id !== item.id)
    toast.add({ severity: 'success', summary: 'Đã xóa', detail: 'Dòng đã được xóa khỏi báo cáo', life: 3000 })
    await loadReport()
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Không xóa được dòng'
    toast.add({ severity: 'error', summary: 'Lỗi', detail: msg, life: 4000 })
  }
}

// ── Submit / Approve / Reject ─────────────────────────────────────────────────

async function submitReport() {
  if (!confirm('Nộp báo cáo lên duyệt? Sau khi nộp không thể sửa đổi dòng biến động.')) return
  actioning.value = true
  try {
    const res = await insuranceService.submitReport(reportId.value)
    report.value = { ...report.value!, ...res.data }
    toast.add({ severity: 'success', summary: 'Đã nộp', detail: 'Báo cáo đã được nộp lên duyệt', life: 3000 })
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Không nộp được báo cáo'
    toast.add({ severity: 'error', summary: 'Lỗi', detail: msg, life: 4000 })
  } finally {
    actioning.value = false
  }
}

function openApproveDialog() {
  approveDialog.note = ''
  approveDialog.visible = true
}

async function doApprove() {
  actioning.value = true
  try {
    const res = await insuranceService.approveReport(reportId.value, { note: approveDialog.note || null })
    report.value = { ...report.value!, ...res.data }
    approveDialog.visible = false
    toast.add({ severity: 'success', summary: 'Đã duyệt', detail: 'Báo cáo đã được phê duyệt', life: 3000 })
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Không duyệt được báo cáo'
    toast.add({ severity: 'error', summary: 'Lỗi', detail: msg, life: 4000 })
  } finally {
    actioning.value = false
    approveDialog.visible = false
  }
}

function openRejectDialog() {
  rejectDialog.review_note = ''
  rejectDialog.visible = true
}

async function doReject() {
  if (!rejectDialog.review_note.trim()) {
    toast.add({ severity: 'warn', summary: 'Thiếu thông tin', detail: 'Vui lòng nhập lý do trả lại', life: 3000 })
    return
  }
  actioning.value = true
  try {
    const res = await insuranceService.rejectReport(reportId.value, { review_note: rejectDialog.review_note })
    report.value = { ...report.value!, ...res.data }
    rejectDialog.visible = false
    toast.add({ severity: 'warn', summary: 'Đã trả lại', detail: 'Báo cáo đã được trả lại cho người lập', life: 3000 })
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Không trả lại được báo cáo'
    toast.add({ severity: 'error', summary: 'Lỗi', detail: msg, life: 4000 })
  } finally {
    actioning.value = false
    rejectDialog.visible = false
  }
}

// ── Export ────────────────────────────────────────────────────────────────────

async function exportReport() {
  exporting.value = true
  try {
    const res = await insuranceService.exportReportD02Ts(reportId.value)
    const url = URL.createObjectURL(new Blob([res.data]))
    const a = document.createElement('a')
    a.href = url
    a.download = `D02-TS_BaoCao${reportId.value}_T${String(report.value!.period_month).padStart(2, '0')}_${report.value!.period_year}_VNPT.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi xuất file', detail: 'Không thể xuất D02-TS', life: 3000 })
  } finally {
    exporting.value = false
  }
}

onMounted(loadReport)
</script>
