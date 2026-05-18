<template>
  <div class="section-stack">
    <!-- Toolbar -->
    <div class="section-header" style="padding: 0.25rem 0 0.5rem;">
      <div style="display:flex; gap:0.5rem; align-items:center;">
        <Select
          v-model="filterType"
          :options="filterOptions"
          option-label="label"
          option-value="value"
          filter
          show-clear
          placeholder="Lọc loại tài liệu"
          style="min-width:200px;"
          @change="load"
        />
      </div>
      <Button
        v-if="canEdit"
        label="Tải lên tài liệu"
        icon="pi pi-upload"
        size="small"
        @click="openUpload"
      />
    </div>

    <!-- Loading -->
    <div v-if="loading" style="text-align:center; padding:2rem;">
      <i class="pi pi-spin pi-spinner" style="font-size:1.5rem;" />
    </div>

    <!-- Empty state -->
    <div v-else-if="displayGroups.length === 0" style="text-align:center; padding:2rem; color:var(--l-text-muted);">
      <i class="pi pi-paperclip" style="font-size:2rem; margin-bottom:0.5rem; display:block;" />
      <span>Chưa có tài liệu nào</span>
    </div>

    <!-- Grouped list -->
    <template v-else>
      <div v-for="group in displayGroups" :key="group.label" class="attachment-group">
        <div class="attachment-group-title">{{ group.label }}</div>
        <div class="attachment-list">
          <div
            v-for="(att, idx) in group.items"
            :key="att.id"
            class="attachment-row"
            :class="{ 'attachment-old': idx > 0 }"
          >
            <span class="attachment-icon">{{ fileIcon(att.mime_type, att.file_name) }}</span>
            <div class="attachment-info">
              <div class="attachment-name" :title="att.file_name">{{ att.file_name }}</div>
              <div class="attachment-meta">
                {{ formatSize(att.file_size) }} &middot; {{ formatDate(att.uploaded_at) }}
                <span v-if="att.description"> &middot; {{ att.description }}</span>
                <Tag v-if="idx === 0 && group.items.length > 1" value="Mới nhất" severity="info" style="font-size:0.7rem; margin-left:0.4rem;" />
              </div>
            </div>
            <div class="attachment-actions">
              <Button
                icon="pi pi-download"
                rounded
                text
                size="small"
                v-tooltip.top="'Tải xuống'"
                @click="download(att)"
              />
              <Button
                v-if="canEdit"
                icon="pi pi-trash"
                rounded
                text
                size="small"
                severity="danger"
                v-tooltip.top="'Xóa'"
                @click="confirmDelete(att)"
              />
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>

  <!-- Upload dialog -->
  <Dialog v-model:visible="uploadVisible" modal header="Tải lên tài liệu" style="width:420px;">
    <div class="form-grid" style="gap:1rem;">
      <div class="col-full">
        <label class="field-label">Loại tài liệu <span class="required">*</span></label>
        <Select
          v-model="uploadForm.document_type"
          :options="DOCUMENT_TYPE_OPTIONS"
          option-label="label"
          option-value="value"
          filter
          placeholder="Chọn loại tài liệu"
          class="w-full"
        />
      </div>
      <div class="col-full">
        <label class="field-label">Mô tả</label>
        <InputText v-model="uploadForm.description" class="w-full" placeholder="Tùy chọn" maxlength="255" />
      </div>
      <div class="col-full">
        <label class="field-label">File <span class="required">*</span></label>
        <input
          ref="fileInput"
          type="file"
          accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
          style="display:none;"
          @change="onFileSelected"
        />
        <div class="attachment-upload-zone" @click="fileInput?.click()">
          <template v-if="uploadForm.file">
            <i class="pi pi-check-circle" style="margin-right:0.4rem;" />
            {{ uploadForm.file.name }} ({{ formatSize(uploadForm.file.size) }})
          </template>
          <template v-else>
            <i class="pi pi-upload" style="margin-right:0.4rem;" />
            Nhấn để chọn file (PDF, ảnh, Word — tối đa 20 MB)
          </template>
        </div>
        <small v-if="uploadError" class="p-error">{{ uploadError }}</small>
      </div>
    </div>
    <template #footer>
      <Button label="Hủy" text @click="uploadVisible = false" />
      <Button label="Tải lên" icon="pi pi-upload" :loading="uploading" @click="submitUpload" />
    </template>
  </Dialog>

  <!-- Confirm delete -->
  <ConfirmDialog />
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import ConfirmDialog from 'primevue/confirmdialog'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'

import { useAuthStore } from '@/stores/auth'
import employeeService, {
  DOCUMENT_TYPE_GROUPS,
  DOCUMENT_TYPE_OPTIONS,
  type EmployeeAttachmentRead,
} from '@/services/employeeService'

const props = defineProps<{ employeeId: number }>()

const confirm = useConfirm()
const toast   = useToast()
const auth    = useAuthStore()
const canEdit = computed(() => auth.hasPermission('employees:edit'))

// ── State ─────────────────────────────────────────────────────────
const loading   = ref(false)
const uploading = ref(false)
const attachments = ref<EmployeeAttachmentRead[]>([])
const filterType  = ref<string | null>(null)
const uploadVisible = ref(false)
const fileInput     = ref<HTMLInputElement | null>(null)
const uploadError   = ref('')

const uploadForm = ref({
  document_type: '',
  description:   '',
  file:          null as File | null,
})

// ── Computed ──────────────────────────────────────────────────────
const filterOptions = [
  { label: 'Tất cả', value: '' },
  ...DOCUMENT_TYPE_OPTIONS,
]

const displayGroups = computed(() => {
  const list = attachments.value
  const result: { label: string; items: EmployeeAttachmentRead[] }[] = []

  for (const group of DOCUMENT_TYPE_GROUPS) {
    const items = list.filter(a => group.types.includes(a.document_type))
    if (items.length) {
      result.push({ label: group.label, items })
    }
  }

  // Types not in any group
  const knownTypes = DOCUMENT_TYPE_GROUPS.flatMap(g => g.types)
  const others = list.filter(a => !knownTypes.includes(a.document_type))
  if (others.length) result.push({ label: 'Khác', items: others })

  return result
})

// ── Load ──────────────────────────────────────────────────────────
async function load() {
  loading.value = true
  try {
    const res = await employeeService.getAttachments(
      props.employeeId,
      filterType.value || undefined,
    )
    attachments.value = res.data
  } finally {
    loading.value = false
  }
}

load()

// ── Upload ────────────────────────────────────────────────────────
function openUpload() {
  uploadForm.value = { document_type: '', description: '', file: null }
  uploadError.value = ''
  uploadVisible.value = true
}

function onFileSelected(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (!f) return
  if (f.size > 20 * 1024 * 1024) {
    uploadError.value = 'File vượt quá 20 MB'
    return
  }
  uploadError.value = ''
  uploadForm.value.file = f
}

async function submitUpload() {
  uploadError.value = ''
  if (!uploadForm.value.document_type) {
    uploadError.value = 'Vui lòng chọn loại tài liệu'
    return
  }
  if (!uploadForm.value.file) {
    uploadError.value = 'Vui lòng chọn file'
    return
  }
  const fd = new FormData()
  fd.append('document_type', uploadForm.value.document_type)
  if (uploadForm.value.description) fd.append('description', uploadForm.value.description)
  fd.append('file', uploadForm.value.file)

  uploading.value = true
  try {
    await employeeService.uploadAttachment(props.employeeId, fd)
    toast.add({ severity: 'success', summary: 'Đã tải lên', life: 3000 })
    uploadVisible.value = false
    await load()
  } catch (err: any) {
    const detail = err?.response?.data?.detail
    toast.add({ severity: 'error', summary: 'Lỗi', detail: detail ?? 'Không tải được file', life: 4000 })
  } finally {
    uploading.value = false
  }
}

// ── Download ──────────────────────────────────────────────────────
function download(att: EmployeeAttachmentRead) {
  const url = employeeService.getAttachmentDownloadUrl(props.employeeId, att.id)
  const a = document.createElement('a')
  a.href = `/api/v1${url}`
  a.download = att.file_name
  a.click()
}

// ── Delete ────────────────────────────────────────────────────────
function confirmDelete(att: EmployeeAttachmentRead) {
  confirm.require({
    message: `Xóa tài liệu "${att.file_name}"?`,
    header: 'Xác nhận xóa',
    icon: 'pi pi-trash',
    rejectLabel: 'Hủy',
    acceptLabel: 'Xóa',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        await employeeService.deleteAttachment(props.employeeId, att.id)
        toast.add({ severity: 'success', summary: 'Đã xóa', life: 2000 })
        await load()
      } catch {
        toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không xóa được tài liệu', life: 3000 })
      }
    },
  })
}

// ── Helpers ───────────────────────────────────────────────────────
function formatSize(bytes: number | null): string {
  if (!bytes) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' })
}

function fileIcon(mime: string | null, name: string): string {
  const m = mime ?? ''
  const ext = name.split('.').pop()?.toLowerCase() ?? ''
  if (m.startsWith('image/')) return '🖼️'
  if (m === 'application/pdf' || ext === 'pdf') return '📄'
  if (['doc', 'docx'].includes(ext)) return '📝'
  return '📎'
}
</script>
