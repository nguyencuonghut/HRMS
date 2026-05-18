<template>
  <Dialog
    v-model:visible="visible"
    header="Import nhân viên từ Excel"
    modal
    :style="{ width: '680px' }"
    @hide="reset"
  >
    <!-- Template download -->
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

    <!-- Upload zone -->
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

    <!-- Result -->
    <div v-if="result" class="import-result">
      <div class="import-result-summary">
        <div class="import-stat success">
          <i class="pi pi-check-circle" />
          <span>Thành công: <strong>{{ result.success }}</strong></span>
        </div>
        <div class="import-stat" :class="result.failed > 0 ? 'error' : 'muted'">
          <i class="pi pi-times-circle" />
          <span>Lỗi: <strong>{{ result.failed }}</strong></span>
        </div>
        <div class="import-stat muted">
          <i class="pi pi-list" />
          <span>Tổng: <strong>{{ result.total }}</strong></span>
        </div>
      </div>

      <DataTable
        v-if="result.errors.length > 0"
        :value="result.errors"
        size="small"
        class="import-error-table"
        :rows="10"
        paginator
        paginator-template="PrevPageLink PageLinks NextPageLink"
      >
        <Column field="row" header="Dòng" style="width:70px" />
        <Column field="column" header="Cột" style="width:160px" />
        <Column field="message" header="Lỗi" />
      </DataTable>
    </div>

    <template #footer>
      <Button label="Hủy" severity="secondary" outlined @click="visible = false" />
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
import { ref } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import { useToast } from 'primevue/usetoast'

import employeeService, { type ImportResult } from '@/services/employeeService'

const emit = defineEmits<{ imported: [result: ImportResult] }>()

const toast = useToast()

const visible            = defineModel<boolean>({ default: false })
const fileInput          = ref<HTMLInputElement | null>(null)
const selectedFile       = ref<File | null>(null)
const isDragging         = ref(false)
const uploading          = ref(false)
const downloadingTemplate = ref(false)
const result             = ref<ImportResult | null>(null)

function reset() {
  selectedFile.value = null
  result.value       = null
  isDragging.value   = false
}

function formatSize(bytes: number): string {
  if (bytes < 1024)       return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.[0]) {
    selectedFile.value = input.files[0]
    result.value = null
  }
}

function onDrop(e: DragEvent) {
  isDragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file && file.name.endsWith('.xlsx')) {
    selectedFile.value = file
    result.value = null
  } else {
    toast.add({ severity: 'warn', summary: 'Chỉ chấp nhận file .xlsx', life: 3000 })
  }
}

async function downloadTemplate() {
  downloadingTemplate.value = true
  try {
    await employeeService.downloadImportTemplate()
  } catch {
    toast.add({ severity: 'error', summary: 'Không tải được file mẫu', life: 4000 })
  } finally {
    downloadingTemplate.value = false
  }
}

async function doImport() {
  if (!selectedFile.value) return
  uploading.value = true
  result.value    = null
  try {
    const fd = new FormData()
    fd.append('file', selectedFile.value)
    const resp = await employeeService.importEmployees(fd)
    result.value = resp.data
    if (resp.data.success > 0) {
      toast.add({
        severity: 'success',
        summary: 'Import thành công',
        detail: `Đã tạo ${resp.data.success} nhân viên` + (resp.data.failed > 0 ? `, ${resp.data.failed} dòng lỗi` : ''),
        life: 5000,
      })
      emit('imported', resp.data)
    } else {
      toast.add({ severity: 'warn', summary: 'Không có dòng nào thành công', detail: `${resp.data.failed} dòng lỗi`, life: 5000 })
    }
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    toast.add({ severity: 'error', summary: 'Lỗi upload', detail: err.response?.data?.detail ?? 'Đã xảy ra lỗi', life: 5000 })
  } finally {
    uploading.value = false
  }
}
</script>
