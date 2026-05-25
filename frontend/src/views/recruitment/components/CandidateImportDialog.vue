<template>
  <Dialog
    v-model:visible="visible"
    header="Import ứng viên từ Excel"
    modal
    :style="{ width: '680px' }"
    @hide="reset"
  >
    <div class="import-template-row">
      <span class="import-template-hint">Chưa có file mẫu?</span>
      <Button
        label="Tải file mẫu .xlsx"
        icon="pi pi-download"
        severity="secondary"
        size="small"
        :loading="downloadingTemplate"
        @click="downloadTemplate"
      />
    </div>

    <div
      class="import-upload-zone"
      :class="{ 'is-over': isDragging, 'has-file': !!selectedFile }"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="onDrop"
      @click="fileInput?.click()"
    >
      <input
        ref="fileInput"
        type="file"
        accept=".xlsx"
        class="import-file-input"
        @change="onFileChange"
      />
      <template v-if="selectedFile">
        <i class="pi pi-file-excel import-zone-icon has-file" />
        <span class="import-zone-filename">{{ selectedFile.name }}</span>
        <span class="import-zone-size">{{ formatSize(selectedFile.size) }}</span>
      </template>
      <template v-else>
        <i class="pi pi-upload import-zone-icon" />
        <span class="import-zone-text">Chọn file .xlsx hoặc kéo thả vào đây</span>
      </template>
    </div>

    <div v-if="result" class="import-result">
      <div class="import-result-summary">
        <div class="import-stat success">
          <i class="pi pi-plus-circle" />
          <span>Tạo mới: <strong>{{ result.created }}</strong></span>
        </div>
        <div class="import-stat info">
          <i class="pi pi-sync" />
          <span>Cập nhật: <strong>{{ result.updated }}</strong></span>
        </div>
        <div class="import-stat muted">
          <i class="pi pi-forward" />
          <span>Bỏ qua: <strong>{{ result.skipped }}</strong></span>
        </div>
        <div class="import-stat" :class="result.errors.length > 0 ? 'error' : 'muted'">
          <i class="pi pi-times-circle" />
          <span>Lỗi: <strong>{{ result.errors.length }}</strong></span>
        </div>
      </div>

      <DataTable
        v-if="result.errors.length > 0"
        :value="errorRows"
        size="small"
        class="import-error-table"
        :rows="10"
        paginator
        paginator-template="PrevPageLink PageLinks NextPageLink"
      >
        <Column field="line" header="#" style="width: 70px" />
        <Column field="message" header="Chi tiết lỗi" />
      </DataTable>
    </div>

    <template #footer>
      <Button label="Đóng" severity="secondary" outlined @click="visible = false" />
      <Button
        label="Tải lên & Import"
        icon="pi pi-upload"
        :disabled="!selectedFile"
        :loading="uploading"
        @click="doImport"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import { useToast } from 'primevue/usetoast'

import recruitmentService, { type ImportResult } from '@/services/recruitmentService'

const emit = defineEmits<{ (e: 'imported', result: ImportResult): void }>()

const toast = useToast()

const visible = defineModel<boolean>('visible', { default: false })
const fileInput = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)
const isDragging = ref(false)
const uploading = ref(false)
const downloadingTemplate = ref(false)
const result = ref<ImportResult | null>(null)

const errorRows = computed(() =>
  (result.value?.errors ?? []).map((message, index) => ({
    line: index + 1,
    message,
  })),
)

function reset() {
  selectedFile.value = null
  isDragging.value = false
  result.value = null
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files?.[0]) {
    selectedFile.value = input.files[0]
    result.value = null
  }
}

function onDrop(event: DragEvent) {
  isDragging.value = false
  const file = event.dataTransfer?.files?.[0]
  if (!file) return

  if (!file.name.toLowerCase().endsWith('.xlsx')) {
    toast.add({ severity: 'warn', summary: 'Chỉ chấp nhận file .xlsx', life: 3000 })
    return
  }

  selectedFile.value = file
  result.value = null
}

async function downloadTemplate() {
  downloadingTemplate.value = true
  try {
    const response = await recruitmentService.downloadImportTemplate()
    const blob = new Blob([response.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'candidate_import_template.xlsx'
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  } catch {
    toast.add({ severity: 'error', summary: 'Không tải được file mẫu', life: 4000 })
  } finally {
    downloadingTemplate.value = false
  }
}

async function doImport() {
  if (!selectedFile.value) return

  uploading.value = true
  result.value = null
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)

    const response = await recruitmentService.importCandidates(formData)
    result.value = response.data

    const successCount = response.data.created + response.data.updated
    if (successCount > 0) {
      toast.add({
        severity: 'success',
        summary: 'Import thành công',
        detail: `Tạo ${response.data.created}, cập nhật ${response.data.updated}, bỏ qua ${response.data.skipped}`,
        life: 5000,
      })
      emit('imported', response.data)
    } else {
      toast.add({
        severity: 'warn',
        summary: 'Không có dòng nào được import',
        detail: `Bỏ qua ${response.data.skipped}, lỗi ${response.data.errors.length}`,
        life: 5000,
      })
    }
  } catch (error: unknown) {
    const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    toast.add({
      severity: 'error',
      summary: 'Lỗi upload',
      detail: typeof detail === 'string' ? detail : 'Đã xảy ra lỗi khi import',
      life: 5000,
    })
  } finally {
    uploading.value = false
  }
}
</script>
