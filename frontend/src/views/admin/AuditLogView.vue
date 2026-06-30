<template>
  <div>
    <!-- Page header -->
    <div class="page-header">
      <div>
        <h2>Nhật ký hệ thống</h2>
        <span class="subtitle">Lịch sử thao tác toàn hệ thống</span>
      </div>
    </div>

    <!-- Toolbar -->
    <div class="toolbar">
      <Select
        v-model="filterAction"
        :options="actionOptions"
        option-label="label"
        option-value="code"
        placeholder="Tất cả hành động"
        show-clear
        filter
        class="toolbar-filter"
      />
      <Select
        v-model="filterEntityType"
        :options="entityTypeOptions"
        option-label="label"
        option-value="code"
        placeholder="Tất cả đối tượng"
        show-clear
        filter
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
      <IconField class="toolbar-search">
        <InputIcon class="pi pi-search" />
        <InputText
          v-model="filterKeyword"
          placeholder="Tên, email, IP..."
          class="w-full"
          @keyup.enter="applyFilter"
        />
      </IconField>
      <Button label="Lọc" icon="pi pi-filter" @click="applyFilter" />
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
        lazy
        :total-records="total"
        responsive-layout="scroll"
        :paginator="true"
        :rows="pageSize"
        :rows-per-page-options="[10, 25, 50]"
        :first="(page - 1) * pageSize"
        paginator-template="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
        current-page-report-template="Hiển thị từ {first} đến {last} trên tổng số {totalRecords} dòng"
        sort-mode="single"
        @page="handlePage"
      >
        <template #empty>
          <div class="empty-state">
            <i class="pi pi-history" />
            <span>Không có dữ liệu</span>
          </div>
        </template>

        <Column field="created_at" header="Thời gian" sortable style="width: 160px">
          <template #body="{ data }">{{ formatDate(data.created_at) }}</template>
        </Column>

        <Column field="user_name" header="Người thực hiện" sortable style="min-width: 160px">
          <template #body="{ data }">
            <div v-if="data.user_name">
              <div style="font-weight: 500;">{{ data.user_name }}</div>
              <div class="muted-text" style="font-size: 0.78rem;">{{ data.user_email }}</div>
            </div>
            <span v-else class="muted-text">Hệ thống</span>
          </template>
        </Column>

        <Column field="action" header="Hành động" sortable style="width: 140px">
          <template #body="{ data }">
            <Tag :value="data.action_label" :severity="data.action_severity" />
          </template>
        </Column>

        <Column field="entity_type" header="Đối tượng" sortable style="min-width: 180px">
          <template #body="{ data }">
            <div v-if="data.entity_type">
              <Tag :value="data.entity_type_label || data.entity_type" :severity="data.entity_type_severity || 'secondary'" />
              <span v-if="data.entity_name" class="muted-text" style="margin-left: 0.5rem;">{{ data.entity_name }}</span>
            </div>
            <span v-else class="muted-text">—</span>
          </template>
        </Column>

        <Column header="Chi tiết" style="width: 80px">
          <template #body="{ data }">
            <Button
              v-if="data.old_data || data.new_data"
              icon="pi pi-eye"
              severity="secondary"
              text rounded size="small"
              v-tooltip.top="'Xem chi tiết'"
              @click="openDetail(data)"
            />
            <span v-else class="muted-text">—</span>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Detail Dialog -->
    <Dialog
      v-model:visible="detailVisible"
      :header="`Chi tiết: ${detailItem?.action} — ${detailItem?.entity_name ?? detailItem?.entity_type ?? ''}`"
      :style="{ width: '680px' }"
      modal
    >
      <div v-if="detailItem" class="detail-wrap">
        <div class="detail-meta">
          <span><strong>Hành động:</strong>
            <Tag :value="detailItem.action_label" :severity="detailItem.action_severity" class="ml-2" />
          </span>
          <span><strong>Thời gian:</strong> {{ formatDate(detailItem.created_at) }}</span>
          <span v-if="detailItem.user_name"><strong>Người thực hiện:</strong> {{ detailItem.user_name }}</span>
          <span v-if="detailItem.ip_address"><strong>IP:</strong> {{ detailItem.ip_address }}</span>
        </div>

        <!-- Create -->
        <template v-if="detailItem.action === 'CREATE' && detailItem.new_data">
          <p class="diff-subtitle">Dữ liệu được tạo:</p>
          <DataTable :value="dataRows(detailItem.new_data)" size="small" striped-rows>
            <Column field="field" header="Trường" style="width: 180px; font-weight:600" />
            <Column field="value" header="Giá trị">
              <template #body="{ data }">{{ formatValue(data.value) }}</template>
            </Column>
          </DataTable>
        </template>

        <!-- Delete -->
        <template v-else-if="detailItem.action === 'DELETE' && detailItem.old_data">
          <p class="diff-subtitle">Dữ liệu bị xóa:</p>
          <DataTable :value="dataRows(detailItem.old_data)" size="small" striped-rows>
            <Column field="field" header="Trường" style="width: 180px; font-weight:600" />
            <Column field="value" header="Giá trị">
              <template #body="{ data }">{{ formatValue(data.value) }}</template>
            </Column>
          </DataTable>
        </template>

        <!-- Update -->
        <template v-else-if="detailItem.action === 'UPDATE'">
          <p class="diff-subtitle">Thay đổi (chỉ hiển thị trường có sự khác biệt):</p>
          <DataTable :value="diffRows(detailItem.old_data, detailItem.new_data)" size="small" striped-rows>
            <Column field="field" header="Trường" style="width: 160px; font-weight:600" />
            <Column field="old_val" header="Trước">
              <template #body="{ data }">
                <span class="val-old">{{ formatValue(data.old_val) }}</span>
              </template>
            </Column>
            <Column field="new_val" header="Sau">
              <template #body="{ data }">
                <span class="val-new">{{ formatValue(data.new_val) }}</span>
              </template>
            </Column>
          </DataTable>
        </template>

        <!-- Other actions (LOGIN, EXPORT, ...) -->
        <template v-else>
          <p class="diff-subtitle">Không có dữ liệu chi tiết cho hành động này.</p>
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
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'

import auditLogService, {
  type AuditActionOption,
  type AuditEntityTypeOption,
  type AuditLogItem,
} from '@/services/auditLogService'
import { toLocalIso } from '@/utils/format'

const toast    = useToast()
const loading  = ref(false)
const list     = ref<AuditLogItem[]>([])
const total    = ref(0)
const page     = ref(1)
const pageSize = ref(20)

function handlePage(e: { first: number; rows: number }) {
  page.value     = Math.floor(e.first / e.rows) + 1
  pageSize.value = e.rows
  loadData()
}

const filterAction     = ref<string | null>(null)
const filterEntityType = ref<string | null>(null)
const filterDateFrom   = ref<Date | null>(null)
const filterDateTo     = ref<Date | null>(null)
const filterKeyword    = ref('')

const detailVisible = ref(false)
const detailItem    = ref<AuditLogItem | null>(null)

const actionOptions = ref<AuditActionOption[]>([])
const entityTypeOptions = ref<AuditEntityTypeOption[]>([])

async function loadData(resetPage = false) {
  if (resetPage) page.value = 1
  loading.value = true
  try {
    const { data } = await auditLogService.getList({
      action:      filterAction.value ?? undefined,
      entity_type: filterEntityType.value ?? undefined,
      date_from:   filterDateFrom.value ? toISODate(filterDateFrom.value) : undefined,
      date_to:     filterDateTo.value   ? toISODate(filterDateTo.value)   : undefined,
      keyword:     filterKeyword.value?.trim() || undefined,
      page:        page.value,
      page_size:   pageSize.value,
    })
    list.value  = data.items
    total.value = data.total
  } catch (e) {
    const err = e as { response?: { data?: { detail?: string } } }
    toast.add({ severity: 'error', summary: 'Lỗi', detail: err.response?.data?.detail ?? 'Không thể tải dữ liệu', life: 4000 })
  } finally {
    loading.value = false
  }
}

async function loadMeta() {
  const { data } = await auditLogService.getMeta()
  actionOptions.value = [...data.actions].sort((a, b) => a.order - b.order)
  entityTypeOptions.value = [...data.entity_types].sort((a, b) => a.order - b.order)
}

function applyFilter() { loadData(true) }

function resetAndLoad() {
  filterAction.value   = null
  filterEntityType.value = null
  filterDateFrom.value = null
  filterDateTo.value   = null
  filterKeyword.value  = ''
  loadData(true)
}

function openDetail(item: AuditLogItem) {
  detailItem.value    = item
  detailVisible.value = true
}

function dataRows(data: Record<string, unknown> | null) {
  if (!data) return []
  return Object.entries(data).map(([field, value]) => ({ field, value }))
}

function diffRows(
  old_data: Record<string, unknown> | null,
  new_data: Record<string, unknown> | null,
) {
  const allKeys = new Set([...Object.keys(old_data ?? {}), ...Object.keys(new_data ?? {})])
  return Array.from(allKeys)
    .map(field => ({
      field,
      old_val: old_data?.[field] ?? null,
      new_val: new_data?.[field] ?? null,
    }))
    .filter(r => JSON.stringify(r.old_val) !== JSON.stringify(r.new_val))
}

function toISODate(d: Date): string {
  return toLocalIso(d)
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

onMounted(async () => {
  await loadMeta()
  await loadData()
})
</script>

<style scoped>
.detail-wrap  { display: flex; flex-direction: column; gap: 1rem; }
.detail-meta  { display: flex; gap: 1.5rem; flex-wrap: wrap; font-size: 0.9rem; }
.diff-subtitle { margin: 0; font-size: 0.875rem; color: var(--p-text-muted-color); font-weight: 500; }
.ml-2         { margin-left: 0.5rem; }

.val-old { color: var(--p-red-500);   text-decoration: line-through; font-size: 0.875rem; }
.val-new { color: var(--p-green-600); font-weight: 600; font-size: 0.875rem; }
</style>
