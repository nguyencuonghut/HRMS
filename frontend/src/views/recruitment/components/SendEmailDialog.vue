<template>
  <Dialog
    v-model:visible="visible"
    header="Gửi email cho ứng viên"
    modal
    :style="{ width: '640px' }"
    @hide="reset"
  >
    <div class="rc-form" style="margin-top: 0.5rem">
      <!-- Application select -->
      <div class="rc-field">
        <label class="rc-label">Ứng tuyển (JR) <span class="rc-optional">(để lấy vị trí, phòng ban)</span></label>
        <Select
          v-model="form.application_id"
          :options="applicationOptions"
          option-label="label"
          option-value="value"
          show-clear
          placeholder="— Chọn JR liên quan —"
          class="w-full"
          @change="onContextChange"
        />
      </div>

      <!-- Template select -->
      <div class="rc-field">
        <label class="rc-label">Template <span class="rc-req">*</span></label>
        <Select
          v-model="form.template_id"
          :options="templateOptions"
          option-label="label"
          option-value="value"
          placeholder="Chọn template email"
          filter
          class="w-full"
          @change="onContextChange"
        />
      </div>

      <!-- No-email warning -->
      <div v-if="noEmail" style="color: var(--p-orange-600); font-size: 0.85rem; margin-bottom: 0.5rem">
        <i class="pi pi-exclamation-triangle" style="margin-right: 0.3rem" />
        Ứng viên chưa có email — email sẽ được ghi log với trạng thái "Lỗi".
      </div>

      <!-- Preview -->
      <div v-if="previewLoading" class="rc-jd-empty">Đang tải preview...</div>
      <div v-else-if="preview" class="comm-preview-panel">
        <div class="comm-preview-subject">
          <strong>Tiêu đề:</strong> {{ preview.subject }}
        </div>
        <div class="comm-preview-body">
          <!-- eslint-disable-next-line vue/no-v-html -->
          <div v-html="preview.body_html" />
        </div>
      </div>
    </div>

    <template #footer>
      <Button label="Hủy" severity="secondary" outlined @click="visible = false" />
      <Button
        label="Gửi ngay"
        icon="pi pi-send"
        :loading="sending"
        :disabled="!form.template_id"
        @click="doSend"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Select from 'primevue/select'
import { useToast } from 'primevue/usetoast'
import {
  emailTemplateService,
  communicationService,
  type EmailTemplateRead,
  type EmailTemplatePreviewResult,
} from '@/services/recruitmentService'
import recruitmentService from '@/services/recruitmentService'

const props = defineProps<{
  candidateId: number
  noEmail?: boolean
}>()

const emit = defineEmits<{ (e: 'sent'): void }>()

const visible = defineModel<boolean>('visible', { default: false })

const toast = useToast()

const templates = ref<EmailTemplateRead[]>([])
const triggerEventLabels: Record<string, string> = {
  'stage_moved:screening': 'Chuyển giai đoạn: Sàng lọc',
  'stage_moved:interview': 'Chuyển giai đoạn: Phỏng vấn (chưa có lịch)',
  'interview_scheduled': 'Lịch phỏng vấn đã được xếp',
  'stage_moved:offer': 'Chuyển giai đoạn: Đề nghị',
  'offer_sent': 'Gửi offer',
  'offer_accepted': 'Ứng viên chấp nhận offer',
  'offer_rejected': 'Ứng viên từ chối offer',
  'hired': 'Tuyển dụng thành công',
  'rejected': 'Từ chối ứng viên',
}

const templateOptions = ref<{ label: string; value: number }[]>([])
const applicationOptions = ref<{ label: string; value: number }[]>([])

const form = ref({
  template_id: null as number | null,
  application_id: null as number | null,
})
const preview = ref<EmailTemplatePreviewResult | null>(null)
const previewLoading = ref(false)
const sending = ref(false)

async function loadData() {
  try {
    const [tplRes, appRes] = await Promise.all([
      emailTemplateService.list(),
      recruitmentService.listCandidateApplications(props.candidateId, { page_size: 50 }),
    ])
    templates.value = tplRes
    templateOptions.value = tplRes.map((t) => ({
      label: t.name + (t.trigger_event ? ` (${triggerEventLabels[t.trigger_event] ?? t.trigger_event})` : ''),
      value: t.id,
    }))
    applicationOptions.value = appRes.data.items.map((a) => ({
      label: `${a.job_requisition_code} — ${a.job_position_name ?? ''}${a.department_name ? ' / ' + a.department_name : ''}`,
      value: a.id,
    }))
    // auto-select nếu chỉ có 1 application
    if (appRes.data.items.length === 1) {
      form.value.application_id = appRes.data.items[0].id
    }
  } catch {}
}

async function onContextChange() {
  preview.value = null
  if (!form.value.template_id) return
  previewLoading.value = true
  try {
    preview.value = await emailTemplateService.preview(form.value.template_id, {
      candidate_id: props.candidateId,
      application_id: form.value.application_id ?? undefined,
      use_sample_data: false,
    })
  } catch {
    preview.value = null
  } finally {
    previewLoading.value = false
  }
}

async function doSend() {
  if (!form.value.template_id) return
  sending.value = true
  try {
    await communicationService.send(props.candidateId, {
      template_id: form.value.template_id,
      application_id: form.value.application_id ?? undefined,
    })
    toast.add({ severity: 'success', summary: 'Đã gửi email', life: 3000 })
    emit('sent')
  } catch (err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    toast.add({
      severity: 'error',
      summary: 'Lỗi gửi email',
      detail: typeof detail === 'string' ? detail : 'Không thể gửi email',
      life: 4000,
    })
  } finally {
    sending.value = false
  }
}

function reset() {
  form.value.template_id = null
  form.value.application_id = null
  preview.value = null
}

watch(visible, (v) => {
  if (v) loadData()
})
</script>
