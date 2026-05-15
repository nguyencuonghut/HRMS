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
        option-value="value"
        placeholder="Tất cả hành động"
        show-clear
        filter
        class="toolbar-filter"
      />
      <Select
        v-model="filterEntityType"
        :options="entityTypeOptions"
        option-label="label"
        option-value="value"
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
          v-model="filters.global.value"
          placeholder="Tìm kiếm..."
          class="w-full"
          @input="first = 0"
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
        v-model:filters="filters"
        :global-filter-fields="['user_name', 'user_email', 'action', 'entity_type', 'entity_name', 'ip_address']"
        responsive-layout="scroll"
        :paginator="true"
        :rows="pageRows"
        :rows-per-page-options="[10, 25, 50]"
        :first="first"
        paginator-template="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink"
        sort-mode="single"
        @page="handlePage"
      >
        <template #paginatorstart>
          <span class="paginator-info" v-if="displayedTotal > 0">
            Hiển thị {{ first + 1 }}–{{ Math.min(first + pageRows, displayedTotal) }} trên tổng số {{ displayedTotal }} dòng
          </span>
        </template>
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
            <Tag :value="actionLabel(data.action)" :severity="actionSeverity(data.action)" />
          </template>
        </Column>

        <Column field="entity_type" header="Đối tượng" sortable style="min-width: 180px">
          <template #body="{ data }">
            <div v-if="data.entity_type">
              <Tag :value="entityLabel(data.entity_type)" :severity="entitySeverity(data.entity_type)" />
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
            <Tag :value="actionLabel(detailItem.action)" :severity="actionSeverity(detailItem.action)" class="ml-2" />
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
import { ref, computed, watch, onMounted } from 'vue'
import { FilterMatchMode } from '@primevue/core/api'
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

import auditLogService, { type AuditLogItem } from '@/services/auditLogService'

const toast    = useToast()
const loading  = ref(false)
const list     = ref<AuditLogItem[]>([])
const pageRows = ref(10)
const first    = ref(0)

const filters = ref({ global: { value: null as string | null, matchMode: FilterMatchMode.CONTAINS } })

const FILTER_FIELDS = ['user_name', 'user_email', 'action', 'entity_type', 'entity_name', 'ip_address'] as const

const displayedTotal = computed(() => {
  const q = filters.value.global.value?.trim().toLowerCase()
  if (!q) return list.value.length
  return list.value.filter(item =>
    FILTER_FIELDS.some(f => String(item[f] ?? '').toLowerCase().includes(q))
  ).length
})

watch(() => filters.value.global.value, () => { first.value = 0 })

function handlePage(e: { first: number; rows: number }) {
  first.value    = e.first
  pageRows.value = e.rows
}

const filterAction     = ref<string | null>(null)
const filterEntityType = ref<string | null>(null)
const filterDateFrom   = ref<Date | null>(null)
const filterDateTo     = ref<Date | null>(null)

const detailVisible = ref(false)
const detailItem    = ref<AuditLogItem | null>(null)

const actionOptions = [
  { label: 'Đăng nhập',    value: 'LOGIN' },
  { label: 'Tạo mới',      value: 'CREATE' },
  { label: 'Cập nhật',     value: 'UPDATE' },
  { label: 'Xóa',          value: 'DELETE' },
  { label: 'Xuất dữ liệu', value: 'EXPORT' },
  { label: 'Đặt lại MK',   value: 'RESET_PASSWORD' },
]

const entityTypeOptions = [
  { label: 'Người dùng',    value: 'user' },
  { label: 'Phân quyền',    value: 'user_role' },
  { label: 'Vai trò',       value: 'role' },
  { label: 'Quyền vai trò', value: 'role_permissions' },
  { label: 'Phòng/Ban',     value: 'department' },
  { label: 'Chức danh',     value: 'job_title' },
  { label: 'Vị trí',        value: 'job_position' },
  { label: 'Nhân viên',     value: 'employee' },
  { label: 'Hợp đồng',      value: 'contract' },
]

async function loadData() {
  first.value   = 0
  loading.value = true
  try {
    const { data } = await auditLogService.getList({
      action:      filterAction.value ?? undefined,
      entity_type: filterEntityType.value ?? undefined,
      date_from:   filterDateFrom.value ? toISODate(filterDateFrom.value) : undefined,
      date_to:     filterDateTo.value   ? toISODate(filterDateTo.value)   : undefined,
      limit:       500,
    })
    list.value = data
  } catch (e) {
    const err = e as { response?: { data?: { detail?: string } } }
    toast.add({ severity: 'error', summary: 'Lỗi', detail: err.response?.data?.detail ?? 'Không thể tải dữ liệu', life: 4000 })
  } finally {
    loading.value = false
  }
}

function applyFilter() { loadData() }

function resetAndLoad() {
  filterAction.value        = null
  filterEntityType.value    = null
  filterDateFrom.value      = null
  filterDateTo.value        = null
  filters.value.global.value = null
  loadData()
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

function actionLabel(action: string): string {
  return ({
    LOGIN:          'Đăng nhập',
    CREATE:         'Tạo mới',
    UPDATE:         'Cập nhật',
    DELETE:         'Xóa',
    EXPORT:         'Xuất',
    RESET_PASSWORD: 'Đặt lại MK',
  } as Record<string, string>)[action] ?? action
}

function actionSeverity(action: string): string {
  return ({
    LOGIN:          'info',
    CREATE:         'success',
    UPDATE:         'warn',
    DELETE:         'danger',
    EXPORT:         'secondary',
    RESET_PASSWORD: 'warn',
  } as Record<string, string>)[action] ?? 'secondary'
}

function entityLabel(type: string): string {
  return ({
    user:             'Người dùng',
    user_role:        'Phân quyền',
    role:             'Vai trò',
    role_permissions: 'Quyền vai trò',
    department:       'Phòng/Ban',
    job_title:        'Chức danh',
    job_position:     'Vị trí',
    employee:         'Nhân viên',
    contract:         'Hợp đồng',
  } as Record<string, string>)[type] ?? type
}

function entitySeverity(type: string): string {
  return ({
    user:             'warn',
    user_role:        'warn',
    role:             'danger',
    role_permissions: 'danger',
    department:       'info',
    job_title:        'secondary',
    job_position:     'secondary',
    employee:         'info',
    contract:         'success',
  } as Record<string, string>)[type] ?? 'secondary'
}

onMounted(loadData)
</script>

<style scoped>
.detail-wrap  { display: flex; flex-direction: column; gap: 1rem; }
.detail-meta  { display: flex; gap: 1.5rem; flex-wrap: wrap; font-size: 0.9rem; }
.diff-subtitle { margin: 0; font-size: 0.875rem; color: var(--p-text-muted-color); font-weight: 500; }
.ml-2         { margin-left: 0.5rem; }

.val-old { color: var(--p-red-500);   text-decoration: line-through; font-size: 0.875rem; }
.val-new { color: var(--p-green-600); font-weight: 600; font-size: 0.875rem; }
</style>
