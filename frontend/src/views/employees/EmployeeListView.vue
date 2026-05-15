<template>
  <div class="employee-list-page">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h2>Danh sách nhân viên</h2>
        <span class="subtitle">Quản lý hồ sơ nhân sự toàn công ty</span>
      </div>
      <Button label="Thêm mới" icon="pi pi-plus" @click="router.push('/employees/new')" />
    </div>

    <!-- Toolbar -->
    <div class="toolbar">
      <Select
        v-model="filterStatus"
        :options="statusOptions"
        option-label="label"
        option-value="value"
        filter
        class="toolbar-filter"
        @change="onFilterChange"
      />
      <Select
        v-model="filterActive"
        :options="activeOptions"
        option-label="label"
        option-value="value"
        filter
        class="toolbar-filter"
        @change="onFilterChange"
      />
      <IconField class="toolbar-search">
        <InputIcon class="pi pi-search" />
        <InputText
          v-model="keyword"
          placeholder="Tìm tên, CCCD, SĐT..."
          class="w-full"
          @input="onSearch"
        />
      </IconField>
      <Button
        icon="pi pi-refresh"
        severity="secondary"
        text rounded
        v-tooltip.top="'Làm mới'"
        :loading="loading"
        @click="loadData"
      />
    </div>

    <!-- Table -->
    <div class="card">
      <DataTable
        :value="items"
        :loading="loading"
        responsive-layout="scroll"
        :paginator="true"
        :rows="pageSize"
        :total-records="total"
        :rows-per-page-options="[10, 25, 50]"
        lazy
        paginator-template="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink"
        row-hover
        @page="onPage"
        @update:rows="onRowsChange"
        @row-click="onRowClick"
      >
        <template #paginatorstart>
          <span class="paginator-info" v-if="total > 0">
            Hiển thị {{ (page - 1) * pageSize + 1 }}–{{ Math.min(page * pageSize, total) }} / {{ total }}
          </span>
        </template>
        <template #empty>
          <div class="empty-state">
            <i class="pi pi-users" />
            <span>Không có nhân viên nào</span>
          </div>
        </template>

        <Column field="display_code" header="Mã NV" style="width: 100px" />

        <Column field="full_name" header="Họ và tên" style="min-width: 180px">
          <template #body="{ data }">
            <span class="name-cell">{{ data.full_name }}</span>
          </template>
        </Column>

        <Column header="Trạng thái" style="width: 130px">
          <template #body="{ data }">
            <Tag :value="statusLabel(data.status)" :severity="statusSeverity(data.status)" />
          </template>
        </Column>

        <Column field="start_date" header="Ngày vào làm" style="width: 140px">
          <template #body="{ data }">{{ formatDate(data.start_date) }}</template>
        </Column>

        <Column field="phone_number" header="Số điện thoại" style="width: 145px">
          <template #body="{ data }">
            <span class="muted">{{ data.phone_number || '—' }}</span>
          </template>
        </Column>

        <Column header="Tình trạng" style="width: 120px">
          <template #body="{ data }">
            <Tag
              :value="data.is_active ? 'Đang làm' : 'Đã rời'"
              :severity="data.is_active ? 'success' : 'secondary'"
            />
          </template>
        </Column>

        <Column header="" style="width: 90px">
          <template #body="{ data }">
            <div class="action-cell" @click.stop>
              <Button
                icon="pi pi-eye"
                severity="secondary"
                text rounded size="small"
                v-tooltip.top="'Xem hồ sơ'"
                @click="router.push(`/employees/${data.id}`)"
              />
              <Button
                v-if="data.is_active"
                icon="pi pi-ban"
                severity="danger"
                text rounded size="small"
                v-tooltip.top="'Vô hiệu hóa'"
                @click="confirmDeactivate(data)"
              />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'

import employeeService, { type EmployeeListItem } from '@/services/employeeService'

const router  = useRouter()
const toast   = useToast()
const confirm = useConfirm()

// ── State ──────────────────────────────────────────────────────────────────────
const loading      = ref(false)
const items        = ref<EmployeeListItem[]>([])
const total        = ref(0)
const page         = ref(1)
const pageSize     = ref(25)
const keyword      = ref('')
const filterStatus = ref<string | null>(null)
const filterActive = ref<boolean | null>(null)

// ── Options ────────────────────────────────────────────────────────────────────
const statusOptions = [
  { label: 'Tất cả trạng thái', value: null },
  { label: 'Thử việc',          value: 'probation' },
  { label: 'Chính thức',        value: 'official' },
  { label: 'Nghỉ dài hạn',      value: 'long_leave' },
  { label: 'Đã nghỉ việc',      value: 'resigned' },
]

const activeOptions = [
  { label: 'Tất cả', value: null },
  { label: 'Đang làm việc',  value: true },
  { label: 'Đã rời công ty', value: false },
]

// ── Helpers ────────────────────────────────────────────────────────────────────
function statusLabel(s: string): string {
  const map: Record<string, string> = {
    probation: 'Thử việc', official: 'Chính thức',
    long_leave: 'Nghỉ dài hạn', resigned: 'Đã nghỉ',
  }
  return map[s] ?? s
}

function statusSeverity(s: string): 'warn' | 'success' | 'secondary' | 'danger' {
  const map: Record<string, 'warn' | 'success' | 'secondary' | 'danger'> = {
    probation: 'warn', official: 'success',
    long_leave: 'secondary', resigned: 'danger',
  }
  return map[s] ?? 'secondary'
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('vi-VN')
}

function apiError(e: unknown): string {
  const err = e as { response?: { data?: { detail?: unknown } } }
  const detail = err.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((d: { msg: string }) => d.msg).join('; ')
  return typeof detail === 'string' ? detail : 'Đã xảy ra lỗi'
}

// ── Data ───────────────────────────────────────────────────────────────────────
async function loadData() {
  loading.value = true
  try {
    const resp = await employeeService.list({
      keyword:   keyword.value || undefined,
      status:    filterStatus.value ?? undefined,
      is_active: filterActive.value ?? undefined,
      page:      page.value,
      page_size: pageSize.value,
    })
    items.value = resp.data.items
    total.value = resp.data.total
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 })
  } finally {
    loading.value = false
  }
}

let searchTimer: ReturnType<typeof setTimeout>
function onSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { page.value = 1; loadData() }, 300)
}

function onFilterChange() { page.value = 1; loadData() }

function onPage(event: { page: number; rows: number }) {
  page.value = event.page + 1
  pageSize.value = event.rows
  loadData()
}

function onRowsChange(rows: number) {
  pageSize.value = rows
  page.value = 1
  loadData()
}

function onRowClick(event: { data: EmployeeListItem }) {
  router.push(`/employees/${event.data.id}`)
}

// ── Deactivate ─────────────────────────────────────────────────────────────────
function confirmDeactivate(emp: EmployeeListItem) {
  confirm.require({
    message: `Vô hiệu hóa nhân viên "${emp.full_name}"?`,
    header: 'Xác nhận',
    icon: 'pi pi-exclamation-triangle',
    rejectProps: { label: 'Hủy', severity: 'secondary', outlined: true },
    acceptProps: { label: 'Vô hiệu hóa', severity: 'danger' },
    accept: async () => {
      try {
        await employeeService.deactivate(emp.id)
        toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã vô hiệu hóa nhân viên', life: 3000 })
        loadData()
      } catch (e) {
        toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 })
      }
    },
  })
}

onMounted(loadData)
</script>

<style scoped>
.employee-list-page {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.page-header h2 {
  margin: 0 0 0.2rem;
  font-size: 1.5rem;
  font-weight: 700;
}

.subtitle { color: var(--l-text-muted); }

.toolbar {
  display: flex;
  gap: 0.6rem;
  flex-wrap: wrap;
  align-items: center;
}

.toolbar-filter { min-width: 160px; }
.toolbar-search { flex: 1; min-width: 200px; }

.card {
  background: var(--l-surface);
  border: 1px solid var(--l-border);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: var(--l-shadow);
}

.paginator-info {
  font-size: 0.85rem;
  color: var(--l-text-muted);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 3rem;
  color: var(--l-text-muted);
}

.empty-state i { font-size: 2rem; opacity: 0.4; }

.name-cell { font-weight: 500; }
.muted { color: var(--l-text-muted); }

.action-cell {
  display: flex;
  gap: 0.25rem;
  justify-content: flex-end;
}

:deep(.p-datatable-tbody > tr) { cursor: pointer; }

@media (max-width: 768px) {
  .page-header { flex-direction: column; }
}
</style>
