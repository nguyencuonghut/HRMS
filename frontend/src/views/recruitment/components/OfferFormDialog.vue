<template>
  <Dialog
    v-model:visible="visible"
    :header="editing ? 'Chỉnh sửa Offer' : 'Tạo Offer'"
    modal
    :style="{ width: '640px' }"
    @hide="resetForm"
  >
    <div class="rc-form">
      <!-- Vị trí & phòng ban: readonly khi có JR context, editable khi sửa offer standalone -->
      <div v-if="hasJrContext && !editing" class="rc-field">
        <label class="rc-label">Vị trí / Phòng ban</label>
        <div class="rc-muted" style="padding: 0.5rem 0; font-size: 0.95rem;">
          <strong>{{ props.jrJobPositionName }}</strong> &mdash; {{ props.jrDeptName }}
        </div>
      </div>
      <div v-else class="rc-row">
        <div class="rc-field">
          <label class="rc-label">Vị trí tuyển dụng <span class="req">*</span></label>
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
      </div>

      <div class="rc-field">
        <label class="rc-label">Ngày bắt đầu dự kiến <span class="req">*</span></label>
        <DatePicker v-model="form.proposed_start_date" date-format="dd/mm/yy" class="w-full" />
      </div>

      <div class="rc-row">
        <div class="rc-field">
          <label class="rc-label">Lương chính thức (VNĐ) <span class="req">*</span></label>
          <InputNumber
            v-model="form.official_salary"
            :use-grouping="true"
            :min="0"
            class="w-full"
            placeholder="10,000,000"
          />
        </div>
        <div class="rc-field">
          <label class="rc-label">Lương thử việc (VNĐ) <span class="req">*</span></label>
          <InputNumber
            v-model="form.probation_salary"
            :use-grouping="true"
            :min="0"
            class="w-full"
            placeholder="8,500,000"
          />
          <small v-if="probationSalaryWarning" class="rc-error">
            <i class="pi pi-exclamation-triangle" />
            Thấp hơn 85% lương chính thức (vi phạm Điều 24 BLLĐ 2019)
          </small>
        </div>
      </div>

      <div class="rc-row">
        <div class="rc-field">
          <label class="rc-label">Số ngày thử việc <span class="req">*</span></label>
          <InputNumber
            v-model="form.probation_days"
            :use-grouping="false"
            :min="1"
            :max="180"
            class="w-full"
            placeholder="60"
          />
          <small v-if="probationDaysWarning" class="rc-error">
            <i class="pi pi-exclamation-triangle" />
            Vượt giới hạn thử việc quy định (tối đa {{ probationDaysLimit }} ngày)
          </small>
        </div>
        <div class="rc-field">
          <label class="rc-label">Hạn phản hồi</label>
          <DatePicker v-model="form.expires_at" date-format="dd/mm/yy" class="w-full" />
        </div>
      </div>

      <div class="rc-field">
        <label class="rc-label">Phúc lợi / ghi chú</label>
        <Textarea v-model="form.benefits_note" rows="2" class="w-full" auto-resize placeholder="BHXH, BHYT, thưởng lễ..." />
      </div>

      <div class="rc-field">
        <label class="rc-label">Ghi chú nội bộ</label>
        <Textarea v-model="form.internal_note" rows="2" class="w-full" auto-resize placeholder="Lưu ý nội bộ..." />
      </div>
    </div>

    <template #footer>
      <Button label="Hủy" severity="secondary" outlined @click="visible = false" />
      <Button label="Lưu" icon="pi pi-check" :loading="saving" @click="save" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted } from 'vue'
import Button from 'primevue/button'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import { useToast } from 'primevue/usetoast'

import { offerService, type OfferRead } from '@/services/recruitmentService'
import departmentService from '@/services/departmentService'
import jobPositionService from '@/services/jobPositionService'
import { toLocalIso } from '@/utils/format'

const props = defineProps<{
  applicationId: number
  offer?: OfferRead | null
  jrJobPositionId?: number | null
  jrDeptId?: number | null
  jrJobPositionName?: string | null
  jrDeptName?: string | null
}>()

const emit = defineEmits<{
  (e: 'saved', offer: OfferRead): void
}>()

const visible = defineModel<boolean>('visible', { default: false })
const toast = useToast()
const saving = ref(false)
const editing = computed(() => !!props.offer)

// Có JR context → auto-fill và không cần user chọn vị trí/phòng ban
const hasJrContext = computed(() => !!props.jrJobPositionId && !!props.jrDeptId)

const departmentOptions = ref<{ label: string; value: number }[]>([])
const jobPositionOptions = ref<{ label: string; value: number }[]>([])

const form = ref({
  job_position_id: null as number | null,
  department_id: null as number | null,
  proposed_start_date: null as Date | null,
  official_salary: null as number | null,
  probation_salary: null as number | null,
  probation_days: 60 as number | null,
  expires_at: null as Date | null,
  benefits_note: '',
  internal_note: '',
})

const probationSalaryWarning = computed(() => {
  const off = form.value.official_salary
  const prob = form.value.probation_salary
  if (!off || !prob || off <= 0) return false
  return prob < off * 0.85
})

const probationDaysLimit = computed(() => props.offer?.probation_days_limit ?? 60)
const probationDaysWarning = computed(() => (form.value.probation_days ?? 0) > probationDaysLimit.value)

function resetForm() {
  const o = props.offer
  form.value = {
    job_position_id: o?.job_position_id ?? props.jrJobPositionId ?? null,
    department_id:   o?.department_id   ?? props.jrDeptId         ?? null,
    proposed_start_date: o?.proposed_start_date ? new Date(o.proposed_start_date) : null,
    official_salary:  o ? parseFloat(o.official_salary)  : null,
    probation_salary: o ? parseFloat(o.probation_salary) : null,
    probation_days:   o?.probation_days ?? 60,
    expires_at:       o?.expires_at ? new Date(o.expires_at) : null,
    benefits_note:    o?.benefits_note  ?? '',
    internal_note:    o?.internal_note  ?? '',
  }
}

function toDateStr(d: Date | null): string | null {
  if (!d) return null
  return toLocalIso(d)
}

async function save() {
  if (!form.value.job_position_id || !form.value.department_id
    || !form.value.proposed_start_date || !form.value.official_salary
    || !form.value.probation_salary || !form.value.probation_days) {
    toast.add({ severity: 'warn', summary: 'Thiếu thông tin', detail: 'Vui lòng điền đầy đủ các trường bắt buộc.', life: 3000 })
    return
  }
  saving.value = true
  try {
    const payload = {
      job_position_id: form.value.job_position_id,
      department_id:   form.value.department_id,
      proposed_start_date: toDateStr(form.value.proposed_start_date)!,
      official_salary:  form.value.official_salary,
      probation_salary: form.value.probation_salary,
      probation_days:   form.value.probation_days,
      expires_at:       toDateStr(form.value.expires_at),
      benefits_note:    form.value.benefits_note || null,
      internal_note:    form.value.internal_note || null,
    }
    const result = editing.value && props.offer
      ? await offerService.update(props.offer.id, payload)
      : await offerService.create(props.applicationId, payload)
    toast.add({ severity: 'success', summary: 'Đã lưu offer', life: 2000 })
    emit('saved', result)
    visible.value = false
  } catch (err: any) {
    const msg = err?.response?.data?.detail ?? 'Có lỗi xảy ra'
    toast.add({ severity: 'error', summary: 'Lỗi', detail: msg, life: 4000 })
  } finally {
    saving.value = false
  }
}

watch(visible, (v: boolean) => { if (v) resetForm() })

onMounted(async () => {
  // Chỉ load options khi không có JR context (cần cho trường hợp sửa offer)
  if (!hasJrContext.value || editing.value) {
    const [deptsRes, positionsRes] = await Promise.all([
      departmentService.getList(true),
      jobPositionService.getList({ is_active: true }),
    ])
    departmentOptions.value = deptsRes.data.map((d: any) => ({ label: d.name, value: d.id }))
    jobPositionOptions.value = positionsRes.data.map((p: any) => ({ label: p.name, value: p.id }))
  }
})
</script>
