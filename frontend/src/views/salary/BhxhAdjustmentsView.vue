<template>
  <div class="salary-adj-view">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h2 class="page-title">Lịch sử điều chỉnh lương BHXH</h2>
        <span class="page-subtitle">Toàn bộ quyết định điều chỉnh · Immutable audit trail</span>
      </div>
    </div>

    <!-- Toolbar -->
    <div class="salary-basis-toolbar">
      <Select
        v-model="filterDeptId"
        :options="departments"
        option-label="name"
        option-value="id"
        placeholder="Tất cả phòng ban"
        show-clear
        filter
        style="width: 220px"
        @change="loadPage(1)"
      />
      <DatePicker
        v-model="filterFromDate"
        placeholder="Từ ngày"
        date-format="dd/mm/yy"
        show-clear
        style="width: 160px"
        @update:model-value="loadPage(1)"
      />
      <DatePicker
        v-model="filterToDate"
        placeholder="Đến ngày"
        date-format="dd/mm/yy"
        show-clear
        style="width: 160px"
        @update:model-value="loadPage(1)"
      />
      <IconField>
        <InputIcon class="pi pi-search" />
        <InputText
          v-model="search"
          placeholder="Tìm tên nhân viên"
          style="width: 200px"
          @input="onSearchInput"
        />
      </IconField>
      <Button icon="pi pi-refresh" text rounded :loading="loading" @click="loadPage(1)" />
    </div>

    <!-- Table + detail panel -->
    <div class="salary-adj-layout">
      <!-- Main table -->
      <div class="card salary-adj-table-card">
        <DataTable
          :value="rows"
          :loading="loading"
          responsive-layout="scroll"
          row-hover
          striped-rows
          size="small"
          :row-class="(d: BhxhSalaryAdjustmentRead) => d.id === selected?.id ? 'salary-adj-row-selected' : ''"
          @row-click="onRowClick"
          style="cursor: pointer"
        >
          <template #empty>
            <div class="salary-adj-empty">Không có dữ liệu điều chỉnh</div>
          </template>

          <Column header="Ngày hiệu lực" style="min-width: 120px">
            <template #body="{ data }: { data: BhxhSalaryAdjustmentRead }">
              {{ fmtDate(data.effective_date) }}
            </template>
          </Column>

          <Column header="Nhân viên" style="min-width: 190px">
            <template #body="{ data }: { data: BhxhSalaryAdjustmentRead }">
              <span class="salary-adj-emp-code">{{ data.employee_code }}</span>
              <span class="salary-adj-emp-sep">·</span>
              <span class="salary-adj-emp-name">{{ data.employee_name }}</span>
            </template>
          </Column>

          <Column header="Phòng ban" style="min-width: 130px">
            <template #body="{ data }: { data: BhxhSalaryAdjustmentRead }">
              {{ data.department_name || '—' }}
            </template>
          </Column>

          <Column header="Mức cũ" style="min-width: 120px">
            <template #body="{ data }: { data: BhxhSalaryAdjustmentRead }">
              <span class="salary-adj-amount-old">{{ fmtMoney(data.old_basis_amount) }}</span>
            </template>
          </Column>

          <Column header="Mức mới" style="min-width: 120px">
            <template #body="{ data }: { data: BhxhSalaryAdjustmentRead }">
              <span class="salary-basis-amount">{{ fmtMoney(data.new_basis_amount) }}</span>
            </template>
          </Column>

          <Column header="Thay đổi" style="min-width: 150px">
            <template #body="{ data }: { data: BhxhSalaryAdjustmentRead }">
              <span :class="data.change_direction === 'increase' ? 'salary-adj-delta-up' : 'salary-adj-delta-down'">
                <i :class="data.change_direction === 'increase' ? 'pi pi-arrow-up' : 'pi pi-arrow-down'" />
                {{ data.change_direction === 'increase' ? '+' : '-' }}{{ fmtMoney(data.change_amount) }}
                <span class="salary-adj-pct">
                  ({{ data.change_direction === 'increase' ? '+' : '-' }}{{ data.change_pct.toFixed(1) }}%)
                </span>
              </span>
            </template>
          </Column>
        </DataTable>

        <!-- Pagination -->
        <Paginator
          v-if="total > pageSize"
          :rows="pageSize"
          :total-records="total"
          :first="(currentPage - 1) * pageSize"
          template="PrevPageLink PageLinks NextPageLink"
          @page="(e: { page: number }) => loadPage(e.page + 1)"
        />
        <div class="salary-adj-footer-total">Tổng: {{ total }} điều chỉnh</div>
      </div>

      <!-- Detail panel -->
      <Transition name="salary-adj-panel">
        <div v-if="selected" class="card salary-adj-detail-panel">
          <div class="salary-adj-detail-header">
            <span>Chi tiết</span>
            <Button icon="pi pi-times" text rounded size="small" @click="selected = null" />
          </div>

          <div class="salary-adj-detail-section">
            <div class="salary-adj-detail-item">
              <span class="salary-adj-detail-label">Nhân viên</span>
              <span class="salary-adj-detail-value">
                <strong>{{ selected.employee_code }}</strong> — {{ selected.employee_name }}
              </span>
            </div>
            <div class="salary-adj-detail-item">
              <span class="salary-adj-detail-label">Phòng ban</span>
              <span class="salary-adj-detail-value">{{ selected.department_name || '—' }}</span>
            </div>
          </div>

          <div class="salary-adj-detail-divider" />

          <div class="salary-adj-detail-section">
            <div class="salary-adj-detail-item">
              <span class="salary-adj-detail-label">Ngày hiệu lực</span>
              <span class="salary-adj-detail-value">{{ fmtDate(selected.effective_date) }}</span>
            </div>
            <div class="salary-adj-detail-item">
              <span class="salary-adj-detail-label">Mức cũ</span>
              <span class="salary-adj-detail-value salary-adj-amount-old">{{ fmtMoney(selected.old_basis_amount) }}</span>
            </div>
            <div class="salary-adj-detail-item">
              <span class="salary-adj-detail-label">Mức mới</span>
              <span class="salary-adj-detail-value salary-basis-amount">{{ fmtMoney(selected.new_basis_amount) }}</span>
            </div>
            <div class="salary-adj-detail-item">
              <span class="salary-adj-detail-label">Thay đổi</span>
              <span :class="selected.change_direction === 'increase' ? 'salary-adj-delta-up' : 'salary-adj-delta-down'">
                <i :class="selected.change_direction === 'increase' ? 'pi pi-arrow-up' : 'pi pi-arrow-down'" />
                {{ selected.change_direction === 'increase' ? '+' : '-' }}{{ fmtMoney(selected.change_amount) }}
                ({{ selected.change_direction === 'increase' ? '+' : '-' }}{{ selected.change_pct.toFixed(1) }}%)
              </span>
            </div>
          </div>

          <div class="salary-adj-detail-divider" />

          <div class="salary-adj-detail-section">
            <div class="salary-adj-detail-item">
              <span class="salary-adj-detail-label">Số quyết định</span>
              <span class="salary-adj-detail-value">{{ selected.decision_number || '—' }}</span>
            </div>
            <div class="salary-adj-detail-item">
              <span class="salary-adj-detail-label">Lý do</span>
              <span class="salary-adj-detail-value salary-adj-detail-reason">{{ selected.reason }}</span>
            </div>
          </div>

          <div class="salary-adj-detail-divider" />

          <div class="salary-adj-detail-section">
            <div class="salary-adj-detail-item">
              <span class="salary-adj-detail-label">Người điều chỉnh</span>
              <span class="salary-adj-detail-value">{{ selected.created_by_name || '—' }}</span>
            </div>
            <div class="salary-adj-detail-item">
              <span class="salary-adj-detail-label">Thời gian tạo</span>
              <span class="salary-adj-detail-value">{{ fmtDateTime(selected.created_at) }}</span>
            </div>
            <div class="salary-adj-detail-item">
              <span class="salary-adj-detail-label">Biến động BHXH</span>
              <span class="salary-adj-detail-value">
                <span v-if="selected.insurance_change_event_id" class="salary-adj-event-link">
                  <i class="pi pi-link" /> #{{ selected.insurance_change_event_id }}
                </span>
                <span v-else>—</span>
              </span>
            </div>
          </div>
        </div>
      </Transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Paginator from 'primevue/paginator'
import Select from 'primevue/select'

import departmentService, { type DepartmentRead } from '@/services/departmentService'
import salaryService, { type BhxhSalaryAdjustmentRead } from '@/services/salaryService'

// ── State ─────────────────────────────────────────────────────────────────────

const rows = ref<BhxhSalaryAdjustmentRead[]>([])
const total = ref(0)
const loading = ref(false)
const currentPage = ref(1)
const pageSize = 50

const filterDeptId = ref<number | null>(null)
const filterFromDate = ref<Date | null>(null)
const filterToDate = ref<Date | null>(null)
const search = ref('')
const selected = ref<BhxhSalaryAdjustmentRead | null>(null)

const departments = ref<DepartmentRead[]>([])

// ── Data loading ──────────────────────────────────────────────────────────────

function toIso(d: Date | null): string | null {
  if (!d) return null
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

async function loadPage(page = 1) {
  currentPage.value = page
  loading.value = true
  selected.value = null
  try {
    const res = await salaryService.listAdjustments({
      department_id: filterDeptId.value,
      search: search.value || null,
      from_date: toIso(filterFromDate.value),
      to_date: toIso(filterToDate.value),
      page,
      page_size: pageSize,
    })
    rows.value = res.data.items
    total.value = res.data.total
  } catch {
    rows.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

async function loadDepartments() {
  try {
    const res = await departmentService.getList(true)
    departments.value = res.data
  } catch {
    departments.value = []
  }
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => loadPage(1), 350)
}

// ── Row selection ─────────────────────────────────────────────────────────────

function onRowClick(event: { data: BhxhSalaryAdjustmentRead }) {
  selected.value = selected.value?.id === event.data.id ? null : event.data
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtMoney(val: string | null | undefined) {
  if (!val) return '—'
  return Number(val).toLocaleString('vi-VN') + ' đ'
}

function fmtDate(iso: string) {
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

function fmtDateTime(iso: string | null) {
  if (!iso) return '—'
  const utc = iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z'
  const d = new Date(utc)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

onMounted(() => {
  loadDepartments()
  loadPage(1)
})
</script>
