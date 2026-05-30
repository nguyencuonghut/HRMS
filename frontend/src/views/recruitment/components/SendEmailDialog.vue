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

      <!-- Stage indicator -->
      <div v-if="selectedApplicationStage" style="font-size: 0.83rem; color: var(--l-text-muted); margin-bottom: 0.25rem">
        <i class="pi pi-filter" style="margin-right: 0.3rem" />
        Giai đoạn hiện tại: <strong>{{ stageName(selectedApplicationStage) }}</strong>
        — chỉ hiển thị template phù hợp với giai đoạn này.
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
          <div v-html="sanitizeHtml(preview.body_html)" />
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
import { ref, computed, watch } from 'vue'
import { useSanitize } from '@/composables/useSanitize'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Select from 'primevue/select'
import { useToast } from 'primevue/usetoast'
import {
  emailTemplateService,
  communicationService,
  type EmailTemplateRead,
  type EmailTemplatePreviewResult,
  type ApplicationRead,
} from '@/services/recruitmentService'
import recruitmentService from '@/services/recruitmentService'

const props = defineProps<{
  candidateId: number
  noEmail?: boolean
}>()

const emit = defineEmits<{ (e: 'sent'): void }>()

const visible = defineModel<boolean>('visible', { default: false })

const toast = useToast()
const { sanitizeHtml } = useSanitize()

const templates = ref<EmailTemplateRead[]>([])
const applicationItems = ref<ApplicationRead[]>([])

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
  'hold': 'Tạm giữ hồ sơ',
}

const STAGE_NAMES: Record<string, string> = {
  new: 'Mới nộp',
  screening: 'Sàng lọc',
  test: 'Kiểm tra',
  interview: 'Phỏng vấn',
  final: 'Vòng cuối',
  offer: 'Đề nghị',
  hired: 'Đã tuyển',
  rejected: 'Đã từ chối',
  withdrawn: 'Đã rút',
}

function stageName(stage: string | null): string {
  return stage ? (STAGE_NAMES[stage] ?? stage) : ''
}

// trigger_event → danh sách stage được phép chọn template này
const TRIGGER_STAGE_ALLOW: Record<string, string[]> = {
  'stage_moved:new':        ['new'],
  'stage_moved:screening':  ['screening'],
  'stage_moved:test':       ['test'],
  'stage_moved:interview':  ['interview'],
  'stage_moved:final':      ['final'],
  'stage_moved:offer':      ['offer'],
  'interview_scheduled':    ['interview'],
  'offer_sent':             ['offer'],
  'offer_accepted':         ['offer'],
  'offer_rejected':         ['offer'],
  'hired':                  ['hired'],
  'hold':                   ['new', 'screening', 'test', 'interview', 'final'],
  'rejected':               [], // special: luôn cho phép (xem isTemplateAllowed)
}

function isTemplateAllowed(t: EmailTemplateRead, currentStage: string | null): boolean {
  if (!currentStage) return true                    // chưa chọn app → hiện tất cả
  if (!t.trigger_event) return true                 // template generic → luôn hiện
  if (t.trigger_event === 'rejected') return true   // từ chối có thể gửi ở bất kỳ giai đoạn nào
  const allowed = TRIGGER_STAGE_ALLOW[t.trigger_event]
  if (allowed === undefined) return true            // trigger không xác định → hiện
  return allowed.includes(currentStage)
}

const applicationOptions = computed(() =>
  applicationItems.value.map((a) => ({
    label: `${a.job_requisition_code} — ${a.job_position_name ?? ''}${a.department_name ? ' / ' + a.department_name : ''}`,
    value: a.id,
  }))
)

const selectedApplicationStage = computed<string | null>(() => {
  if (!form.value.application_id) return null
  return applicationItems.value.find((a) => a.id === form.value.application_id)?.current_stage ?? null
})

const templateOptions = computed(() =>
  templates.value
    .filter((t) => isTemplateAllowed(t, selectedApplicationStage.value))
    .map((t) => ({
      label: t.name + (t.trigger_event ? ` (${triggerEventLabels[t.trigger_event] ?? t.trigger_event})` : ''),
      value: t.id,
    }))
)

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
    applicationItems.value = appRes.data.items
    // auto-select nếu chỉ có 1 application
    if (appRes.data.items.length === 1) {
      form.value.application_id = appRes.data.items[0].id
    }
  } catch {}
}

// Reset template nếu không còn hợp lệ sau khi đổi application
watch(selectedApplicationStage, () => {
  if (form.value.template_id) {
    const stillValid = templateOptions.value.some((o) => o.value === form.value.template_id)
    if (!stillValid) {
      form.value.template_id = null
      preview.value = null
    }
  }
})

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
