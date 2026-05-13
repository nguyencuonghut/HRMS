<template>
  <div class="file-attachment-list">
    <!-- Upload area -->
    <div class="mb-3">
      <FileUpload
        mode="basic"
        :auto="true"
        :custom-upload="true"
        choose-label="Chọn file để upload"
        :disabled="uploading"
        @uploader="handleUpload"
      />
    </div>

    <!-- File list -->
    <div v-if="loading" class="flex align-items-center gap-2 text-color-secondary">
      <i class="pi pi-spin pi-spinner" />
      <span>Đang tải...</span>
    </div>

    <div v-else-if="attachments.length === 0" class="text-color-secondary text-sm">
      Chưa có file đính kèm.
    </div>

    <DataTable
      v-else
      :value="attachments"
      size="small"
      :show-gridlines="false"
      striped-rows
    >
      <Column header="Tên file" style="min-width: 200px">
        <template #body="{ data }">
          <a
            :href="data.download_url"
            target="_blank"
            rel="noopener noreferrer"
            class="flex align-items-center gap-2 text-primary no-underline hover:underline"
          >
            <i :class="fileIcon(data.file_name)" />
            {{ data.file_name }}
          </a>
        </template>
      </Column>

      <Column header="Kích thước" style="width: 110px">
        <template #body="{ data }">
          {{ formatSize(data.file_size) }}
        </template>
      </Column>

      <Column header="Ngày upload" style="width: 160px">
        <template #body="{ data }">
          {{ formatDate(data.uploaded_at) }}
        </template>
      </Column>

      <Column header="" style="width: 60px">
        <template #body="{ data }">
          <Button
            icon="pi pi-trash"
            severity="danger"
            text
            rounded
            size="small"
            @click="confirmDelete(data)"
          />
        </template>
      </Column>
    </DataTable>
  </div>

  <ConfirmDialog />
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import axios from 'axios'
import Button from 'primevue/button'
import Column from 'primevue/column'
import ConfirmDialog from 'primevue/confirmdialog'
import DataTable from 'primevue/datatable'
import FileUpload, { type FileUploadUploaderEvent } from 'primevue/fileupload'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'

interface Attachment {
  id:           number
  file_name:    string
  file_path:    string
  file_size:    number | null
  uploaded_at:  string
  download_url: string   // presigned URL từ MinIO, hết hạn sau 1h
}

const props = defineProps<{ positionId: number | null }>()
const emit  = defineEmits<{ (e: 'change'): void }>()

const confirm    = useConfirm()
const toast      = useToast()
const attachments = ref<Attachment[]>([])
const loading    = ref(false)
const uploading  = ref(false)

async function fetchAttachments() {
  if (!props.positionId) { attachments.value = []; return }
  loading.value = true
  try {
    const { data } = await axios.get<Attachment[]>(
      `/api/v1/job-positions/${props.positionId}/attachments`
    )
    attachments.value = data
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể tải danh sách file', life: 3000 })
  } finally {
    loading.value = false
  }
}

async function handleUpload(event: FileUploadUploaderEvent) {
  const files = Array.isArray(event.files) ? event.files : [event.files]
  const file = files[0]
  if (!file || !props.positionId) return
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    await axios.post(`/api/v1/job-positions/${props.positionId}/attachments`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    toast.add({ severity: 'success', summary: 'Thành công', detail: `Đã upload "${file.name}"`, life: 3000 })
    await fetchAttachments()
    emit('change')
  } catch (err: any) {
    const detail = err.response?.data?.detail ?? 'Upload thất bại'
    toast.add({ severity: 'error', summary: 'Lỗi', detail, life: 4000 })
  } finally {
    uploading.value = false
  }
}

function confirmDelete(att: Attachment) {
  confirm.require({
    message: `Xóa file "${att.file_name}"?`,
    header:  'Xác nhận xóa',
    icon:    'pi pi-exclamation-triangle',
    acceptLabel: 'Xóa',
    rejectLabel: 'Hủy',
    accept: () => doDelete(att),
  })
}

async function doDelete(att: Attachment) {
  try {
    await axios.delete(`/api/v1/job-positions/${props.positionId}/attachments/${att.id}`)
    toast.add({ severity: 'success', summary: 'Đã xóa', detail: att.file_name, life: 3000 })
    await fetchAttachments()
    emit('change')
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể xóa file', life: 3000 })
  }
}

function fileIcon(name: string): string {
  const ext = name.split('.').pop()?.toLowerCase() ?? ''
  if (['pdf'].includes(ext))               return 'pi pi-file-pdf text-red-500'
  if (['doc', 'docx'].includes(ext))       return 'pi pi-file-word text-blue-500'
  if (['xls', 'xlsx'].includes(ext))       return 'pi pi-file-excel text-green-500'
  if (['png', 'jpg', 'jpeg'].includes(ext)) return 'pi pi-image text-purple-500'
  return 'pi pi-file'
}

function formatSize(bytes: number | null): string {
  if (!bytes) return '—'
  if (bytes < 1024)       return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function formatDate(iso: string): string {
  return new Intl.DateTimeFormat('vi-VN', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  }).format(new Date(iso))
}

watch(() => props.positionId, fetchAttachments, { immediate: true })
</script>
