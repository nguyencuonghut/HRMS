<template>
  <div class="section-stack" style="padding-top: 0.75rem">
    <div class="section-card">
      <div class="section-header">
        <div style="display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap">
          <InputText
            v-model="filterSearch"
            placeholder="Tìm mã NV hoặc họ tên..."
            style="min-width: 220px"
            @input="onSearchInput"
          />
          <Select
            v-model="filterStatus"
            :options="statusOptions"
            option-label="label"
            option-value="value"
            show-clear
            placeholder="Trạng thái"
            style="min-width: 180px"
            @change="load"
          />
          <Select
            v-model="filterDeptId"
            :options="deptOptions"
            option-label="label"
            option-value="value"
            filter
            show-clear
            placeholder="Phòng ban"
            style="min-width: 180px"
            @change="load"
          />
        </div>
        <Button
          label="Xuất báo cáo lao động"
          icon="pi pi-file-excel"
          size="small"
          severity="success"
          outlined
          @click="showExportDialog = true"
        />
      </div>

      <div v-if="loading" class="rc-jd-empty">Đang tải...</div>
      <div v-else-if="!rows.length" class="rc-jd-empty">Không có dữ liệu.</div>

      <DataTable v-else :value="rows" size="small" striped-rows>
        <Column field="employee_code" header="Mã NV" style="width: 110px" />
        <Column field="employee_name" header="Họ tên">
          <template #body="{ data }">
            <a
              :href="`/employees/${data.employee_id}`"
              style="color: var(--p-primary-color); text-decoration: none"
            >{{ data.employee_name }}</a>
          </template>
        </Column>
        <Column field="department_name" header="Phòng ban">
          <template #body="{ data }">
            {{ data.department_name ?? '—' }}
          </template>
        </Column>
        <Column header="Đã nộp / Bắt buộc" style="width: 140px; text-align: center">
          <template #body="{ data }">
            {{ data.submitted_count }} / {{ data.total_required }}
          </template>
        </Column>
        <Column field="missing_count" header="Còn thiếu" style="width: 100px; text-align: center">
          <template #body="{ data }">
            <span :style="data.missing_count > 0 ? 'color: var(--p-red-500); font-weight: 600' : ''">
              {{ data.missing_count }}
            </span>
          </template>
        </Column>
        <Column field="expiring_count" header="Sắp hết hạn" style="width: 110px; text-align: center">
          <template #body="{ data }">
            <span :style="data.expiring_count > 0 ? 'color: var(--p-orange-500); font-weight: 600' : ''">
              {{ data.expiring_count }}
            </span>
          </template>
        </Column>
        <Column header="Hoàn thành" style="width: 140px">
          <template #body="{ data }">
            <div style="display: flex; align-items: center; gap: 0.4rem">
              <ProgressBar
                :value="data.completion_rate"
                :show-value="false"
                style="height: 6px; width: 80px; flex-shrink: 0"
              />
              <span style="font-size: 0.8rem">{{ data.completion_rate }}%</span>
            </div>
          </template>
        </Column>
      </DataTable>
    </div>
  </div>

  <!-- Export dialog -->
  <Dialog
    v-model:visible="showExportDialog"
    header="Xuất báo cáo lao động mới"
    modal
    :style="{ width: '360px' }"
  >
    <div class="rc-form" style="margin-top: 0.5rem">
      <div class="rc-row">
        <div class="rc-field">
          <label class="rc-label">Năm</label>
          <InputNumber v-model="exportYear" :use-grouping="false" class="w-full" />
        </div>
        <div class="rc-field">
          <label class="rc-label">Tháng</label>
          <InputNumber
            v-model="exportMonth"
            :min="1"
            :max="12"
            :use-grouping="false"
            class="w-full"
          />
        </div>
      </div>
    </div>
    <template #footer>
      <Button label="Hủy" severity="secondary" outlined @click="showExportDialog = false" />
      <Button
        label="Xuất Excel"
        icon="pi pi-download"
        :loading="exporting"
        @click="doExport"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import ProgressBar from 'primevue/progressbar'
import Select from 'primevue/select'
import departmentService from '@/services/departmentService'
import {
  documentChecklistService,
  type EmployeeChecklistSummary,
} from '@/services/recruitmentService'

// ── Filters ───────────────────────────────────────────────────────────────────

const filterSearch = ref('')
const filterStatus = ref<string | null>(null)
const filterDeptId = ref<number | null>(null)
let searchTimer: ReturnType<typeof setTimeout> | null = null

function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(load, 350)
}

const statusOptions = [
  { label: 'Thiếu giấy tờ', value: 'incomplete' },
  { label: 'Sắp hết hạn', value: 'expiring' },
  { label: 'Hoàn thành', value: 'complete' },
]

interface DeptOption {
  label: string
  value: number
}
const deptOptions = ref<DeptOption[]>([])

// ── Table data ────────────────────────────────────────────────────────────────

const rows = ref<EmployeeChecklistSummary[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const params: { status?: string; department_id?: number; search?: string } = {}
    if (filterSearch.value.trim()) params.search = filterSearch.value.trim()
    if (filterStatus.value) params.status = filterStatus.value
    if (filterDeptId.value) params.department_id = filterDeptId.value
    rows.value = await documentChecklistService.getSummary(params)
  } catch (err) {
    console.error('DocumentChecklistSummaryTab: load error', err)
    rows.value = []
  } finally {
    loading.value = false
  }
}

// ── Export dialog ─────────────────────────────────────────────────────────────

const showExportDialog = ref(false)
const exporting = ref(false)
const now = new Date()
const exportYear = ref<number>(now.getFullYear())
const exportMonth = ref<number>(now.getMonth() + 1)

async function doExport() {
  if (!exportYear.value || !exportMonth.value) return
  exporting.value = true
  try {
    await documentChecklistService.exportLaborReport(exportYear.value, exportMonth.value)
    showExportDialog.value = false
  } catch (err) {
    console.error('DocumentChecklistSummaryTab: export error', err)
  } finally {
    exporting.value = false
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────

onMounted(async () => {
  const depts = await departmentService.getList(true).then((r) => r.data)
  deptOptions.value = depts.map((d) => ({ label: d.name, value: d.id }))
  await load()
})
</script>
