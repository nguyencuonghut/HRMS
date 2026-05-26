<template>
  <Dialog
    v-model:visible="visible"
    header="Gửi email cho ứng viên"
    modal
    :style="{ width: '640px' }"
    @hide="reset"
  >
    <div class="rc-form" style="margin-top: 0.5rem">
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
          @change="onTemplateChange"
        />
      </div>

      <!-- No-email warning -->
      <div v-if="noEmail" style="color: var(--p-orange-600); font-size: 0.85rem; margin-bottom: 0.5rem">
        <i class="pi pi-exclamation-triangle" style="margin-right: 0.3rem" />
        Ứng viên chưa có email — email sẽ được ghi log với trạng thái "Lỗi".
      </div>

      <!-- Preview -->
      <div v-if="preview" class="comm-preview-panel">
        <div class="comm-preview-subject">
          <strong>Tiêu đề:</strong> {{ preview.subject }}
        </div>
        <div class="comm-preview-body">
          <!-- eslint-disable-next-line vue/no-v-html -->
          <div v-html="preview.body_html" />
        </div>
      </div>
      <div v-else-if="form.template_id && previewLoading" class="rc-jd-empty">Đang tải preview...</div>
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
import { ref, onMounted, watch } from 'vue'
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

const props = defineProps<{
  candidateId: number
  noEmail?: boolean
}>()

const emit = defineEmits<{ (e: 'sent'): void }>()

const visible = defineModel<boolean>('visible', { default: false })

const toast = useToast()

const templates = ref<EmailTemplateRead[]>([])
const templateOptions = ref<{ label: string; value: number }[]>([])
const form = ref({ template_id: null as number | null })
const preview = ref<EmailTemplatePreviewResult | null>(null)
const previewLoading = ref(false)
const sending = ref(false)

async function loadTemplates() {
  try {
    templates.value = await emailTemplateService.list()
    templateOptions.value = templates.value.map((t) => ({
      label: t.name + (t.trigger_event ? ` (${t.trigger_event})` : ''),
      value: t.id,
    }))
  } catch {}
}

async function onTemplateChange() {
  preview.value = null
  if (!form.value.template_id) return
  previewLoading.value = true
  try {
    preview.value = await emailTemplateService.preview(form.value.template_id, { use_sample_data: true })
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
    await communicationService.send(props.candidateId, { template_id: form.value.template_id })
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
  preview.value = null
}

watch(visible, (v) => {
  if (v) loadTemplates()
})

onMounted(loadTemplates)
</script>
