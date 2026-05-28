<template>
  <div>
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
      <Select
        v-model="filterStatus"
        :options="statusOptions"
        option-label="label"
        option-value="value"
        placeholder="Tất cả trạng thái BH"
        show-clear
        style="width: 200px"
        @change="loadPage(1)"
      />
      <IconField>
        <InputIcon class="pi pi-search" />
        <InputText
          v-model="search"
          placeholder="Tìm theo tên nhân viên"
          style="width: 220px"
          @input="onSearchInput"
        />
      </IconField>
      <Button icon="pi pi-refresh" text rounded :loading="loading" @click="loadPage(1)" />
    </div>

    <!-- Table -->
    <div class="card">
      <DataTable
        :value="rows"
        :loading="loading"
        responsive-layout="scroll"
        row-hover
        striped-rows
        size="small"
        @row-click="openHistory"
        style="cursor: pointer"
      >
        <template #empty>
          <div style="padding: 1rem; color: var(--p-text-muted-color)">Không có nhân viên nào</div>
        </template>

        <Column header="Mã NV" style="min-width: 90px">
          <template #body="{ data }: { data: SalaryEmployeeRow }">
            <strong>{{ data.employee_code }}</strong>
          </template>
        </Column>

        <Column header="Họ và tên" style="min-width: 180px">
          <template #body="{ data }: { data: SalaryEmployeeRow }">
            {{ data.full_name }}
          </template>
        </Column>

        <Column header="Phòng ban" style="min-width: 150px">
          <template #body="{ data }: { data: SalaryEmployeeRow }">
            {{ data.department_name || '—' }}
          </template>
        </Column>

        <Column header="Mức lương BHXH" style="min-width: 170px">
          <template #body="{ data }: { data: SalaryEmployeeRow }">
            <span v-if="data.insurance_basis_amount" class="salary-basis-amount">
              {{ fmtMoney(data.insurance_basis_amount) }}
            </span>
            <span v-else style="color: var(--p-text-muted-color)">—</span>
            <span
              v-if="data.has_discrepancy"
              v-tooltip.top="'Mức thủ công khác mức trong hợp đồng đang hiệu lực'"
              class="salary-basis-warn"
              style="margin-left: 0.4rem"
            >
              <i class="pi pi-exclamation-triangle" />
            </span>
          </template>
        </Column>

        <Column header="Nguồn" style="min-width: 120px">
          <template #body="{ data }: { data: SalaryEmployeeRow }">
            <span v-if="data.insurance_basis_source === 'contract'" class="salary-source-contract">
              <i class="pi pi-file-edit" /> HĐ
            </span>
            <span v-else-if="data.insurance_basis_source === 'manual_fixed'" class="salary-source-manual">
              <i class="pi pi-pencil" /> Thủ công
            </span>
            <span v-else-if="data.insurance_basis_source === 'computed'" class="salary-source-contract">
              <i class="pi pi-calculator" /> Tính tự động
            </span>
            <span v-else style="color: var(--p-text-muted-color)">—</span>
          </template>
        </Column>

        <Column header="TT bảo hiểm" style="min-width: 120px">
          <template #body="{ data }: { data: SalaryEmployeeRow }">
            <span v-if="data.participation_status === 'active'" class="salary-status-active">● Đang đóng</span>
            <span v-else-if="data.participation_status === 'paused'" class="salary-status-paused">◌ Tạm dừng</span>
            <span v-else-if="data.participation_status === 'stopped'" class="salary-status-stopped">✕ Đã dừng</span>
            <span v-else style="color: var(--p-text-muted-color)">—</span>
          </template>
        </Column>

        <Column header="" style="width: 60px; text-align: right">
          <template #body="{ data }: { data: SalaryEmployeeRow }">
            <Button
              v-if="data.participation_status === 'active'"
              v-tooltip.left="'Điều chỉnh lương BHXH'"
              icon="pi pi-pencil"
              text
              rounded
              size="small"
              @click.stop="openAdjustment(data)"
            />
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
        @page="onPageChange"
      />
      <div style="padding: 0.5rem 0; font-size: 0.85rem; color: var(--p-text-muted-color)">
        Tổng: {{ total }} nhân viên
      </div>
    </div>

    <!-- History dialog -->
    <BhxhHistoryDialog
      v-model="showHistory"
      :employee="selectedEmployee"
      @hide="selectedEmployee = null"
    />

    <!-- Adjustment dialog -->
    <BhxhAdjustmentDialog
      v-model="showAdjustment"
      :employee="adjustEmployee"
      @hide="adjustEmployee = null"
      @saved="onAdjustmentSaved"
    />

    <Toast />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Paginator from 'primevue/paginator'
import Select from 'primevue/select'
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'

import departmentService, { type DepartmentRead } from '@/services/departmentService'
import salaryService, { type SalaryEmployeeRow } from '@/services/salaryService'
import BhxhAdjustmentDialog from './BhxhAdjustmentDialog.vue'
import BhxhHistoryDialog from './BhxhHistoryDialog.vue'

// ── State ─────────────────────────────────────────────────────────────────────

const rows = ref<SalaryEmployeeRow[]>([])
const total = ref(0)
const loading = ref(false)
const currentPage = ref(1)
const pageSize = 50

const filterDeptId = ref<number | null>(null)
const filterStatus = ref<string | null>(null)
const search = ref('')

const departments = ref<DepartmentRead[]>([])
const showHistory = ref(false)
const selectedEmployee = ref<SalaryEmployeeRow | null>(null)

const showAdjustment = ref(false)
const adjustEmployee = ref<SalaryEmployeeRow | null>(null)
const toast = useToast()

// ── Options ───────────────────────────────────────────────────────────────────

const statusOptions = [
  { label: 'Đang đóng', value: 'active' },
  { label: 'Tạm dừng', value: 'paused' },
  { label: 'Đã dừng', value: 'stopped' },
]

// ── Data loading ──────────────────────────────────────────────────────────────

async function loadPage(page = 1) {
  currentPage.value = page
  loading.value = true
  try {
    const res = await salaryService.listEmployees({
      department_id: filterDeptId.value,
      search: search.value || null,
      participation_status: filterStatus.value,
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

function onPageChange(event: { page: number }) {
  loadPage(event.page + 1)
}

// ── Actions ───────────────────────────────────────────────────────────────────

function openHistory(event: { data: SalaryEmployeeRow }) {
  selectedEmployee.value = event.data
  showHistory.value = true
}

function openAdjustment(row: SalaryEmployeeRow) {
  adjustEmployee.value = row
  showAdjustment.value = true
}

function onAdjustmentSaved() {
  toast.add({ severity: 'success', summary: 'Thành công', detail: 'Điều chỉnh lương BHXH đã được lưu', life: 3000 })
  loadPage(currentPage.value)
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtMoney(val: string | null) {
  if (!val) return '—'
  return Number(val).toLocaleString('vi-VN') + ' đ'
}

onMounted(() => {
  loadDepartments()
  loadPage(1)
})
</script>
