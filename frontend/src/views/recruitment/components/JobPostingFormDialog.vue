<template>
  <Dialog
    :visible="visible"
    @update:visible="$emit('update:visible', $event)"
    :header="editing ? `Sửa tin: ${editing.title}` : 'Tạo tin tuyển dụng'"
    modal
    :style="{ width: '680px' }"
    :closable="!saving"
  >
    <div class="rc-form">
      <!-- JR -->
      <div class="rc-field">
        <label class="rc-label">Yêu cầu tuyển dụng (JR) <span class="rc-req">*</span></label>
        <Select
          v-model="form.job_requisition_id"
          :options="approvedJRs"
          option-label="label"
          option-value="value"
          placeholder="Chọn JR đã duyệt..."
          filter
          class="w-full"
          :disabled="!!editing"
          @change="onJrChange"
        />
        <span v-if="errors.job_requisition_id" class="rc-error">{{ errors.job_requisition_id }}</span>
      </div>

      <!-- Tiêu đề -->
      <div class="rc-field">
        <label class="rc-label">Tiêu đề tin <span class="rc-req">*</span></label>
        <InputText v-model="form.title" class="w-full" placeholder="VD: Tuyển kỹ sư phần mềm Senior..." />
        <span v-if="errors.title" class="rc-error">{{ errors.title }}</span>
      </div>

      <!-- Loại + kênh -->
      <div class="rc-row">
        <div class="rc-field">
          <label class="rc-label">Loại tin</label>
          <Select
            v-model="form.posting_type"
            :options="[{ label: 'Bên ngoài', value: 'external' }, { label: 'Nội bộ', value: 'internal' }]"
            option-label="label"
            option-value="value"
            class="w-full"
          />
        </div>
        <div class="rc-field">
          <label class="rc-label">Hạn nộp hồ sơ</label>
          <DatePicker
            v-model="form.deadline"
            date-format="dd/mm/yy"
            placeholder="Chọn ngày..."
            show-icon
            class="w-full"
          />
        </div>
      </div>

      <!-- Kênh đăng -->
      <div class="rc-field">
        <label class="rc-label">Kênh tuyển dụng</label>
        <MultiSelect
          v-model="form.channels"
          :options="channels"
          option-label="name"
          option-value="id"
          placeholder="Chọn kênh đăng..."
          filter
          class="w-full"
        />
      </div>

      <!-- Mức lương + địa điểm -->
      <div class="rc-row">
        <div class="rc-field">
          <label class="rc-label">Mức lương hiển thị</label>
          <InputText v-model="form.salary_display" class="w-full" placeholder="VD: 15–20 triệu hoặc Thỏa thuận" />
        </div>
        <div class="rc-field">
          <label class="rc-label">Địa điểm làm việc</label>
          <InputText v-model="form.work_location" class="w-full" placeholder="VD: Hà Nội, TP.HCM..." />
        </div>
      </div>

      <!-- Mô tả -->
      <div class="rc-field">
        <label class="rc-label">Mô tả công việc <span class="rc-req">*</span></label>
        <Textarea
          v-model="form.description"
          rows="4"
          class="w-full"
          auto-resize
          placeholder="Nội dung hiển thị cho ứng viên..."
          @blur="checkLanguage"
        />
        <span v-if="errors.description" class="rc-error">{{ errors.description }}</span>
      </div>

      <!-- Yêu cầu -->
      <div class="rc-field">
        <label class="rc-label">Yêu cầu ứng viên</label>
        <Textarea
          v-model="form.requirements"
          rows="3"
          class="w-full"
          auto-resize
          placeholder="Kinh nghiệm, kỹ năng, bằng cấp..."
          @blur="checkLanguage"
        />
      </div>

      <!-- Cảnh báo ngôn ngữ vi phạm -->
      <div v-if="langWarnings.length" class="rc-lang-warning">
        <i class="pi pi-exclamation-triangle" />
        <div>
          <strong>Cảnh báo ngôn ngữ có thể vi phạm Điều 8 BLLĐ:</strong>
          <span v-for="w in langWarnings" :key="w" class="rc-lang-chip">{{ w }}</span>
        </div>
      </div>

      <!-- Phúc lợi -->
      <div class="rc-field">
        <label class="rc-label">Phúc lợi</label>
        <Textarea v-model="form.benefits" rows="2" class="w-full" auto-resize placeholder="Bảo hiểm, thưởng, du lịch..." />
      </div>

      <!-- Ghi chú nội bộ -->
      <div class="rc-field">
        <label class="rc-label">Ghi chú nội bộ</label>
        <Textarea v-model="form.note" rows="2" class="w-full" auto-resize />
      </div>

      <p v-if="apiError" class="rc-api-error">
        <i class="pi pi-exclamation-triangle" /> {{ apiError }}
      </p>
    </div>

    <template #footer>
      <Button label="Hủy" severity="secondary" text :disabled="saving" @click="$emit('update:visible', false)" />
      <Button :label="editing ? 'Lưu thay đổi' : 'Tạo tin'" :loading="saving" @click="submit" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import Button from 'primevue/button'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import MultiSelect from 'primevue/multiselect'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import { useToast } from 'primevue/usetoast'

import recruitmentService, {
  type JobPostingRead,
  type JobRequisitionListItem,
  type RecruitmentChannelRead,
} from '@/services/recruitmentService'

const props = defineProps<{
  visible: boolean
  editing: JobPostingRead | null
}>()
const emit = defineEmits<{
  (e: 'update:visible', v: boolean): void
  (e: 'saved'): void
}>()

const toast = useToast()

const saving      = ref(false)
const apiError    = ref('')
const errors      = ref<Record<string, string>>({})
const langWarnings = ref<string[]>([])

const approvedJRs = ref<{ label: string; value: number }[]>([])
const channels    = ref<RecruitmentChannelRead[]>([])

const form = ref({
  job_requisition_id: null as number | null,
  title:         '',
  description:   '',
  requirements:  '',
  benefits:      '',
  work_location: '',
  salary_display: '',
  posting_type:  'external' as 'internal' | 'external',
  channels:      [] as number[],
  deadline:      null as Date | null,
  note:          '',
})

function resetForm() {
  errors.value      = {}
  apiError.value    = ''
  langWarnings.value = []
  if (props.editing) {
    const p = props.editing
    form.value = {
      job_requisition_id: p.job_requisition_id,
      title:         p.title,
      description:   p.description,
      requirements:  p.requirements ?? '',
      benefits:      p.benefits ?? '',
      work_location: p.work_location ?? '',
      salary_display: p.salary_display ?? '',
      posting_type:  p.posting_type as 'internal' | 'external',
      channels:      p.channels.map(c => c.id),
      deadline:      p.deadline ? new Date(p.deadline) : null,
      note:          p.note ?? '',
    }
  } else {
    form.value = {
      job_requisition_id: null,
      title:         '',
      description:   '',
      requirements:  '',
      benefits:      '',
      work_location: '',
      salary_display: '',
      posting_type:  'external',
      channels:      [],
      deadline:      null,
      note:          '',
    }
  }
}

watch(() => props.visible, v => { if (v) resetForm() })

async function onJrChange() {
  if (!form.value.job_requisition_id || props.editing) return
  try {
    const res = await recruitmentService.getJR(form.value.job_requisition_id)
    const jr = res.data
    if (!form.value.title)
      form.value.title = jr.job_position_name
    if (!form.value.description && jr.effective_description)
      form.value.description = jr.effective_description
    if (!form.value.requirements && jr.effective_requirements)
      form.value.requirements = jr.effective_requirements
  } catch { /* ignore */ }
}

async function checkLanguage() {
  const text = `${form.value.description} ${form.value.requirements}`.trim()
  if (!text) { langWarnings.value = []; return }
  try {
    const res = await recruitmentService.validateLanguage(text)
    langWarnings.value = res.data.warnings
  } catch { langWarnings.value = [] }
}

function validate(): boolean {
  errors.value = {}
  if (!form.value.job_requisition_id) errors.value.job_requisition_id = 'Vui lòng chọn JR'
  if (!form.value.title.trim()) errors.value.title = 'Vui lòng nhập tiêu đề'
  if (!form.value.description.trim()) errors.value.description = 'Vui lòng nhập mô tả công việc'
  return Object.keys(errors.value).length === 0
}

async function submit() {
  if (!validate()) return
  saving.value  = true
  apiError.value = ''
  try {
    const payload = {
      job_requisition_id: form.value.job_requisition_id!,
      title:         form.value.title.trim(),
      description:   form.value.description.trim(),
      requirements:  form.value.requirements.trim() || null,
      benefits:      form.value.benefits.trim() || null,
      work_location: form.value.work_location.trim() || null,
      salary_display: form.value.salary_display.trim() || null,
      posting_type:  form.value.posting_type,
      channels:      form.value.channels,
      deadline:      form.value.deadline ? form.value.deadline.toISOString().substring(0, 10) : null,
      note:          form.value.note.trim() || null,
    }
    if (props.editing) {
      await recruitmentService.updatePosting(props.editing.id, payload)
    } else {
      await recruitmentService.createPosting(payload)
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
    const [jrRes, chRes] = await Promise.all([
      recruitmentService.listJR({ status: 'approved', page_size: 200 }),
      recruitmentService.listChannels(),
    ])
    const inProgress = await recruitmentService.listJR({ status: 'in_progress', page_size: 200 })
    const allJRs = [...(jrRes.data.items ?? []), ...(inProgress.data.items ?? [])]
    approvedJRs.value = allJRs.map((jr: JobRequisitionListItem) => ({
      label: `${jr.code} — ${jr.job_position_name} (${jr.department_name})`,
      value: jr.id,
    }))
    channels.value = chRes.data.filter(c => c.is_active)
  } catch { /* ignore */ }
})
</script>
