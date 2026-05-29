<template>
  <div class="import-panel">
    <!-- Header + hướng dẫn -->
    <div class="card import-guide-card">
      <div class="import-guide-steps">
        <div class="import-step">
          <span class="import-step-num">1</span>
          <span>Tải file mẫu</span>
        </div>
        <i class="pi pi-arrow-right import-step-arrow" />
        <div class="import-step">
          <span class="import-step-num">2</span>
          <span>Điền dữ liệu vào file</span>
        </div>
        <i class="pi pi-arrow-right import-step-arrow" />
        <div class="import-step">
          <span class="import-step-num">3</span>
          <span>Upload và import</span>
        </div>
      </div>
      <p class="import-description">{{ description }}</p>
      <Button
        label="Tải file mẫu .xlsx"
        icon="pi pi-download"
        severity="secondary"
        outlined
        size="small"
        :loading="downloadingTemplate"
        @click="handleDownload"
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
        <Button
          label="Đổi file"
          severity="secondary"
          size="small"
          text
          @click.stop="fileInput?.click()"
        />
      </template>
      <template v-else>
        <i class="pi pi-upload import-zone-icon" />
        <span class="import-zone-text">Chọn file .xlsx hoặc kéo thả vào đây</span>
        <span class="import-zone-hint">Tối đa 5MB · 1000 dòng/lần</span>
      </template>
    </div>

    <div class="import-actions">
      <Button
        label="Bắt đầu import"
        icon="pi pi-upload"
        :disabled="!selectedFile"
        :loading="uploading"
        @click="doImport"
      />
      <Button
        v-if="selectedFile || result"
        label="Xóa"
        severity="secondary"
        outlined
        @click="reset"
      />
    </div>

    <!-- Result -->
    <div v-if="result" class="card import-result-card">
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
        striped-rows
      >
        <Column field="row" header="Dòng" style="width: 80px" />
        <Column field="column" header="Cột" style="width: 180px" />
        <Column field="message" header="Chi tiết lỗi">
          <template #body="{ data }">
            <span :class="data.message.startsWith('[CẢNH BÁO]') ? 'import-warn-msg' : ''">
              {{ data.message }}
            </span>
          </template>
        </Column>
      </DataTable>

      <p v-else class="import-no-errors">
        <i class="pi pi-check" /> Không có lỗi nào.
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import { useToast } from 'primevue/usetoast'

import type { ImportResult } from '@/services/dataImportService'

const props = defineProps<{
  title: string
  description: string
  downloadTemplate: () => Promise<void>
  uploadFn: (file: File) => Promise<{ data: ImportResult }>
}>()

const toast = useToast()

const fileInput = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)
const isDragging = ref(false)
const uploading = ref(false)
const downloadingTemplate = ref(false)
const result = ref<ImportResult | null>(null)

function reset() {
  selectedFile.value = null
  result.value = null
  isDragging.value = false
  if (fileInput.value) fileInput.value.value = ''
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
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
  if (file?.name.endsWith('.xlsx')) {
    selectedFile.value = file
    result.value = null
  } else {
    toast.add({ severity: 'warn', summary: 'Chỉ chấp nhận file .xlsx', life: 3000 })
  }
}

async function handleDownload() {
  downloadingTemplate.value = true
  try {
    await props.downloadTemplate()
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
    const resp = await props.uploadFn(selectedFile.value)
    result.value = resp.data

    const { success, failed } = resp.data
    if (success > 0) {
      toast.add({
        severity: failed > 0 ? 'warn' : 'success',
        summary: `Import hoàn tất`,
        detail: `${success} dòng thành công` + (failed > 0 ? `, ${failed} dòng lỗi` : ''),
        life: 5000,
      })
    } else {
      toast.add({
        severity: 'error',
        summary: 'Không có dòng nào thành công',
        detail: `${failed} dòng lỗi`,
        life: 5000,
      })
    }
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    toast.add({
      severity: 'error',
      summary: 'Lỗi upload',
      detail: err.response?.data?.detail ?? 'Đã xảy ra lỗi',
      life: 5000,
    })
  } finally {
    uploading.value = false
  }
}
</script>

<style>
.import-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding-top: 0.5rem;
}

.import-guide-card {
  padding: 1rem 1.25rem;
  border: 1px solid var(--l-border);
  background: var(--l-surface);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.import-guide-steps {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.import-step {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  font-weight: 500;
}

.import-step-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 50%;
  background: var(--p-primary-color);
  color: #fff;
  font-size: 0.75rem;
  font-weight: 700;
}

.import-step-arrow {
  color: var(--l-text-muted);
  font-size: 0.75rem;
}

.import-description {
  font-size: 0.85rem;
  color: var(--l-text-muted);
  margin: 0;
}

.import-upload-zone {
  border: 2px dashed var(--l-border);
  border-radius: 0.75rem;
  padding: 2.5rem 1rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
  background: var(--l-surface);
  text-align: center;
}

.import-upload-zone:hover,
.import-upload-zone.is-over {
  border-color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 5%, transparent);
}

.import-upload-zone.has-file {
  border-color: var(--p-primary-color);
}

.import-file-input {
  display: none;
}

.import-zone-icon {
  font-size: 2.5rem;
  color: var(--l-text-muted);
}

.import-zone-icon.has-file {
  color: #22c55e;
}

.import-zone-text {
  font-size: 0.95rem;
  font-weight: 500;
}

.import-zone-filename {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--l-text);
}

.import-zone-size,
.import-zone-hint {
  font-size: 0.8rem;
  color: var(--l-text-muted);
}

.import-actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.import-result-card {
  border: 1px solid var(--l-border);
  background: var(--l-surface);
  padding: 1rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.import-result-summary {
  display: flex;
  gap: 1.5rem;
  flex-wrap: wrap;
}

.import-stat {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.9rem;
}

.import-stat.success { color: #22c55e; }
.import-stat.error   { color: #ef4444; }
.import-stat.muted   { color: var(--l-text-muted); }

.import-error-table {
  font-size: 0.85rem;
}

.import-warn-msg {
  color: #f59e0b;
}

.import-no-errors {
  color: #22c55e;
  font-size: 0.9rem;
  margin: 0;
}

@media (max-width: 640px) {
  .import-guide-steps {
    flex-direction: column;
    align-items: flex-start;
  }
  .import-step-arrow {
    transform: rotate(90deg);
  }
  .import-result-summary {
    flex-direction: column;
    gap: 0.5rem;
  }
}
</style>
