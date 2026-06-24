<template>
  <div class="hr-report-tab">
    <Toast />

    <div class="hr-toolbar">
      <div class="hr-toolbar-actions">
        <Button
          label="Xem báo cáo"
          icon="pi pi-search"
          :loading="loading"
          @click="loadReport"
        />
        <Button
          label="Xuất Excel"
          icon="pi pi-file-excel"
          severity="success"
          outlined
          :loading="exporting"
          @click="exportExcel"
        />
      </div>
    </div>

    <div class="card hr-filter-card">
      <div class="hr-filter-grid">
        <div class="hr-field">
          <label>Năm báo cáo</label>
          <Select
            v-model="selectedYear"
            :options="yearOptions"
            option-label="label"
            option-value="value"
          />
        </div>
        <div class="hr-field">
          <label>Tháng báo cáo</label>
          <Select
            v-model="selectedMonth"
            :options="monthOptions"
            option-label="label"
            option-value="value"
          />
        </div>
        <div class="hr-field">
          <label>Phòng ban</label>
          <Select
            v-model="departmentId"
            :options="departments"
            option-label="name"
            option-value="id"
            placeholder="Toàn công ty"
            show-clear
            filter
          />
        </div>
        <div class="hr-field">
          <label>Giới tính</label>
          <Select
            v-model="gender"
            :options="genderOptions"
            option-label="label"
            option-value="value"
            placeholder="Nam + Nữ"
            show-clear
          />
        </div>
      </div>
    </div>

    <div v-if="report" class="hr-summary-strip">
      <div class="hr-summary-item">
        <span class="hr-summary-label">Tổng lao động cao tuổi</span>
        <strong>{{ report.summary.total }}</strong>
      </div>
      <div class="hr-summary-item">
        <span class="hr-summary-label">Nam</span>
        <strong>{{ report.summary.male_count }}</strong>
      </div>
      <div class="hr-summary-item">
        <span class="hr-summary-label">Nữ</span>
        <strong>{{ report.summary.female_count }}</strong>
      </div>
      <div class="hr-summary-item">
        <span class="hr-summary-label">Kỳ chốt</span>
        <strong>{{ formatDate(report.as_of_date) }}</strong>
      </div>
    </div>

    <div v-if="report" class="card hr-filter-card">
      <div class="older-worker-policy-card">
        <div>
          <div class="hr-summary-label">Policy áp dụng</div>
          <div class="older-worker-policy-name">{{ report.policy_name }}</div>
          <div class="older-worker-policy-note">
            {{ report.legal_basis_summary || 'Chưa khai báo căn cứ pháp lý' }}
          </div>
        </div>
        <div class="older-worker-thresholds">
          <Tag :value="`Nam: ${report.male_threshold_label || '—'}`" severity="contrast" />
          <Tag :value="`Nữ: ${report.female_threshold_label || '—'}`" severity="info" />
        </div>
      </div>
    </div>

    <div class="card hr-table-card">
      <div class="older-worker-section-header">
        <div>
          <h3>Danh sách người lao động cao tuổi</h3>
          <p>Snapshot tại ngày cuối tháng của kỳ báo cáo.</p>
        </div>
      </div>

      <DataTable
        :value="report?.items ?? []"
        :loading="loading"
        striped-rows
        responsive-layout="scroll"
      >
        <template #empty>
          <div class="hr-empty">Không có lao động cao tuổi trong bộ lọc hiện tại.</div>
        </template>

        <Column field="employee_code" header="Mã NV" style="width: 120px" />
        <Column field="full_name" header="Họ tên" style="min-width: 220px" />
        <Column header="Giới tính" style="width: 110px">
          <template #body="{ data }">{{ genderLabel(data.gender) }}</template>
        </Column>
        <Column header="Ngày sinh" style="width: 130px">
          <template #body="{ data }">{{ formatDate(data.date_of_birth) }}</template>
        </Column>
        <Column field="department_name" header="Phòng ban" style="min-width: 180px">
          <template #body="{ data }">{{ data.department_name || '—' }}</template>
        </Column>
        <Column field="job_title_name" header="Chức danh" style="min-width: 180px">
          <template #body="{ data }">{{ data.job_title_name || '—' }}</template>
        </Column>
        <Column header="Ngày vào làm" style="width: 130px">
          <template #body="{ data }">{{ formatDate(data.start_date) }}</template>
        </Column>
        <Column header="Ngưỡng tuổi nghỉ hưu" style="width: 160px">
          <template #body="{ data }">
            {{ formatRetirementAge(data.retirement_age_years, data.retirement_age_months) }}
          </template>
        </Column>
        <Column header="Ngày đủ tuổi" style="width: 130px">
          <template #body="{ data }">{{ formatDate(data.retirement_date) }}</template>
        </Column>
        <Column header="Tuổi tại kỳ" style="width: 140px">
          <template #body="{ data }">{{ formatRetirementAge(data.age_years, data.age_months) }}</template>
        </Column>
        <Column header="Vượt ngưỡng" style="width: 140px">
          <template #body="{ data }">{{ data.months_beyond_retirement }} tháng</template>
        </Column>
      </DataTable>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'
import departmentService, { type DepartmentRead } from '@/services/departmentService'
import hrReportService from '@/services/hrReportService'
import type { HrOlderWorkerReportResponse } from '@/types/hr_report.types'

const toast = useToast()
const now = new Date()

const loading = ref(false)
const exporting = ref(false)
const departments = ref<DepartmentRead[]>([])
const report = ref<HrOlderWorkerReportResponse | null>(null)

const selectedYear = ref(now.getFullYear())
const selectedMonth = ref(now.getMonth() + 1)
const departmentId = ref<number | null>(null)
const gender = ref<'male' | 'female' | null>(null)

const yearOptions = computed(() =>
  Array.from({ length: 11 }, (_, index) => {
    const year = now.getFullYear() - 5 + index
    return { label: `Năm ${year}`, value: year }
  }),
)

const monthOptions = Array.from({ length: 12 }, (_, index) => ({
  label: `Tháng ${index + 1}`,
  value: index + 1,
}))

const genderOptions = [
  { label: 'Nam', value: 'male' },
  { label: 'Nữ', value: 'female' },
]

function formatDate(value?: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('vi-VN').format(date)
}

function genderLabel(value: string) {
  if (value === 'male') return 'Nam'
  if (value === 'female') return 'Nữ'
  return value
}

function formatRetirementAge(years: number, months: number) {
  return `${years} tuổi ${months} tháng`
}

function buildReportParams() {
  return {
    year: selectedYear.value,
    month: selectedMonth.value,
    department_id: departmentId.value,
    gender: gender.value,
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

async function loadReport() {
  loading.value = true
  try {
    const res = await hrReportService.getOlderWorkerReport(buildReportParams())
    report.value = res.data
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Không tải được báo cáo',
      detail: error?.response?.data?.detail || 'Vui lòng thử lại.',
      life: 4000,
    })
  } finally {
    loading.value = false
  }
}

async function exportExcel() {
  exporting.value = true
  try {
    await hrReportService.exportReport('older-worker', buildReportParams())
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Xuất Excel thất bại',
      detail: error?.response?.data?.detail || 'Không thể xuất báo cáo.',
      life: 4000,
    })
  } finally {
    exporting.value = false
  }
}

onMounted(async () => {
  await loadDepartments()
  await loadReport()
})
</script>

<style>
.older-worker-policy-card {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.older-worker-policy-name {
  font-size: 1rem;
  font-weight: 700;
  color: var(--l-text);
}

.older-worker-policy-note {
  margin-top: 0.35rem;
  color: var(--l-text-muted);
}

.older-worker-thresholds {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: flex-start;
}

.older-worker-section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.older-worker-section-header h3 {
  margin: 0;
  font-size: 1rem;
}

.older-worker-section-header p {
  margin: 0.25rem 0 0;
  color: var(--l-text-muted);
}
</style>
