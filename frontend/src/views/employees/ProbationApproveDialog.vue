<template>
  <Dialog
    :visible="true"
    header="Phê duyệt phiếu đánh giá thử việc"
    :style="{ width: '520px' }"
    modal
    :closable="!submitting"
    @update:visible="(v) => { if (!v) emit('close') }"
  >
    <!-- Loading -->
    <div v-if="loading" class="ob-loading">
      <i class="pi pi-spin pi-spinner" />
    </div>

    <template v-else>
      <!-- Điểm tóm tắt -->
      <div v-if="evaluation" class="probation-score-summary ob-card">
        <div class="probation-score-title">Tóm tắt điểm đánh giá</div>
        <div class="probation-score-grid">
          <div class="probation-score-item">
            <span class="probation-score-label">Thái độ</span>
            <span class="probation-score-value">{{ evaluation.attitude_score ?? '—' }}</span>
          </div>
          <div class="probation-score-item">
            <span class="probation-score-label">Năng lực</span>
            <span class="probation-score-value">{{ evaluation.competence_score ?? '—' }}</span>
          </div>
          <div class="probation-score-item">
            <span class="probation-score-label">Văn hóa</span>
            <span class="probation-score-value">{{ evaluation.culture_score ?? '—' }}</span>
          </div>
          <div class="probation-score-item">
            <span class="probation-score-label">KPI</span>
            <span class="probation-score-value">{{ evaluation.kpi_score ?? '—' }}</span>
          </div>
          <div class="probation-score-item probation-score-overall">
            <span class="probation-score-label">Tổng điểm</span>
            <span class="probation-score-value probation-score-overall-val">{{ evaluation.overall_score ?? '—' }}</span>
          </div>
        </div>
        <div v-if="evaluation.manager_comment" class="probation-comment-row">
          <span class="probation-score-label">Nhận xét quản lý:</span>
          <span class="probation-comment-text">{{ evaluation.manager_comment }}</span>
        </div>
      </div>

      <!-- Legal violations warning -->
      <div v-if="legalCheck && legalCheck.violations.length > 0" class="probation-legal-block">
        <Message
          v-for="(v, i) in legalCheck.violations"
          :key="i"
          severity="error"
          :closable="false"
        >{{ v }}</Message>
      </div>
      <div v-if="legalCheck && legalCheck.warnings.length > 0" class="probation-legal-block">
        <Message
          v-for="(w, i) in legalCheck.warnings"
          :key="i"
          severity="warn"
          :closable="false"
        >{{ w }}</Message>
      </div>

      <!-- Form phê duyệt -->
      <div class="ob-form">
        <div class="ob-form-field">
          <label class="ob-form-label">Kết quả thử việc <span class="ob-required">*</span></label>
          <div class="probation-radio-group">
            <div
              v-for="opt in resultOptions"
              :key="opt.value"
              class="probation-radio-item"
            >
              <RadioButton
                v-model="form.result"
                :value="opt.value"
                :inputId="`approve-result-${opt.value}`"
              />
              <label :for="`approve-result-${opt.value}`">{{ opt.label }}</label>
            </div>
          </div>
        </div>

        <div v-if="form.result === 'extended'" class="ob-form-field">
          <label class="ob-form-label">Số ngày gia hạn <span class="ob-required">*</span></label>
          <InputNumber
            v-model="form.extension_days"
            :min="1"
            :max="180"
            class="w-full"
            :invalid="!!errors.extension_days"
          />
          <small v-if="errors.extension_days" class="ob-error">{{ errors.extension_days }}</small>
        </div>

        <div class="ob-form-field">
          <label class="ob-form-label">Nhận xét HR</label>
          <Textarea
            v-model="form.hr_comment"
            rows="3"
            class="w-full"
            placeholder="Nhập nhận xét từ HR (tuỳ chọn)"
          />
        </div>
      </div>
    </template>

    <template #footer>
      <Button
        label="Hủy"
        severity="secondary"
        outlined
        :disabled="submitting"
        @click="emit('close')"
      />
      <Button
        label="Xác nhận phê duyệt"
        icon="pi pi-check"
        :loading="submitting"
        :disabled="loading"
        @click="doApprove"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
import RadioButton from 'primevue/radiobutton'
import Textarea from 'primevue/textarea'
import probationService, {
  type ProbationEvaluationRead,
  type ProbationLegalCheck,
} from '@/services/probationService'

const props = defineProps<{
  evalId: number
  employeeId: number
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'approved'): void
}>()

const toast = useToast()
const loading = ref(false)
const submitting = ref(false)
const evaluation = ref<ProbationEvaluationRead | null>(null)
const legalCheck = ref<ProbationLegalCheck | null>(null)
const errors = ref<Record<string, string>>({})

const form = ref({
  result: 'passed' as string,
  extension_days: null as number | null,
  hr_comment: '' as string,
})

const resultOptions = [
  { value: 'passed', label: 'Đạt' },
  { value: 'failed', label: 'Không đạt' },
  { value: 'extended', label: 'Gia hạn' },
]

function apiError(e: unknown): string {
  const err = e as { response?: { data?: { detail?: unknown } } }
  const detail = err.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((d: { msg: string }) => d.msg).join('; ')
  return typeof detail === 'string' ? detail : 'Đã xảy ra lỗi'
}

async function loadData() {
  loading.value = true
  try {
    const [detailRes, legalRes] = await Promise.all([
      probationService.getDetail(props.employeeId),
      probationService.getLegalCheck(props.employeeId),
    ])
    evaluation.value = detailRes.data.evaluation
    legalCheck.value = legalRes.data
    // Pre-fill result from existing evaluation
    if (evaluation.value?.result && evaluation.value.result !== 'pending') {
      form.value.result = evaluation.value.result
    }
    if (evaluation.value?.extension_days) {
      form.value.extension_days = evaluation.value.extension_days
    }
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể tải thông tin', life: 4000 })
  } finally {
    loading.value = false
  }
}

function validate(): boolean {
  errors.value = {}
  if (!form.value.result) {
    errors.value.result = 'Vui lòng chọn kết quả'
    return false
  }
  if (form.value.result === 'extended' && !form.value.extension_days) {
    errors.value.extension_days = 'Nhập số ngày gia hạn'
    return false
  }
  return true
}

async function doApprove() {
  if (!validate()) return
  submitting.value = true
  try {
    await probationService.approveEvaluation(props.employeeId, {
      result: form.value.result,
      hr_comment: form.value.hr_comment || null,
      extension_days: form.value.result === 'extended' ? form.value.extension_days : null,
    })
    toast.add({ severity: 'success', summary: 'Đã phê duyệt', detail: 'Phiếu đánh giá đã được phê duyệt', life: 3000 })
    emit('approved')
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
  } finally {
    submitting.value = false
  }
}

onMounted(loadData)
</script>
