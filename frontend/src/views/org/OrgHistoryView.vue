<template>
  <div>
    <!-- Page header -->
    <div class="page-header">
      <div>
        <h2>Lịch sử thay đổi cơ cấu</h2>
        <span class="subtitle">Ghi nhận toàn bộ thao tác tạo / sửa / xóa cơ cấu tổ chức</span>
      </div>
    </div>

    <!-- Toolbar -->
    <div class="toolbar">
      <Select
        v-model="filterType"
        :options="typeOptions"
        option-label="label"
        option-value="value"
        placeholder="Tất cả loại"
        show-clear
        class="toolbar-filter"
      />
      <DatePicker
        v-model="filterDateFrom"
        placeholder="Từ ngày"
        date-format="dd/mm/yy"
        show-button-bar
        class="toolbar-date"
      />
      <DatePicker
        v-model="filterDateTo"
        placeholder="Đến ngày"
        date-format="dd/mm/yy"
        show-button-bar
        class="toolbar-date"
      />
      <Button label="Lọc" icon="pi pi-filter" @click="loadData" />
      <Button
        icon="pi pi-refresh"
        severity="secondary"
        text rounded
        v-tooltip.top="'Làm mới'"
        :loading="loading"
        @click="resetAndLoad"
      />
    </div>

    <!-- DataTable -->
    <div class="card">
      <DataTable
        :value="list"
        :loading="loading"
        responsive-layout="scroll"
        :paginator="true"
        :rows="pageRows"
        :rows-per-page-options="[25, 50, 100]"
        paginator-template="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink"
        sort-mode="single"
      >
        <template #paginatorstart>
          <span class="paginator-info" v-if="list.length">Tổng {{ list.length }} bản ghi</span>
        </template>
        <template #empty>
          <div class="empty-state">
            <i class="pi pi-history" />
            <span>Không có dữ liệu lịch sử</span>
          </div>
        </template>

        <Column field="changed_at" header="Thời gian" sortable style="width: 160px">
          <template #body="{ data }">{{ formatDate(data.changed_at) }}</template>
        </Column>

        <Column field="entity_label" header="Đối tượng" sortable style="width: 150px">
          <template #body="{ data }">
            <Tag :value="data.entity_label" :severity="entitySeverity(data.entity_type)" />
          </template>
        </Column>

        <Column field="entity_name" header="Tên" sortable style="min-width: 180px" />

        <Column field="action_label" header="Hành động" sortable style="width: 120px">
          <template #body="{ data }">
            <Tag :value="data.action_label" :severity="actionSeverity(data.action)" />
          </template>
        </Column>

        <Column header="Chi tiết" style="width: 80px">
          <template #body="{ data }">
            <Button
              v-if="data.old_data || data.new_data"
              icon="pi pi-eye"
              severity="secondary"
              text rounded
              size="small"
              v-tooltip.top="'Xem chi tiết thay đổi'"
              @click="openDetail(data)"
            />
            <span v-else class="text-muted">—</span>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Detail Dialog -->
    <Dialog
      v-model:visible="detailVisible"
      :header="`Chi tiết: ${detailItem?.entity_label} · ${detailItem?.entity_name}`"
      :style="{ width: '680px' }"
      modal
    >
      <div v-if="detailItem" class="detail-wrap">
        <!-- Header info -->
        <div class="detail-meta">
          <span><strong>Hành động:</strong>
            <Tag :value="detailItem.action_label" :severity="actionSeverity(detailItem.action)" class="ml-2" />
          </span>
          <span><strong>Thời gian:</strong> {{ formatDate(detailItem.changed_at) }}</span>
        </div>

        <!-- Create: chỉ có new_data -->
        <template v-if="detailItem.action === 'create'">
          <p class="diff-subtitle">Dữ liệu được tạo:</p>
          <DataTable :value="newDataRows(detailItem.new_data)" size="small" striped-rows>
            <Column field="field" header="Trường" style="width: 180px; font-weight:600" />
            <Column field="value" header="Giá trị">
              <template #body="{ data }">{{ formatValue(data.value) }}</template>
            </Column>
          </DataTable>
        </template>

        <!-- Delete: chỉ có old_data -->
        <template v-else-if="detailItem.action === 'delete'">
          <p class="diff-subtitle">Dữ liệu bị xóa:</p>
          <DataTable :value="newDataRows(detailItem.old_data)" size="small" striped-rows>
            <Column field="field" header="Trường" style="width: 180px; font-weight:600" />
            <Column field="value" header="Giá trị">
              <template #body="{ data }">{{ formatValue(data.value) }}</template>
            </Column>
          </DataTable>
        </template>

        <!-- Update: so sánh old vs new -->
        <template v-else-if="detailItem.action === 'update'">
          <p class="diff-subtitle">Thay đổi (chỉ hiển thị trường có sự khác biệt):</p>
          <DataTable :value="diffRows(detailItem.old_data, detailItem.new_data)" size="small" striped-rows>
            <Column field="field" header="Trường" style="width: 160px; font-weight:600" />
            <Column field="old_val" header="Trước">
              <template #body="{ data }">
                <span :class="data.changed ? 'val-old' : ''">{{ formatValue(data.old_val) }}</span>
              </template>
            </Column>
            <Column field="new_val" header="Sau">
              <template #body="{ data }">
                <span :class="data.changed ? 'val-new' : ''">{{ formatValue(data.new_val) }}</span>
              </template>
            </Column>
          </DataTable>
        </template>
      </div>

      <template #footer>
        <Button label="Đóng" severity="secondary" outlined @click="detailVisible = false" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import Select from 'primevue/select'
import Tag from 'primevue/tag'

import orgHistoryService, { type OrgHistoryItem } from '@/services/orgHistoryService'

// ── State ──────────────────────────────────────────────────────────────────────

const toast       = useToast()
const loading     = ref(false)
const list        = ref<OrgHistoryItem[]>([])
const pageRows    = ref(25)

const filterType     = ref<string | null>(null)
const filterDateFrom = ref<Date | null>(null)
const filterDateTo   = ref<Date | null>(null)

const detailVisible = ref(false)
const detailItem    = ref<OrgHistoryItem | null>(null)

// ── Options ────────────────────────────────────────────────────────────────────

const typeOptions = [
  { label: 'Phòng/Ban',        value: 'department'   },
  { label: 'Chức danh',        value: 'job_title'    },
  { label: 'Vị trí công việc', value: 'job_position' },
]

// ── Data ───────────────────────────────────────────────────────────────────────

async function loadData() {
  loading.value = true
  try {
    const { data } = await orgHistoryService.getList({
      entity_type: filterType.value ?? undefined,
      date_from:   filterDateFrom.value ? toISODate(filterDateFrom.value) : undefined,
      date_to:     filterDateTo.value   ? toISODate(filterDateTo.value)   : undefined,
      limit:       1000,
    })
    list.value = data
  } catch (e) {
    const err = e as { response?: { data?: { detail?: string } } }
    toast.add({ severity: 'error', summary: 'Lỗi', detail: err.response?.data?.detail ?? 'Không thể tải dữ liệu', life: 4000 })
  } finally {
    loading.value = false
  }
}

function resetAndLoad() {
  filterType.value     = null
  filterDateFrom.value = null
  filterDateTo.value   = null
  loadData()
}

// ── Detail dialog ──────────────────────────────────────────────────────────────

function openDetail(item: OrgHistoryItem) {
  detailItem.value   = item
  detailVisible.value = true
}

function newDataRows(data: Record<string, unknown> | null) {
  if (!data) return []
  return Object.entries(data).map(([field, value]) => ({ field, value }))
}

function diffRows(
  old_data: Record<string, unknown> | null,
  new_data: Record<string, unknown> | null,
) {
  const allKeys = new Set([
    ...Object.keys(old_data ?? {}),
    ...Object.keys(new_data ?? {}),
  ])
  return Array.from(allKeys).map(field => {
    const old_val = old_data?.[field] ?? null
    const new_val = new_data?.[field] ?? null
    return {
      field,
      old_val,
      new_val,
      changed: JSON.stringify(old_val) !== JSON.stringify(new_val),
    }
  }).filter(r => r.changed)  // chỉ hiện dòng có thay đổi
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function toISODate(d: Date): string {
  return d.toISOString().slice(0, 10)
}

function formatDate(iso: string): string {
  return new Intl.DateTimeFormat('vi-VN', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  }).format(new Date(iso))
}

function formatValue(val: unknown): string {
  if (val === null || val === undefined) return '—'
  if (typeof val === 'boolean') return val ? 'Có' : 'Không'
  return String(val)
}

function entitySeverity(type: string): string {
  return { department: 'info', job_title: 'warn', job_position: 'secondary' }[type] ?? 'secondary'
}

function actionSeverity(action: string): string {
  return { create: 'success', update: 'warn', delete: 'danger' }[action] ?? 'secondary'
}

onMounted(loadData)
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.25rem;
  h2 { margin: 0 0 0.2rem; font-size: 1.5rem; font-weight: 700; }
  .subtitle { color: var(--p-text-muted-color); font-size: 0.875rem; }
}

.toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.toolbar-filter { min-width: 180px; }
.toolbar-date   { min-width: 150px; }

.card {
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 10px;
  overflow: hidden;
}

.empty-state {
  display: flex; flex-direction: column; align-items: center;
  gap: 0.5rem; padding: 3rem; color: var(--p-text-muted-color);
  i { font-size: 2rem; opacity: 0.3; }
}

.paginator-info { font-size: 0.875rem; color: var(--p-text-muted-color); }
.text-muted     { color: var(--p-text-muted-color); }
.ml-2           { margin-left: 0.5rem; }

/* Detail dialog */
.detail-wrap    { display: flex; flex-direction: column; gap: 1rem; }
.detail-meta    { display: flex; gap: 1.5rem; flex-wrap: wrap; font-size: 0.9rem; }
.diff-subtitle  { margin: 0; font-size: 0.875rem; color: var(--p-text-muted-color); font-weight: 500; }

.val-old { color: var(--p-red-500);   text-decoration: line-through; font-size: 0.875rem; }
.val-new { color: var(--p-green-600); font-weight: 600; font-size: 0.875rem; }
</style>
