<template>
  <Dialog
    v-model:visible="visible"
    header="Quyết định tuyển dụng"
    modal
    :style="{ width: '640px' }"
    @hide="resetForm"
  >
    <!-- Form tạo/sửa quyết định -->
    <div v-if="!decision || decision.status === 'pending'" class="rc-form">
      <div class="rc-row">
        <div class="rc-field">
          <label class="rc-label">Số quyết định</label>
          <InputText v-model="form.decision_number" class="w-full" placeholder="QĐ-2026-001" />
        </div>
        <div class="rc-field">
          <label class="rc-label">Ngày ký <span class="req">*</span></label>
          <DatePicker v-model="form.signed_date" date-format="dd/mm/yy" class="w-full" />
        </div>
      </div>

      <div class="rc-row">
        <div class="rc-field">
          <label class="rc-label">Phòng ban <span class="req">*</span></label>
          <Select
            v-model="form.department_id"
            :options="departmentOptions"
            option-label="label"
            option-value="value"
            filter
            class="w-full"
            placeholder="Chọn phòng ban..."
          />
        </div>
        <div class="rc-field">
          <label class="rc-label">Vị trí <span class="req">*</span></label>
          <Select
            v-model="form.job_position_id"
            :options="jobPositionOptions"
            option-label="label"
            option-value="value"
            filter
            class="w-full"
            placeholder="Chọn vị trí..."
          />
        </div>
      </div>

      <div class="rc-field">
        <label class="rc-label">Ngày bắt đầu làm việc <span class="req">*</span></label>
        <DatePicker v-model="form.start_date" date-format="dd/mm/yy" class="w-full" />
      </div>

      <div class="rc-row">
        <div class="rc-field">
          <label class="rc-label">Lương chính thức (VNĐ) <span class="req">*</span></label>
          <InputNumber v-model="form.official_salary" :use-grouping="true" :min="0" class="w-full" />
        </div>
        <div class="rc-field">
          <label class="rc-label">Lương thử việc (VNĐ) <span class="req">*</span></label>
          <InputNumber v-model="form.probation_salary" :use-grouping="true" :min="0" class="w-full" />
        </div>
      </div>

      <div class="rc-field">
        <label class="rc-label">Số ngày thử việc <span class="req">*</span></label>
        <InputNumber v-model="form.probation_days" :use-grouping="false" :min="1" :max="180" class="w-full" />
      </div>
    </div>

    <!-- Hiển thị quyết định đã converted -->
    <div v-else class="rc-info-block">
      <div class="rc-info-row">
        <span class="rc-info-label">Số quyết định</span>
        <span>{{ decision.decision_number ?? '—' }}</span>
      </div>
      <div class="rc-info-row">
        <span class="rc-info-label">Ngày ký</span>
        <span>{{ decision.signed_date }}</span>
      </div>
      <div class="rc-info-row">
        <span class="rc-info-label">Ngày bắt đầu</span>
        <span>{{ decision.start_date }}</span>
      </div>
      <div class="rc-info-row">
        <span class="rc-info-label">Mã nhân viên</span>
        <span>{{ convertResult?.employee_code ?? '—' }}</span>
      </div>
      <div class="rc-info-row">
        <span class="rc-info-label">Trạng thái</span>
        <Tag :value="decision.status_label" severity="success" />
      </div>
    </div>

    <!-- Missing fields warning (shown when decision is pending and candidate has missing required fields) -->
    <div
      v-if="decision?.status === 'pending' && decision.candidate_missing_fields?.length"
      class="rc-missing-fields-warn"
    >
      <i class="pi pi-exclamation-triangle" />
      Hồ sơ ứng viên thiếu thông tin bắt buộc — cần bổ sung trước khi tạo nhân viên:
      <ul class="rc-missing-list">
        <li v-for="f in decision.candidate_missing_fields" :key="f">{{ f }}</li>
      </ul>
    </div>

    <template #footer>
      <Button label="Đóng" severity="secondary" outlined @click="visible = false" />
      <Button
        v-if="decision?.status === 'pending'"
        label="Cập nhật"
        icon="pi pi-save"
        severity="secondary"
        :loading="saving"
        @click="update"
      />
      <Button
        v-if="decision?.status === 'pending'"
        label="Tạo nhân viên"
        icon="pi pi-user-plus"
        severity="success"
        :loading="converting"
        :disabled="!!decision.candidate_missing_fields?.length"
        @click="convert"
      />
      <Button
        v-else-if="!decision"
        label="Lưu quyết định"
        icon="pi pi-check"
        :loading="saving"
        @click="save"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import Button from 'primevue/button'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'

import { hiringDecisionService, type HiringDecisionRead, type ConvertToEmployeeResult } from '@/services/recruitmentService'
import departmentService from '@/services/departmentService'
import jobPositionService from '@/services/jobPositionService'

const props = defineProps<{
  offerId: number
  decision?: HiringDecisionRead | null
  /** Pre-fill from offer */
  defaultDeptId?: number | null
  defaultPosId?: number | null
  defaultStartDate?: string | null
  defaultOfficialSalary?: string | null
  defaultProbationSalary?: string | null
  defaultProbationDays?: number | null
}>()

const emit = defineEmits<{
  (e: 'saved', decision: HiringDecisionRead): void
  (e: 'converted', result: ConvertToEmployeeResult, decision: HiringDecisionRead): void
}>()

const visible = defineModel<boolean>('visible', { default: false })
const toast = useToast()

function extractErrorDetail(err: unknown, fallback = 'Có lỗi xảy ra'): string {
  const data = (err as any)?.response?.data
  if (!data) return fallback
  // Plain string response (e.g. nginx/proxy 500)
  if (typeof data === 'string') return data.length < 200 ? data : fallback
  const detail = data.detail
  if (!detail) return fallback
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((d: any) => d?.msg ?? JSON.stringify(d)).join('; ')
  }
  return fallback
}
const saving = ref(false)
const converting = ref(false)
const convertResult = ref<ConvertToEmployeeResult | null>(null)

const departmentOptions = ref<{ label: string; value: number }[]>([])
const jobPositionOptions = ref<{ label: string; value: number }[]>([])

const form = ref({
  decision_number: '',
  signed_date: null as Date | null,
  department_id: null as number | null,
  job_position_id: null as number | null,
  start_date: null as Date | null,
  official_salary: null as number | null,
  probation_salary: null as number | null,
  probation_days: 30 as number | null,
})

function toDateStr(d: Date | null): string | null {
  if (!d) return null
  return d.toISOString().slice(0, 10)
}

function resetForm() {
  const d = props.decision
  form.value = {
    decision_number: d?.decision_number ?? '',
    signed_date: d?.signed_date ? new Date(d.signed_date) : new Date(),
    department_id: d?.department_id ?? props.defaultDeptId ?? null,
    job_position_id: d?.job_position_id ?? props.defaultPosId ?? null,
    start_date: d?.start_date ? new Date(d.start_date) : (props.defaultStartDate ? new Date(props.defaultStartDate) : null),
    official_salary: d ? parseFloat(d.official_salary) : (props.defaultOfficialSalary ? parseFloat(props.defaultOfficialSalary) : null),
    probation_salary: d ? parseFloat(d.probation_salary) : (props.defaultProbationSalary ? parseFloat(props.defaultProbationSalary) : null),
    probation_days: d?.probation_days ?? props.defaultProbationDays ?? 30,
  }
}

async function save() {
  if (!form.value.department_id || !form.value.job_position_id || !form.value.start_date || !form.value.official_salary || !form.value.probation_salary || !form.value.probation_days) {
    toast.add({ severity: 'warn', summary: 'Thiếu thông tin', detail: 'Vui lòng điền đầy đủ các trường bắt buộc.', life: 3000 })
    return
  }
  saving.value = true
  try {
    const payload = {
      decision_number: form.value.decision_number || null,
      signed_date: toDateStr(form.value.signed_date)!,
      department_id: form.value.department_id!,
      job_position_id: form.value.job_position_id!,
      start_date: toDateStr(form.value.start_date)!,
      official_salary: form.value.official_salary!,
      probation_salary: form.value.probation_salary!,
      probation_days: form.value.probation_days!,
    }
    const result = await hiringDecisionService.create(props.offerId, payload)
    toast.add({ severity: 'success', summary: 'Đã tạo quyết định tuyển dụng', life: 2000 })
    emit('saved', result)
    visible.value = false
  } catch (err: unknown) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: extractErrorDetail(err), life: 5000 })
  } finally {
    saving.value = false
  }
}

async function update() {
  if (!props.decision) return
  if (!form.value.department_id || !form.value.job_position_id || !form.value.start_date || !form.value.official_salary || !form.value.probation_salary || !form.value.probation_days) {
    toast.add({ severity: 'warn', summary: 'Thiếu thông tin', detail: 'Vui lòng điền đầy đủ các trường bắt buộc.', life: 3000 })
    return
  }
  saving.value = true
  try {
    const payload = {
      decision_number: form.value.decision_number || null,
      signed_date: toDateStr(form.value.signed_date)!,
      department_id: form.value.department_id!,
      job_position_id: form.value.job_position_id!,
      start_date: toDateStr(form.value.start_date)!,
      official_salary: form.value.official_salary!,
      probation_salary: form.value.probation_salary!,
      probation_days: form.value.probation_days!,
    }
    const result = await hiringDecisionService.update(props.decision.id, payload)
    toast.add({ severity: 'success', summary: 'Đã cập nhật quyết định', life: 2000 })
    emit('saved', result)
  } catch (err: unknown) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: extractErrorDetail(err), life: 5000 })
  } finally {
    saving.value = false
  }
}

async function convert() {
  if (!props.decision) return
  converting.value = true
  try {
    const result = await hiringDecisionService.convert(props.decision.id)
    convertResult.value = result
    const updated = await hiringDecisionService.get(props.decision.id)
    toast.add({ severity: 'success', summary: 'Đã tạo nhân viên', detail: result.message, life: 4000 })
    emit('converted', result, updated)
    visible.value = false
  } catch (err: unknown) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: extractErrorDetail(err), life: 5000 })
  } finally {
    converting.value = false
  }
}

watch(visible, (v: boolean) => { if (v) resetForm() })

onMounted(async () => {
  const [deptsRes, positionsRes] = await Promise.all([
    departmentService.getList(true),
    jobPositionService.getList({ is_active: true }),
  ])
  departmentOptions.value = deptsRes.data.map((d: any) => ({ label: d.name, value: d.id }))
  jobPositionOptions.value = positionsRes.data.map((p: any) => ({ label: p.name, value: p.id }))
})
</script>
