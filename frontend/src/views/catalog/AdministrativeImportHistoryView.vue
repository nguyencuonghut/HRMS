<template>
  <div class="page-shell">
    <div class="page-header">
      <div>
        <h2>Lịch sử import địa chỉ</h2>
        <span class="subtitle">Theo dõi trạng thái các batch đồng bộ dữ liệu hành chính</span>
      </div>
      <div class="header-actions">
        <Button
          label="Quản trị danh mục"
          icon="pi pi-arrow-left"
          severity="secondary"
          outlined
          @click="router.push('/catalog/administrative-units')"
        />
        <Button
          v-can:edit="'catalog'"
          label="Import lại"
          icon="pi pi-download"
          :loading="importing"
          @click="runImport"
        />
      </div>
    </div>

    <div class="toolbar">
      <Button
        icon="pi pi-refresh"
        severity="secondary"
        text
        rounded
        :loading="loading"
        v-tooltip.top="'Làm mới'"
        @click="loadBatches"
      />
    </div>

    <div class="card">
      <DataTable
        :value="batches"
        :loading="loading"
        stripedRows
        paginator
        paginator-template="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
        current-page-report-template="Hiển thị từ {first} đến {last} trên tổng số {totalRecords} dòng"
        :rows="10"
        responsive-layout="scroll"
      >
        <template #empty>
          <div class="empty-state">
            <i class="pi pi-inbox" />
            <span>Chưa có batch import nào</span>
          </div>
        </template>

        <Column field="id" header="#" style="width: 90px" />
        <Column field="source_name" header="Nguồn" style="min-width: 160px" />
        <Column field="source_version" header="Phiên bản" style="width: 130px" />
        <Column field="file_name" header="Tên file" style="min-width: 220px" />
        <Column field="status" header="Trạng thái" style="width: 120px">
          <template #body="{ data }">
            <Tag
              :value="statusLabel(data.status)"
              :severity="data.status === 'success' ? 'success' : data.status === 'failed' ? 'danger' : 'warning'"
            />
          </template>
        </Column>
        <Column header="Kết quả" style="min-width: 200px">
          <template #body="{ data }">
            <div class="batch-stats">
              <span>Tổng: {{ data.total_rows }}</span>
              <span>OK: {{ data.success_rows }}</span>
              <span>Lỗi: {{ data.failed_rows }}</span>
            </div>
          </template>
        </Column>
        <Column header="Thời gian" style="min-width: 180px">
          <template #body="{ data }">{{ formatDateTime(data.imported_at) }}</template>
        </Column>
        <Column header="Ghi chú lỗi" style="min-width: 280px">
          <template #body="{ data }">
            <span class="error-summary">{{ data.error_summary || '—' }}</span>
          </template>
        </Column>
      </DataTable>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'

import administrativeUnitService, { type AdministrativeImportBatchRead } from '@/services/administrativeUnitService'

const router = useRouter()
const toast = useToast()

const loading = ref(false)
const importing = ref(false)
const batches = ref<AdministrativeImportBatchRead[]>([])

function apiError(e: unknown): string {
  const err = e as { response?: { data?: { detail?: unknown } } }
  const detail = err.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((d: { msg: string }) => d.msg).join('; ')
  return typeof detail === 'string' ? detail : 'Đã xảy ra lỗi, vui lòng thử lại'
}

function statusLabel(status: string) {
  if (status === 'success') return 'Thành công'
  if (status === 'failed') return 'Thất bại'
  return 'Đang xử lý'
}

function formatDateTime(value: string) {
  return new Date(value).toLocaleString('vi-VN')
}

async function loadBatches() {
  loading.value = true
  try {
    const res = await administrativeUnitService.listImportBatches()
    batches.value = res.data
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 })
  } finally {
    loading.value = false
  }
}

async function runImport() {
  importing.value = true
  try {
    const res = await administrativeUnitService.importData({
      system_type: 'new',
      source_name: 'official_import',
      source_version: 'qd19_2025',
      mode: 'merge',
    })
    toast.add({
      severity: res.data.failed_rows > 0 ? 'warn' : 'success',
      summary: 'Import hoàn tất',
      detail: `Tổng ${res.data.total_rows}, OK ${res.data.success_rows}, lỗi ${res.data.failed_rows}`,
      life: 4500,
    })
    await loadBatches()
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
  } finally {
    importing.value = false
  }
}

onMounted(loadBatches)
</script>

<style scoped>
.page-shell { display: flex; flex-direction: column; gap: 1rem; }
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}
.page-header h2 { margin: 0; font-size: 1.6rem; font-weight: 700; }
.subtitle { color: var(--p-text-muted-color); }
.header-actions { display: flex; gap: 0.75rem; flex-wrap: wrap; }
.toolbar { display: flex; justify-content: flex-end; }
.batch-stats { display: flex; gap: 0.85rem; flex-wrap: wrap; font-size: 0.92rem; }
.error-summary { color: var(--p-text-muted-color); line-height: 1.45; }
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 2rem 0;
  color: var(--p-text-muted-color);
}
@media (max-width: 768px) {
  .page-header { flex-direction: column; }
}
</style>
