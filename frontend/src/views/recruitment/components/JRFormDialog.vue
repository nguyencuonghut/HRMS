<template>
  <Dialog
    :visible="visible"
    @update:visible="$emit('update:visible', $event)"
    :header="editingJr ? `Sửa JR ${editingJr.code}` : 'Tạo yêu cầu tuyển dụng'"
    modal
    :style="{ width: '620px' }"
    :closable="!saving"
  >
    <div class="rc-form">
      <!-- Vị trí công việc -->
      <div class="rc-field">
        <label class="rc-label">Vị trí công việc <span class="rc-req">*</span></label>
        <Select
          v-model="form.job_position_id"
          :options="positions"
          option-label="name"
          option-value="id"
          placeholder="Chọn vị trí..."
          filter
          :disabled="!!editingJr"
          class="w-full"
          @change="onPositionChange"
        />
        <span v-if="errors.job_position_id" class="rc-error">{{ errors.job_position_id }}</span>
      </div>

      <!-- Phòng ban -->
      <div class="rc-field">
        <label class="rc-label">Phòng ban <span class="rc-req">*</span></label>
        <Select
          v-model="form.department_id"
          :options="departments"
          option-label="name"
          option-value="id"
          placeholder="Chọn phòng ban..."
          filter
          class="w-full"
        />
        <span v-if="errors.department_id" class="rc-error">{{ errors.department_id }}</span>
      </div>

      <!-- Số lượng + Lý do -->
      <div class="rc-row">
        <div class="rc-field">
          <label class="rc-label">Số lượng cần tuyển <span class="rc-req">*</span></label>
          <InputNumber v-model="form.quantity" :min="1" :max="100" :use-grouping="false" class="w-full" />
          <span v-if="errors.quantity" class="rc-error">{{ errors.quantity }}</span>
        </div>
        <div class="rc-field">
          <label class="rc-label">Lý do tuyển <span class="rc-req">*</span></label>
          <Select
            v-model="form.reason_type"
            :options="reasonOptions"
            option-label="label"
            option-value="value"
            placeholder="Chọn lý do..."
            class="w-full"
          />
          <span v-if="errors.reason_type" class="rc-error">{{ errors.reason_type }}</span>
        </div>
      </div>

      <!-- Lương min–max -->
      <div class="rc-row">
        <div class="rc-field">
          <label class="rc-label">Lương từ (VND)</label>
          <InputNumber
            v-model="form.salary_min"
            :min="0"
            :use-grouping="true"
            locale="vi-VN"
            class="w-full"
            placeholder="Không bắt buộc"
          />
        </div>
        <div class="rc-field">
          <label class="rc-label">Đến (VND)</label>
          <InputNumber
            v-model="form.salary_max"
            :min="0"
            :use-grouping="true"
            locale="vi-VN"
            class="w-full"
            placeholder="Không bắt buộc"
          />
        </div>
      </div>
      <span v-if="errors.salary" class="rc-error">{{ errors.salary }}</span>

      <!-- Hạn cần người -->
      <div class="rc-field">
        <label class="rc-label">Hạn cần người</label>
        <DatePicker
          v-model="form.deadline"
          date-format="dd/mm/yy"
          placeholder="Chọn ngày..."
          show-icon
          class="w-full"
        />
      </div>

      <!-- JD override -->
      <div class="rc-field">
        <div class="rc-jd-header">
          <label class="rc-label">Mô tả công việc</label>
          <span class="rc-optional">(Để trống = dùng từ vị trí công việc)</span>
        </div>
        <Textarea v-model="form.jd_description" rows="3" class="w-full" auto-resize placeholder="Mô tả công việc cho đợt tuyển này..." />
      </div>

      <div class="rc-field">
        <label class="rc-label">Yêu cầu ứng viên</label>
        <Textarea v-model="form.jd_requirements" rows="3" class="w-full" auto-resize placeholder="Yêu cầu cho đợt tuyển này..." />
      </div>

      <!-- Ghi chú nội bộ -->
      <div class="rc-field">
        <label class="rc-label">Ghi chú nội bộ</label>
        <Textarea v-model="form.internal_note" rows="2" class="w-full" auto-resize placeholder="Ghi chú nội bộ..." />
      </div>

      <p v-if="apiError" class="rc-api-error">
        <i class="pi pi-exclamation-triangle" />
        {{ apiError }}
      </p>
    </div>

    <template #footer>
      <Button label="Hủy" severity="secondary" text :disabled="saving" @click="$emit('update:visible', false)" />
      <Button :label="editingJr ? 'Lưu thay đổi' : 'Tạo JR'" :loading="saving" @click="submit" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import Button from 'primevue/button'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import { useToast } from 'primevue/usetoast'

import recruitmentService, { type JobRequisitionRead } from '@/services/recruitmentService'
import departmentService, { type DepartmentRead } from '@/services/departmentService'
import jobPositionService, { type JobPositionListItem } from '@/services/jobPositionService'
import { toLocalIso } from '@/utils/format'

const props = defineProps<{
  visible: boolean
  editingJr: JobRequisitionRead | null
}>()
const emit = defineEmits<{
  (e: 'update:visible', v: boolean): void
  (e: 'saved'): void
}>()

const toast = useToast()

const saving  = ref(false)
const apiError = ref('')
const errors   = ref<Record<string, string>>({})

const departments = ref<DepartmentRead[]>([])
const positions   = ref<JobPositionListItem[]>([])

const reasonOptions = [
  { label: 'Vị trí mới',       value: 'new' },
  { label: 'Thay thế nhân sự', value: 'replacement' },
  { label: 'Mở rộng',          value: 'expansion' },
]

const form = ref({
  job_position_id: null as number | null,
  department_id:   null as number | null,
  quantity:        1,
  reason_type:     'new' as string,
  salary_min:      null as number | null,
  salary_max:      null as number | null,
  deadline:        null as Date | null,
  jd_description:  '',
  jd_requirements: '',
  internal_note:   '',
})

function resetForm() {
  errors.value  = {}
  apiError.value = ''
  if (props.editingJr) {
    const jr = props.editingJr
    form.value = {
      job_position_id: jr.job_position_id,
      department_id:   jr.department_id,
      quantity:        jr.quantity,
      reason_type:     jr.reason_type,
      salary_min:      jr.salary_min ? Number(jr.salary_min) : null,
      salary_max:      jr.salary_max ? Number(jr.salary_max) : null,
      deadline:        jr.deadline ? new Date(jr.deadline) : null,
      jd_description:  jr.jd_description ?? '',
      jd_requirements: jr.jd_requirements ?? '',
      internal_note:   jr.internal_note ?? '',
    }
  } else {
    form.value = {
      job_position_id: null,
      department_id:   null,
      quantity:        1,
      reason_type:     'new',
      salary_min:      null,
      salary_max:      null,
      deadline:        null,
      jd_description:  '',
      jd_requirements: '',
      internal_note:   '',
    }
  }
}

watch(() => props.visible, (v) => { if (v) resetForm() })

function onPositionChange() {
  const pos = positions.value.find(p => p.id === form.value.job_position_id)
  if (pos && !form.value.department_id) {
    form.value.department_id = pos.department_id
  }
}

function validate(): boolean {
  errors.value = {}
  if (!form.value.job_position_id) errors.value.job_position_id = 'Vui lòng chọn vị trí'
  if (!form.value.department_id)   errors.value.department_id   = 'Vui lòng chọn phòng ban'
  if (!form.value.quantity || form.value.quantity < 1) errors.value.quantity = 'Số lượng phải ≥ 1'
  if (!form.value.reason_type) errors.value.reason_type = 'Vui lòng chọn lý do'
  if (form.value.salary_min !== null && form.value.salary_max !== null
      && form.value.salary_min > form.value.salary_max) {
    errors.value.salary = 'Lương tối thiểu không được lớn hơn lương tối đa'
  }
  return Object.keys(errors.value).length === 0
}

async function submit() {
  if (!validate()) return
  saving.value  = true
  apiError.value = ''
  try {
    const payload = {
      job_position_id:  form.value.job_position_id!,
      department_id:    form.value.department_id!,
      quantity:         form.value.quantity,
      reason_type:      form.value.reason_type,
      salary_min:       form.value.salary_min,
      salary_max:       form.value.salary_max,
      deadline:         form.value.deadline ? toLocalIso(form.value.deadline) : null,
      jd_description:   form.value.jd_description.trim() || null,
      jd_requirements:  form.value.jd_requirements.trim() || null,
      internal_note:    form.value.internal_note.trim() || null,
    }
    if (props.editingJr) {
      await recruitmentService.updateJR(props.editingJr.id, payload)
      toast.add({ severity: 'success', summary: 'Đã cập nhật', detail: 'Yêu cầu tuyển dụng đã được cập nhật', life: 3000 })
    } else {
      await recruitmentService.createJR(payload)
      toast.add({ severity: 'success', summary: 'Đã tạo', detail: 'Yêu cầu tuyển dụng đã được tạo', life: 3000 })
    }
    emit('saved')
  } catch (err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    apiError.value = typeof detail === 'string' ? detail : 'Có lỗi xảy ra, vui lòng thử lại'
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    const [deptsRes, posRes] = await Promise.all([
      departmentService.getList(true),
      jobPositionService.getList({ is_active: true }),
    ])
    departments.value = deptsRes.data
    positions.value   = posRes.data
  } catch { /* ignore */ }
})
</script>
