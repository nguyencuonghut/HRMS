<template>
  <div class="probation-tab">
    <!-- Loading -->
    <div v-if="loading" class="ob-loading">
      <i class="pi pi-spin pi-spinner" />
    </div>

    <!-- Error -->
    <div v-else-if="loadError" class="ob-empty">
      <i class="pi pi-exclamation-circle" />
      <span>{{ loadError }}</span>
    </div>

    <template v-else-if="detail">
      <!-- ── Section 1: Thông tin thử việc ─────────────────────────────────── -->
      <div class="ob-card">
        <div class="probation-section-title">Thông tin thử việc</div>

        <Message
          v-if="detail.probation_mode === 'historical'"
          class="probation-mode-message"
          severity="info"
          :closable="false"
        >
          Đây là dữ liệu thử việc lịch sử của nhân viên đã không còn ở trạng thái thử việc.
          Bạn vẫn có thể nhập và phê duyệt phiếu đánh giá để hoàn thiện hồ sơ, nhưng hệ thống sẽ không tự đổi trạng thái nhân sự hoặc sinh hợp đồng thử việc.
        </Message>

        <Message
          v-else-if="detail.probation_mode === 'none'"
          class="probation-mode-message"
          severity="secondary"
          :closable="false"
        >
          Nhân viên chưa có dữ liệu thử việc trên bản ghi công việc hiện tại.
        </Message>

        <div class="probation-info-grid">
          <div class="probation-info-item">
            <span class="probation-info-label">Ngày bắt đầu</span>
            <span class="probation-info-value">{{ formatDate(detail.probation_start_date) }}</span>
          </div>
          <div class="probation-info-item">
            <span class="probation-info-label">Ngày kết thúc</span>
            <span class="probation-info-value">{{ formatDate(detail.probation_end_date) }}</span>
          </div>
          <div class="probation-info-item">
            <span class="probation-info-label">Ngày chính thức</span>
            <span class="probation-info-value">{{ formatDate(detail.official_date) }}</span>
          </div>
          <div class="probation-info-item">
            <span class="probation-info-label">Còn lại</span>
            <Tag
              v-if="probationRemainingTag"
              :value="probationRemainingTag.value"
              :severity="probationRemainingTag.severity"
            />
            <span v-else class="ob-muted">—</span>
          </div>
        </div>

        <!-- Legal check violations -->
        <div v-if="detail.legal_check.violations.length > 0" class="probation-legal-block">
          <Message
            v-for="(v, i) in detail.legal_check.violations"
            :key="`vio-${i}`"
            severity="error"
            :closable="false"
          >{{ v }}</Message>
        </div>

        <!-- Legal check warnings -->
        <div v-if="detail.legal_check.warnings.length > 0" class="probation-legal-block">
          <Message
            v-for="(w, i) in detail.legal_check.warnings"
            :key="`warn-${i}`"
            severity="warn"
            :closable="false"
          >{{ w }}</Message>
        </div>

        <!-- Contract button -->
        <div v-if="detail.can_generate_contract" class="probation-contract-row">
          <Button
            v-can:edit="'employees'"
            v-if="detail.contracts.length === 0"
            label="Tạo hợp đồng thử việc"
            icon="pi pi-file-plus"
            severity="secondary"
            :loading="generatingContract"
            @click="generateContract"
          />
          <Tag v-else value="Đã có hợp đồng thử việc" severity="success" icon="pi pi-check" />
        </div>
      </div>

      <!-- ── Section 2: Phiếu đánh giá ─────────────────────────────────────── -->
      <div class="ob-card">
        <div class="probation-section-title">Phiếu đánh giá thử việc</div>

        <!-- Approved summary -->
        <template v-if="detail.evaluation && detail.evaluation.status === 'approved'">
          <div class="probation-approved-card">
            <div class="probation-approved-header">
              <Tag
                :value="resultLabel(detail.evaluation.result)"
                :severity="resultSeverity(detail.evaluation.result)"
              />
              <span class="probation-approved-meta">
                Phê duyệt bởi <strong>{{ detail.evaluation.approved_by_name }}</strong>
                lúc {{ formatDatetime(detail.evaluation.approved_at) }}
              </span>
            </div>
            <div class="probation-score-grid">
              <div class="probation-score-item">
                <span class="probation-score-label">Thái độ</span>
                <span class="probation-score-value">{{ detail.evaluation.attitude_score ?? '—' }}</span>
              </div>
              <div class="probation-score-item">
                <span class="probation-score-label">Năng lực</span>
                <span class="probation-score-value">{{ detail.evaluation.competence_score ?? '—' }}</span>
              </div>
              <div class="probation-score-item">
                <span class="probation-score-label">Văn hóa</span>
                <span class="probation-score-value">{{ detail.evaluation.culture_score ?? '—' }}</span>
              </div>
              <div class="probation-score-item">
                <span class="probation-score-label">KPI</span>
                <span class="probation-score-value">{{ detail.evaluation.kpi_score ?? '—' }}</span>
              </div>
              <div class="probation-score-item probation-score-overall">
                <span class="probation-score-label">Tổng điểm</span>
                <span class="probation-score-value probation-score-overall-val">{{ detail.evaluation.overall_score ?? '—' }}</span>
              </div>
            </div>
            <div v-if="detail.evaluation.hr_comment" class="probation-comment-row">
              <span class="probation-score-label">Nhận xét HR:</span>
              <span class="probation-comment-text">{{ detail.evaluation.hr_comment }}</span>
            </div>
            <div v-if="detail.evaluation.extension_days" class="probation-comment-row">
              <span class="probation-score-label">Số ngày gia hạn:</span>
              <span class="probation-comment-text">{{ detail.evaluation.extension_days }} ngày</span>
            </div>
          </div>
        </template>

        <!-- Submitted - waiting for approval -->
        <template v-else-if="detail.evaluation && detail.evaluation.status === 'submitted'">
          <Message severity="info" :closable="false">
            Phiếu đánh giá đã được nộp và đang chờ HR phê duyệt.
          </Message>
          <div class="probation-score-grid probation-score-grid-readonly">
            <div class="probation-score-item">
              <span class="probation-score-label">Thái độ</span>
              <span class="probation-score-value">{{ detail.evaluation.attitude_score ?? '—' }}</span>
            </div>
            <div class="probation-score-item">
              <span class="probation-score-label">Năng lực</span>
              <span class="probation-score-value">{{ detail.evaluation.competence_score ?? '—' }}</span>
            </div>
            <div class="probation-score-item">
              <span class="probation-score-label">Văn hóa</span>
              <span class="probation-score-value">{{ detail.evaluation.culture_score ?? '—' }}</span>
            </div>
            <div class="probation-score-item">
              <span class="probation-score-label">KPI</span>
              <span class="probation-score-value">{{ detail.evaluation.kpi_score ?? '—' }}</span>
            </div>
            <div class="probation-score-item probation-score-overall">
              <span class="probation-score-label">Tổng điểm</span>
              <span class="probation-score-value probation-score-overall-val">{{ detail.evaluation.overall_score ?? '—' }}</span>
            </div>
          </div>
          <div class="probation-action-row">
            <Button
              v-can:edit="'employees'"
              label="Rút lại để sửa"
              icon="pi pi-undo"
              severity="secondary"
              outlined
              :loading="recallingEval"
              @click="recallEval"
            />
            <Button
              v-if="canReviewProbation"
              label="Phê duyệt"
              icon="pi pi-check-circle"
              @click="openApproveDialog"
            />
          </div>
        </template>

        <!-- Draft or No evaluation — show form -->
        <template v-else-if="detail.can_edit_evaluation">
          <div class="ob-form">
            <!-- Ngày đánh giá -->
            <div class="ob-form-field">
              <label class="ob-form-label">Ngày đánh giá <span class="ob-required">*</span></label>
              <DatePicker
                v-model="evalForm.evaluation_date_obj"
                class="w-full"
                dateFormat="dd/mm/yy"
                :invalid="!!evalErrors.evaluation_date"
              />
              <small v-if="evalErrors.evaluation_date" class="ob-error">{{ evalErrors.evaluation_date }}</small>
            </div>

            <!-- Người đánh giá -->
            <div class="ob-form-field">
              <label class="ob-form-label">Người đánh giá <span class="ob-required">*</span></label>
              <Select
                v-model="evalForm.evaluator_id"
                :options="userOptions"
                option-label="label"
                option-value="value"
                filter
                placeholder="Chọn người đánh giá"
                class="w-full"
                :loading="loadingUsers"
                :invalid="!!evalErrors.evaluator_id"
              />
              <small v-if="evalErrors.evaluator_id" class="ob-error">{{ evalErrors.evaluator_id }}</small>
            </div>

            <!-- Điểm thành phần -->
            <div class="probation-score-inputs">
              <div class="ob-form-field">
                <label class="ob-form-label">Thái độ (0-10)</label>
                <InputNumber
                  v-model="evalForm.attitude_score"
                  :min="0"
                  :max="10"
                  :minFractionDigits="0"
                  :maxFractionDigits="1"
                  class="w-full"
                />
              </div>
              <div class="ob-form-field">
                <label class="ob-form-label">Năng lực (0-10)</label>
                <InputNumber
                  v-model="evalForm.competence_score"
                  :min="0"
                  :max="10"
                  :minFractionDigits="0"
                  :maxFractionDigits="1"
                  class="w-full"
                />
              </div>
              <div class="ob-form-field">
                <label class="ob-form-label">Văn hóa (0-10)</label>
                <InputNumber
                  v-model="evalForm.culture_score"
                  :min="0"
                  :max="10"
                  :minFractionDigits="0"
                  :maxFractionDigits="1"
                  class="w-full"
                />
              </div>
              <div class="ob-form-field">
                <label class="ob-form-label">KPI (0-10)</label>
                <InputNumber
                  v-model="evalForm.kpi_score"
                  :min="0"
                  :max="10"
                  :minFractionDigits="0"
                  :maxFractionDigits="1"
                  class="w-full"
                />
              </div>
            </div>

            <!-- Tổng điểm (computed, readonly) -->
            <div class="ob-form-field">
              <label class="ob-form-label">Tổng điểm (tính tự động)</label>
              <InputNumber
                :model-value="computedOverallScore"
                class="w-full"
                :disabled="true"
                placeholder="—"
              />
            </div>

            <!-- Kết quả đề xuất -->
            <div class="ob-form-field">
              <label class="ob-form-label">Kết quả đề xuất <span class="ob-required">*</span></label>
              <div class="probation-radio-group">
                <div
                  v-for="opt in allResultOptions"
                  :key="opt.value"
                  class="probation-radio-item"
                >
                  <RadioButton
                    v-model="evalForm.result"
                    :value="opt.value"
                    :inputId="`eval-result-${opt.value}`"
                  />
                  <label :for="`eval-result-${opt.value}`">{{ opt.label }}</label>
                </div>
              </div>
              <small v-if="evalErrors.result" class="ob-error">{{ evalErrors.result }}</small>
            </div>

            <!-- Số ngày gia hạn nếu extended -->
            <div v-if="evalForm.result === 'extended'" class="ob-form-field">
              <label class="ob-form-label">Số ngày gia hạn <span class="ob-required">*</span></label>
              <InputNumber
                v-model="evalForm.extension_days"
                :min="1"
                :max="180"
                class="w-full"
                :invalid="!!evalErrors.extension_days"
              />
              <small v-if="evalErrors.extension_days" class="ob-error">{{ evalErrors.extension_days }}</small>
            </div>

            <!-- Nhận xét quản lý -->
            <div class="ob-form-field">
              <label class="ob-form-label">Nhận xét của quản lý</label>
              <Textarea
                v-model="evalForm.manager_comment"
                rows="3"
                class="w-full"
                placeholder="Nhập nhận xét (tuỳ chọn)"
              />
            </div>

            <!-- Action buttons -->
            <div class="probation-action-row">
              <Button
                v-can:edit="'employees'"
                label="Lưu nháp"
                icon="pi pi-save"
                severity="secondary"
                outlined
                :loading="savingDraft"
                @click="saveDraft"
              />
              <Button
                v-can:edit="'employees'"
                v-if="detail.evaluation && detail.evaluation.status === 'draft'"
                label="Nộp lên HR"
                icon="pi pi-send"
                :loading="submittingEval"
                @click="submitToHr"
              />
            </div>
          </div>
        </template>

        <template v-else>
          <Message severity="secondary" :closable="false">
            Không thể nhập phiếu đánh giá vì nhân viên không có dữ liệu thử việc khả dụng.
          </Message>
        </template>
      </div>
    </template>

    <!-- Approve dialog -->
    <ProbationApproveDialog
      v-if="showApproveDialog && detail?.evaluation"
      :eval-id="detail.evaluation.id"
      :employee-id="props.employeeId"
      :approval-triggers-workflow="detail.approval_triggers_workflow"
      @close="showApproveDialog = false"
      @approved="onApproved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import DatePicker from 'primevue/datepicker'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
import RadioButton from 'primevue/radiobutton'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import probationService, { type ProbationDetailRead } from '@/services/probationService'
import userService from '@/services/userService'
import { useAuthStore } from '@/stores/auth'
import ProbationApproveDialog from './ProbationApproveDialog.vue'

const props = defineProps<{ employeeId: number }>()
const auth = useAuthStore()
const canReviewProbation = computed(() => {
  return auth.hasPermission("employees:edit")
})

const toast = useToast()
const loading = ref(false)
const loadError = ref('')
const detail = ref<ProbationDetailRead | null>(null)
const loadingUsers = ref(false)
const userOptions = ref<{ label: string; value: number }[]>([])
const savingDraft = ref(false)
const submittingEval = ref(false)
const recallingEval = ref(false)
const generatingContract = ref(false)
const showApproveDialog = ref(false)
const evalErrors = ref<Record<string, string>>({})

// ── Eval form ──────────────────────────────────────────────────────────────────
const evalForm = ref({
  evaluation_date_obj: null as Date | null,
  evaluator_id: null as number | null,
  attitude_score: null as number | null,
  competence_score: null as number | null,
  culture_score: null as number | null,
  kpi_score: null as number | null,
  result: 'pending' as string,
  extension_days: null as number | null,
  manager_comment: '' as string,
})

const allResultOptions = [
  { value: 'pending', label: 'Chờ quyết định' },
  { value: 'passed', label: 'Đạt' },
  { value: 'failed', label: 'Không đạt' },
  { value: 'extended', label: 'Gia hạn' },
]

// ── Computed ───────────────────────────────────────────────────────────────────
const computedOverallScore = computed(() => {
  const scores = [
    evalForm.value.attitude_score,
    evalForm.value.competence_score,
    evalForm.value.culture_score,
    evalForm.value.kpi_score,
  ].filter((s): s is number => s !== null)
  if (scores.length === 0) return null
  const avg = scores.reduce((a, b) => a + b, 0) / scores.length
  return Math.round(avg * 10) / 10
})

const probationRemainingTag = computed<{
  value: string
  severity: 'danger' | 'warn' | 'success' | 'secondary'
} | null>(() => {
  if (!detail.value) return null

  if (detail.value.probation_mode === 'historical') {
    if (detail.value.official_date) {
      return { value: 'Đã chính thức', severity: 'secondary' }
    }
    if (detail.value.probation_end_date) {
      return { value: 'Đã kết thúc', severity: 'secondary' }
    }
    return null
  }

  if (detail.value.days_remaining === null) return null
  return {
    value: `${detail.value.days_remaining} ngày`,
    severity: daysRemainingSeverity(detail.value.days_remaining),
  }
})

// ── Helpers ────────────────────────────────────────────────────────────────────
function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

function formatDatetime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function toIso(d: Date | null): string | null {
  if (!d) return null
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function daysRemainingSeverity(days: number): 'danger' | 'warn' | 'success' {
  if (days <= 7) return 'danger'
  if (days <= 15) return 'warn'
  return 'success'
}

function resultLabel(r: string): string {
  const map: Record<string, string> = {
    pending: 'Chờ quyết định',
    passed: 'Đạt',
    failed: 'Không đạt',
    extended: 'Gia hạn',
  }
  return map[r] ?? r
}

function resultSeverity(r: string): 'secondary' | 'success' | 'danger' | 'warn' {
  const map: Record<string, 'secondary' | 'success' | 'danger' | 'warn'> = {
    pending: 'secondary',
    passed: 'success',
    failed: 'danger',
    extended: 'warn',
  }
  return map[r] ?? 'secondary'
}

function apiError(e: unknown): string {
  const err = e as { response?: { data?: { detail?: unknown } } }
  const detail = err.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((d: { msg: string }) => d.msg).join('; ')
  return typeof detail === 'string' ? detail : 'Đã xảy ra lỗi'
}

// ── Fill form from existing evaluation ─────────────────────────────────────────
function fillEvalForm(ev: NonNullable<ProbationDetailRead['evaluation']>) {
  evalForm.value = {
    evaluation_date_obj: ev.evaluation_date ? new Date(ev.evaluation_date) : null,
    evaluator_id: ev.evaluator_id,
    attitude_score: ev.attitude_score,
    competence_score: ev.competence_score,
    culture_score: ev.culture_score,
    kpi_score: ev.kpi_score,
    result: ev.result,
    extension_days: ev.extension_days,
    manager_comment: ev.manager_comment ?? '',
  }
}

// ── Load ───────────────────────────────────────────────────────────────────────
async function loadDetail() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await probationService.getDetail(props.employeeId)
    detail.value = res.data
    // Fill form if draft evaluation exists
    if (res.data.evaluation && res.data.evaluation.status === 'draft') {
      fillEvalForm(res.data.evaluation)
    }
  } catch {
    loadError.value = 'Không thể tải thông tin thử việc'
  } finally {
    loading.value = false
  }
}

async function loadUsers() {
  loadingUsers.value = true
  try {
    const res = await userService.list({ is_active: true, limit: 100 })
    userOptions.value = res.data.items.map((u) => ({
      label: u.full_name || u.email,
      value: u.id,
    }))
  } catch {
    // silently fail
  } finally {
    loadingUsers.value = false
  }
}

// ── Validate eval form ─────────────────────────────────────────────────────────
function validateEval(): boolean {
  evalErrors.value = {}
  if (!evalForm.value.evaluation_date_obj) {
    evalErrors.value.evaluation_date = 'Vui lòng chọn ngày đánh giá'
  }
  if (!evalForm.value.evaluator_id) {
    evalErrors.value.evaluator_id = 'Vui lòng chọn người đánh giá'
  }
  if (!evalForm.value.result) {
    evalErrors.value.result = 'Vui lòng chọn kết quả'
  }
  if (evalForm.value.result === 'extended' && !evalForm.value.extension_days) {
    evalErrors.value.extension_days = 'Nhập số ngày gia hạn'
  }
  return Object.keys(evalErrors.value).length === 0
}

function buildEvalPayload() {
  return {
    evaluation_date: toIso(evalForm.value.evaluation_date_obj)!,
    evaluator_id: evalForm.value.evaluator_id!,
    attitude_score: evalForm.value.attitude_score,
    competence_score: evalForm.value.competence_score,
    culture_score: evalForm.value.culture_score,
    kpi_score: evalForm.value.kpi_score,
    result: evalForm.value.result,
    extension_days: evalForm.value.result === 'extended' ? evalForm.value.extension_days : null,
    manager_comment: evalForm.value.manager_comment || null,
  }
}

// ── Actions ───────────────────────────────────────────────────────────────────
async function saveDraft() {
  if (!validateEval()) return
  savingDraft.value = true
  try {
    const payload = buildEvalPayload()
    if (detail.value?.evaluation) {
      await probationService.updateEvaluation(props.employeeId, detail.value.evaluation.id, payload)
    } else {
      await probationService.createEvaluation(props.employeeId, payload)
    }
    toast.add({ severity: 'success', summary: 'Đã lưu nháp', detail: 'Phiếu đánh giá đã được lưu', life: 3000 })
    await loadDetail()
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
  } finally {
    savingDraft.value = false
  }
}

async function recallEval() {
  recallingEval.value = true
  try {
    await probationService.recallEvaluation(props.employeeId)
    toast.add({ severity: 'success', summary: 'Đã rút lại', detail: 'Phiếu đánh giá đã về trạng thái nháp, bạn có thể chỉnh sửa lại', life: 3000 })
    await loadDetail()
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
  } finally {
    recallingEval.value = false
  }
}

async function submitToHr() {
  if (!detail.value?.evaluation) {
    toast.add({ severity: 'warn', summary: 'Lưu ý', detail: 'Vui lòng lưu nháp trước khi nộp', life: 3000 })
    return
  }
  if (!validateEval()) return
  submittingEval.value = true
  try {
    await probationService.updateEvaluation(
      props.employeeId,
      detail.value.evaluation.id,
      buildEvalPayload(),
    )
    await probationService.submitEvaluation(props.employeeId)
    toast.add({ severity: 'success', summary: 'Đã nộp', detail: 'Phiếu đã được nộp lên HR', life: 3000 })
    await loadDetail()
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
  } finally {
    submittingEval.value = false
  }
}

async function generateContract() {
  generatingContract.value = true
  try {
    await probationService.generateContract(props.employeeId)
    toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã tạo hợp đồng thử việc', life: 3000 })
    await loadDetail()
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
  } finally {
    generatingContract.value = false
  }
}

function openApproveDialog() {
  showApproveDialog.value = true
}

async function onApproved() {
  showApproveDialog.value = false
  await loadDetail()
}

onMounted(async () => {
  await Promise.all([loadDetail(), loadUsers()])
})
</script>

<style scoped>
.probation-mode-message {
  margin-bottom: 1rem;
}

.probation-mode-message :deep(.p-message-content) {
  align-items: flex-start;
}

.probation-mode-message :deep(.p-message-text) {
  line-height: 1.45;
}
</style>
