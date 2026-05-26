<template>
  <div class="section-stack" style="padding-top: 0.75rem">
    <div class="section-card">
      <div class="section-header">
        <span class="section-title">Email Templates tuyển dụng</span>
        <Button
          label="Tạo template"
          icon="pi pi-plus"
          size="small"
          @click="openCreate"
        />
      </div>

      <div v-if="loading" class="rc-jd-empty">Đang tải...</div>
      <div v-else-if="!templates.length" class="rc-jd-empty">Chưa có template nào.</div>

      <DataTable v-else :value="templates" size="small" striped-rows>
        <Column field="name" header="Tên template">
          <template #body="{ data }: { data: EmailTemplateRead }">
            <span>{{ data.name }}</span>
            <Tag v-if="data.is_system" value="System" severity="secondary" style="font-size: 0.7rem; margin-left: 0.4rem" />
          </template>
        </Column>
        <Column field="trigger_event" header="Sự kiện kích hoạt" style="width: 200px">
          <template #body="{ data }: { data: EmailTemplateRead }">
            <span class="rc-muted" style="font-size: 0.8rem">{{ data.trigger_event ?? '— thủ công —' }}</span>
          </template>
        </Column>
        <Column header="Trạng thái" style="width: 110px">
          <template #body="{ data }: { data: EmailTemplateRead }">
            <Tag
              :value="data.is_active ? 'Hoạt động' : 'Tắt'"
              :severity="data.is_active ? 'success' : 'secondary'"
              style="font-size: 0.72rem"
            />
          </template>
        </Column>
        <Column header="" style="width: 120px; text-align: right">
          <template #body="{ data }: { data: EmailTemplateRead }">
            <div style="display: flex; gap: 0.25rem; justify-content: flex-end">
              <Button
                icon="pi pi-eye"
                text
                rounded
                size="small"
                severity="info"
                v-tooltip.top="'Xem preview'"
                @click="openPreview(data)"
              />
              <Button
                icon="pi pi-pencil"
                text
                rounded
                size="small"
                severity="secondary"
                v-tooltip.top="'Sửa'"
                @click="openEdit(data)"
              />
              <Button
                v-if="!data.is_system"
                icon="pi pi-trash"
                text
                rounded
                size="small"
                severity="danger"
                v-tooltip.top="'Xóa'"
                @click="confirmDelete(data)"
              />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>
  </div>

  <!-- Create/Edit dialog -->
  <Dialog
    v-model:visible="showFormDialog"
    :header="editingTemplate ? 'Sửa template' : 'Tạo template mới'"
    modal
    :style="{ width: '700px' }"
  >
    <div class="rc-form" style="margin-top: 0.5rem">
      <div class="rc-row">
        <div class="rc-field">
          <label class="rc-label">Code <span class="rc-req">*</span></label>
          <InputText v-model="form.code" :disabled="!!editingTemplate" class="w-full" placeholder="vd: invite_interview" />
        </div>
        <div class="rc-field">
          <label class="rc-label">Sự kiện kích hoạt</label>
          <Select
            v-model="form.trigger_event"
            :options="triggerOptions"
            option-label="label"
            option-value="value"
            show-clear
            placeholder="— Chỉ gửi thủ công —"
            class="w-full"
          />
        </div>
      </div>
      <div class="rc-field">
        <label class="rc-label">Tên template <span class="rc-req">*</span></label>
        <InputText v-model="form.name" class="w-full" />
      </div>
      <div class="rc-field">
        <label class="rc-label">Tiêu đề email <span class="rc-req">*</span></label>
        <InputText v-model="form.subject" class="w-full" placeholder="Hỗ trợ merge fields như {{ten_ung_vien}}" />
      </div>
      <div class="rc-field">
        <label class="rc-label">Nội dung HTML <span class="rc-req">*</span></label>
        <Textarea v-model="form.body_html" rows="10" auto-resize class="w-full" style="font-family: monospace; font-size: 0.8rem" />
        <small class="rc-muted">Hỗ trợ merge fields: {{ mergeFieldHint }}</small>
      </div>
      <div v-if="editingTemplate" class="rc-field" style="flex-direction: row; align-items: center; gap: 0.5rem">
        <ToggleSwitch v-model="form.is_active" />
        <label style="font-size: 0.875rem; cursor: pointer">Hoạt động</label>
      </div>
      <p v-if="formError" class="rc-api-error"><i class="pi pi-exclamation-circle" />{{ formError }}</p>
    </div>
    <template #footer>
      <Button label="Hủy" severity="secondary" outlined @click="showFormDialog = false" />
      <Button label="Lưu" :loading="saving" @click="doSave" />
    </template>
  </Dialog>

  <!-- Preview dialog -->
  <Dialog
    v-model:visible="showPreviewDialog"
    header="Preview template"
    modal
    :style="{ width: '680px' }"
  >
    <div v-if="previewResult" style="margin-top: 0.5rem">
      <div style="font-weight: 600; margin-bottom: 0.5rem">Tiêu đề: {{ previewResult.subject }}</div>
      <div class="comm-preview-body">
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div v-html="previewResult.body_html" />
      </div>
    </div>
    <div v-else class="rc-jd-empty">Đang tải...</div>
    <template #footer>
      <Button label="Đóng" severity="secondary" outlined @click="showPreviewDialog = false" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import ToggleSwitch from 'primevue/toggleswitch'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import {
  emailTemplateService,
  type EmailTemplateRead,
  type EmailTemplatePreviewResult,
} from '@/services/recruitmentService'

const confirm = useConfirm()
const toast = useToast()

const templates = ref<EmailTemplateRead[]>([])
const loading = ref(false)
const saving = ref(false)
const formError = ref('')

const showFormDialog = ref(false)
const editingTemplate = ref<EmailTemplateRead | null>(null)
const form = ref({
  code: '',
  name: '',
  trigger_event: null as string | null,
  subject: '',
  body_html: '',
  is_active: true,
})

const showPreviewDialog = ref(false)
const previewResult = ref<EmailTemplatePreviewResult | null>(null)

const mergeFieldHint = '{{ten_ung_vien}}, {{vi_tri}}, {{ngay_phong_van}}, {{gio_phong_van}}, {{dia_diem_phong_van}}, {{ten_hr}}, ...'

const triggerOptions = [
  { label: 'Chuyển giai đoạn: Sàng lọc', value: 'stage_moved:screening' },
  { label: 'Chuyển giai đoạn: Phỏng vấn', value: 'stage_moved:interview' },
  { label: 'Chuyển giai đoạn: Đề nghị', value: 'stage_moved:offer' },
  { label: 'Gửi offer', value: 'offer_sent' },
  { label: 'Ứng viên chấp nhận offer', value: 'offer_accepted' },
  { label: 'Ứng viên từ chối offer', value: 'offer_rejected' },
  { label: 'Tuyển dụng thành công', value: 'hired' },
  { label: 'Từ chối ứng viên', value: 'rejected' },
]

async function load() {
  loading.value = true
  try {
    templates.value = await emailTemplateService.list()
  } catch {
    templates.value = []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingTemplate.value = null
  form.value = { code: '', name: '', trigger_event: null, subject: '', body_html: '', is_active: true }
  formError.value = ''
  showFormDialog.value = true
}

function openEdit(t: EmailTemplateRead) {
  editingTemplate.value = t
  form.value = {
    code: t.code,
    name: t.name,
    trigger_event: t.trigger_event,
    subject: t.subject,
    body_html: t.body_html,
    is_active: t.is_active,
  }
  formError.value = ''
  showFormDialog.value = true
}

async function doSave() {
  if (!form.value.name.trim() || !form.value.subject.trim() || !form.value.body_html.trim()) {
    formError.value = 'Vui lòng điền đầy đủ các trường bắt buộc'
    return
  }
  saving.value = true
  formError.value = ''
  try {
    if (editingTemplate.value) {
      await emailTemplateService.update(editingTemplate.value.id, {
        name: form.value.name,
        trigger_event: form.value.trigger_event,
        subject: form.value.subject,
        body_html: form.value.body_html,
        is_active: form.value.is_active,
      })
      toast.add({ severity: 'success', summary: 'Đã cập nhật template', life: 3000 })
    } else {
      if (!form.value.code.trim()) {
        formError.value = 'Code không được để trống'
        return
      }
      await emailTemplateService.create({
        code: form.value.code,
        name: form.value.name,
        trigger_event: form.value.trigger_event,
        subject: form.value.subject,
        body_html: form.value.body_html,
      })
      toast.add({ severity: 'success', summary: 'Đã tạo template', life: 3000 })
    }
    showFormDialog.value = false
    await load()
  } catch (err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    formError.value = typeof detail === 'string' ? detail : 'Lỗi lưu template'
  } finally {
    saving.value = false
  }
}

function confirmDelete(t: EmailTemplateRead) {
  confirm.require({
    message: `Xóa template "${t.name}"?`,
    header: 'Xác nhận xóa',
    acceptLabel: 'Xóa',
    rejectLabel: 'Hủy',
    accept: async () => {
      try {
        await emailTemplateService.delete(t.id)
        toast.add({ severity: 'success', summary: 'Đã xóa template', life: 3000 })
        await load()
      } catch (err: unknown) {
        const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        toast.add({
          severity: 'error',
          summary: 'Không thể xóa',
          detail: typeof detail === 'string' ? detail : 'Lỗi xóa template',
          life: 4000,
        })
      }
    },
  })
}

async function openPreview(t: EmailTemplateRead) {
  previewResult.value = null
  showPreviewDialog.value = true
  try {
    previewResult.value = await emailTemplateService.preview(t.id, { use_sample_data: true })
  } catch {
    previewResult.value = { subject: '(Lỗi preview)', body_html: '' }
  }
}

onMounted(load)
</script>
