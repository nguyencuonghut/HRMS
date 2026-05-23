<template>
  <Dialog
    v-model:visible="visible"
    header="Điều chỉnh mức lương BHXH"
    modal
    :style="{ width: '520px' }"
    @hide="onHide"
  >
    <!-- Employee info bar -->
    <div v-if="employee" class="salary-adj-info-bar">
      <span class="salary-adj-info-name">
        <strong>{{ employee.employee_code }}</strong> — {{ employee.full_name }}
      </span>
      <span v-if="employee.department_name" class="salary-adj-info-dept">
        <i class="pi pi-building" /> {{ employee.department_name }}
      </span>
    </div>

    <!-- Current amount summary -->
    <div class="salary-adj-current">
      <span class="salary-adj-current-label">Mức hiện tại:</span>
      <span class="salary-basis-amount">{{ fmtMoney(employee?.insurance_basis_amount) }}</span>
      <span class="salary-adj-current-source">({{ sourceLabel(employee?.insurance_basis_source) }})</span>
    </div>

    <!-- Form -->
    <div class="salary-adj-form">
      <!-- Row 1: Mức mới + Ngày hiệu lực -->
      <div class="salary-adj-row">
        <div class="salary-adj-field">
          <label class="salary-adj-label">Mức lương BHXH mới <span class="salary-adj-required">*</span></label>
          <InputNumber
            v-model="form.newAmount"
            :min="1"
            :max="999999999"
            :use-grouping="true"
            suffix=" đ"
            locale="vi-VN"
            fluid
            :class="{ 'p-invalid': errors.newAmount }"
            @update:model-value="onAmountChange"
          />
          <small v-if="errors.newAmount" class="salary-adj-error">{{ errors.newAmount }}</small>
        </div>
        <div class="salary-adj-field">
          <label class="salary-adj-label">Ngày hiệu lực <span class="salary-adj-required">*</span></label>
          <DatePicker
            v-model="form.effectiveDate"
            date-format="dd/mm/yy"
            :show-icon="true"
            fluid
            :class="{ 'p-invalid': errors.effectiveDate }"
          />
          <small v-if="errors.effectiveDate" class="salary-adj-error">{{ errors.effectiveDate }}</small>
        </div>
      </div>

      <!-- Delta badge -->
      <div v-if="delta !== null" class="salary-adj-delta-row">
        <span :class="delta >= 0 ? 'salary-adj-delta-up' : 'salary-adj-delta-down'">
          <i :class="delta >= 0 ? 'pi pi-arrow-up' : 'pi pi-arrow-down'" />
          {{ delta >= 0 ? '+' : '' }}{{ fmtMoney(String(Math.abs(delta))) }}
          ({{ delta >= 0 ? '+' : '' }}{{ deltaPct.toFixed(1) }}%)
        </span>
      </div>

      <!-- Số quyết định -->
      <div class="salary-adj-field">
        <label class="salary-adj-label">Số quyết định <span class="salary-adj-optional">(tùy chọn)</span></label>
        <InputText v-model="form.decisionNumber" placeholder="VD: QĐ-045/2026" fluid />
      </div>

      <!-- Lý do -->
      <div class="salary-adj-field">
        <label class="salary-adj-label">Lý do điều chỉnh <span class="salary-adj-required">*</span></label>
        <Textarea
          v-model="form.reason"
          rows="3"
          placeholder="Nhập lý do điều chỉnh (tối thiểu 5 ký tự)"
          fluid
          :class="{ 'p-invalid': errors.reason }"
        />
        <small v-if="errors.reason" class="salary-adj-error">{{ errors.reason }}</small>
      </div>

      <!-- Warning -->
      <div class="salary-adj-warning">
        <i class="pi pi-exclamation-triangle" />
        <span>
          Hành động này sẽ cập nhật mức lương BHXH và tạo biến động BHXH tương ứng.
          Không thể hoàn tác — chỉ tạo điều chỉnh mới để đảo ngược.
        </span>
      </div>

      <!-- API error -->
      <div v-if="apiError" class="salary-adj-api-error">
        <i class="pi pi-times-circle" /> {{ apiError }}
      </div>
    </div>

    <template #footer>
      <Button label="Hủy" text @click="visible = false" :disabled="submitting" />
      <Button
        label="Xác nhận điều chỉnh"
        icon="pi pi-check"
        :loading="submitting"
        @click="submit"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'

import salaryService, { type SalaryEmployeeRow } from '@/services/salaryService'

const props = defineProps<{
  modelValue: boolean
  employee: SalaryEmployeeRow | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'hide'): void
  (e: 'saved'): void
}>()

// ── Visibility ────────────────────────────────────────────────────────────────

const visible = ref(props.modelValue)
watch(() => props.modelValue, (v) => { visible.value = v })
watch(visible, (v) => emit('update:modelValue', v))

// ── Form state ────────────────────────────────────────────────────────────────

const form = ref({
  newAmount: null as number | null,
  effectiveDate: new Date() as Date | null,
  decisionNumber: '',
  reason: '',
})

const errors = ref({ newAmount: '', effectiveDate: '', reason: '' })
const submitting = ref(false)
const apiError = ref('')

function resetForm() {
  form.value = { newAmount: null, effectiveDate: new Date(), decisionNumber: '', reason: '' }
  errors.value = { newAmount: '', effectiveDate: '', reason: '' }
  apiError.value = ''
}

watch(() => props.employee, () => resetForm())

// ── Delta calculation ─────────────────────────────────────────────────────────

const currentAmount = computed(() => {
  const v = props.employee?.insurance_basis_amount
  return v ? Number(v) : null
})

const delta = computed(() => {
  if (form.value.newAmount === null || currentAmount.value === null) return null
  return form.value.newAmount - currentAmount.value
})

const deltaPct = computed(() => {
  if (delta.value === null || currentAmount.value === null || currentAmount.value === 0) return 0
  return (delta.value / currentAmount.value) * 100
})

function onAmountChange() {
  errors.value.newAmount = ''
  apiError.value = ''
}

// ── Validation ────────────────────────────────────────────────────────────────

function validate(): boolean {
  let ok = true
  errors.value = { newAmount: '', effectiveDate: '', reason: '' }

  if (!form.value.newAmount || form.value.newAmount <= 0) {
    errors.value.newAmount = 'Mức lương phải lớn hơn 0'
    ok = false
  } else if (currentAmount.value !== null && form.value.newAmount === currentAmount.value) {
    errors.value.newAmount = 'Mức lương mới phải khác mức hiện tại'
    ok = false
  }

  if (!form.value.effectiveDate) {
    errors.value.effectiveDate = 'Vui lòng chọn ngày hiệu lực'
    ok = false
  }

  if (!form.value.reason || form.value.reason.trim().length < 5) {
    errors.value.reason = 'Lý do phải có ít nhất 5 ký tự'
    ok = false
  }

  return ok
}

// ── Submit ────────────────────────────────────────────────────────────────────

async function submit() {
  if (!validate() || !props.employee) return
  submitting.value = true
  apiError.value = ''
  try {
    const d = form.value.effectiveDate!
    const effectiveDateStr = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    await salaryService.createAdjustment({
      employee_id: props.employee.employee_id,
      new_basis_amount: form.value.newAmount!,
      effective_date: effectiveDateStr,
      reason: form.value.reason.trim(),
      decision_number: form.value.decisionNumber.trim() || null,
    })
    visible.value = false
    emit('saved')
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    apiError.value = typeof msg === 'string' ? msg : 'Có lỗi xảy ra, vui lòng thử lại'
  } finally {
    submitting.value = false
  }
}

function onHide() {
  emit('hide')
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtMoney(val: string | number | null | undefined) {
  if (val === null || val === undefined || val === '') return '—'
  return Number(val).toLocaleString('vi-VN') + ' đ'
}

function sourceLabel(src: string | null | undefined) {
  if (src === 'contract') return 'Hợp đồng'
  if (src === 'manual_fixed') return 'Thủ công'
  if (src === 'computed') return 'Tính tự động'
  return '—'
}
</script>
