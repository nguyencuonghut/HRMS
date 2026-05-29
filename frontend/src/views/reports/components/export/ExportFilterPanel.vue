<template>
  <div class="export-filter-panel">
    <div class="export-filter-grid">
      <div class="export-field">
        <label>Loại báo cáo</label>
        <Select
          v-model="draft.report_type"
          :options="reportOptions"
          option-label="label"
          option-value="value"
          @update:model-value="emitApplyType"
        />
      </div>

      <div class="export-field">
        <label>Định dạng</label>
        <Select
          v-model="draft.format"
          :options="formatOptions"
          option-label="label"
          option-value="value"
        />
      </div>

      <div class="export-field export-field-span-2">
        <label>Tên file</label>
        <InputText
          v-model.trim="draft.filename"
          placeholder="Để trống để dùng tên mặc định"
        />
      </div>

      <div class="export-field">
        <label>Phòng ban</label>
        <Select
          v-model="draft.filters.department_id"
          :options="departments"
          option-label="name"
          option-value="id"
          placeholder="Toàn công ty"
          show-clear
          filter
        />
      </div>

      <template v-if="draft.report_type === 'dashboard'">
        <div class="export-field">
          <label>Năm</label>
          <Select
            v-model="draft.filters.year"
            :options="yearOptions"
            option-label="label"
            option-value="value"
            show-clear
          />
        </div>
        <div class="export-field">
          <label>Tháng</label>
          <Select
            v-model="draft.filters.month"
            :options="monthOptions"
            option-label="label"
            option-value="value"
            show-clear
          />
        </div>
      </template>

      <template v-if="draft.report_type === 'hr-employee-list'">
        <div class="export-field">
          <label>Trạng thái</label>
          <Select
            v-model="draft.filters.status"
            :options="employeeStatusOptions"
            option-label="label"
            option-value="value"
            show-clear
          />
        </div>
        <div class="export-field">
          <label>Giới tính</label>
          <Select
            v-model="draft.filters.gender"
            :options="genderOptions"
            option-label="label"
            option-value="value"
            show-clear
          />
        </div>
        <div class="export-field">
          <label>Loại văn bản</label>
          <Select
            v-model="draft.filters.document_kind"
            :options="documentKindOptions"
            option-label="label"
            option-value="value"
            show-clear
          />
        </div>
      </template>

      <template v-if="needsDateRange">
        <div class="export-field">
          <label>Từ ngày</label>
          <DatePicker
            v-model="startDateValue"
            date-format="dd/mm/yy"
            show-icon
            show-button-bar
          />
        </div>
        <div class="export-field">
          <label>Đến ngày</label>
          <DatePicker
            v-model="endDateValue"
            date-format="dd/mm/yy"
            show-icon
            show-button-bar
          />
        </div>
      </template>

      <template v-if="draft.report_type === 'hr-movement'">
        <div class="export-field">
          <label>Nhóm kỳ</label>
          <Select
            v-model="draft.filters.group_by"
            :options="groupByOptions"
            option-label="label"
            option-value="value"
          />
        </div>
      </template>

      <template v-if="draft.report_type === 'leaves'">
        <div class="export-field">
          <label>Năm</label>
          <Select
            v-model="draft.filters.year"
            :options="yearOptions"
            option-label="label"
            option-value="value"
          />
        </div>
      </template>

      <template v-if="draft.report_type === 'insurance'">
        <div class="export-field">
          <label>Năm</label>
          <Select
            v-model="draft.filters.year"
            :options="yearOptions"
            option-label="label"
            option-value="value"
          />
        </div>
        <div class="export-field">
          <label>Tháng</label>
          <Select
            v-model="draft.filters.month"
            :options="monthOptions"
            option-label="label"
            option-value="value"
          />
        </div>
      </template>

      <template v-if="draft.report_type === 'contracts'">
        <div class="export-field">
          <label>Trạng thái</label>
          <Select
            v-model="draft.filters.status"
            :options="contractStatusOptions"
            option-label="label"
            option-value="value"
          />
        </div>
        <div class="export-field">
          <label>Sắp hết hạn trong</label>
          <Select
            v-model="draft.filters.days_ahead"
            :options="daysAheadOptions"
            option-label="label"
            option-value="value"
            show-clear
          />
        </div>
      </template>
    </div>

    <div class="export-filter-summary">
      <span class="export-filter-pill">{{ activeReportLabel }}</span>
      <span class="export-filter-pill">{{ draft.format.toUpperCase() }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import DatePicker from 'primevue/datepicker'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'

import type {
  ExportFormat,
  ExportReportType,
} from '@/services/exportService'
import type { DepartmentRead } from '@/services/departmentService'

interface ExportDraft {
  report_type: ExportReportType
  format: ExportFormat
  filename: string
  filters: Record<string, unknown>
}

const props = defineProps<{
  draft: ExportDraft
  departments: DepartmentRead[]
}>()

const emit = defineEmits<{
  (e: 'report-type-change', value: ExportReportType): void
}>()

const reportOptions: { label: string; value: ExportReportType }[] = [
  { label: 'Dashboard tổng quan', value: 'dashboard' },
  { label: 'Nhân sự: Danh sách nhân viên', value: 'hr-employee-list' },
  { label: 'Nhân sự: Biến động', value: 'hr-movement' },
  { label: 'Nhân sự: Thâm niên', value: 'hr-tenure' },
  { label: 'Nhân sự: Cơ cấu tổ chức', value: 'hr-org-structure' },
  { label: 'Phân tích nghỉ phép', value: 'leaves' },
  { label: 'Báo cáo bảo hiểm', value: 'insurance' },
  { label: 'Báo cáo hợp đồng', value: 'contracts' },
  { label: 'Báo cáo tuyển dụng', value: 'recruitment' },
  { label: 'Báo cáo thử việc', value: 'probation' },
]

const formatOptions = [
  { label: 'Excel (.xlsx)', value: 'xlsx' },
  { label: 'PDF (.pdf)', value: 'pdf' },
]

const currentYear = new Date().getFullYear()
const yearOptions = Array.from({ length: 6 }, (_, index) => currentYear - index).map((year) => ({
  label: `Năm ${year}`,
  value: year,
}))

const monthOptions = Array.from({ length: 12 }, (_, index) => ({
  label: `Tháng ${index + 1}`,
  value: index + 1,
}))

const daysAheadOptions = [
  { label: '30 ngày', value: 30 },
  { label: '60 ngày', value: 60 },
  { label: '90 ngày', value: 90 },
  { label: '180 ngày', value: 180 },
]

const employeeStatusOptions = [
  { label: 'Thử việc', value: 'probation' },
  { label: 'Chính thức', value: 'official' },
  { label: 'Nghỉ dài hạn', value: 'long_leave' },
  { label: 'Đã nghỉ việc', value: 'resigned' },
]

const genderOptions = [
  { label: 'Nam', value: 'male' },
  { label: 'Nữ', value: 'female' },
  { label: 'Khác', value: 'other' },
]

const documentKindOptions = [
  { label: 'Thử việc', value: 'probation' },
  { label: 'Hợp đồng lao động', value: 'labor_contract' },
]

const groupByOptions = [
  { label: 'Tháng', value: 'month' },
  { label: 'Quý', value: 'quarter' },
  { label: 'Năm', value: 'year' },
]

const contractStatusOptions = [
  { label: 'Đang hiệu lực', value: 'active' },
  { label: 'Hết hạn', value: 'expired' },
  { label: 'Tất cả', value: 'all' },
]

const activeReportLabel = computed(
  () => reportOptions.find((item) => item.value === props.draft.report_type)?.label ?? props.draft.report_type,
)

const needsDateRange = computed(() =>
  ['hr-movement', 'recruitment', 'probation'].includes(props.draft.report_type),
)

const startDateValue = computed<Date | null>({
  get() {
    const raw = props.draft.filters.start_date
    return typeof raw === 'string' ? new Date(raw) : null
  },
  set(value) {
    props.draft.filters.start_date = value ? value.toISOString().slice(0, 10) : null
  },
})

const endDateValue = computed<Date | null>({
  get() {
    const raw = props.draft.filters.end_date
    return typeof raw === 'string' ? new Date(raw) : null
  },
  set(value) {
    props.draft.filters.end_date = value ? value.toISOString().slice(0, 10) : null
  },
})

function emitApplyType(value: ExportReportType) {
  emit('report-type-change', value)
}

watch(
  () => props.draft.report_type,
  (value) => {
    if (value === 'dashboard') {
      props.draft.filters.year ??= currentYear
      props.draft.filters.month ??= new Date().getMonth() + 1
    }
    if (value === 'leaves') {
      props.draft.filters.year ??= currentYear
    }
    if (value === 'insurance') {
      props.draft.filters.year ??= currentYear
      props.draft.filters.month ??= new Date().getMonth() + 1
    }
    if (value === 'contracts') {
      props.draft.filters.status ??= 'active'
      props.draft.filters.days_ahead ??= 90
    }
    if (value === 'hr-movement') {
      props.draft.filters.group_by ??= 'month'
    }
  },
  { immediate: true },
)
</script>

<style>
.export-filter-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.export-filter-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1rem;
}

.export-field {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.export-field-span-2 {
  grid-column: span 2;
}

.export-field label {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--l-text-muted);
}

.export-filter-summary {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.export-filter-pill {
  padding: 0.35rem 0.7rem;
  border-radius: 999px;
  border: 1px solid var(--l-border);
  background: color-mix(in srgb, var(--p-primary-color) 8%, var(--l-surface));
  font-size: 0.78rem;
  color: var(--l-text-muted);
}

@media (max-width: 1279px) {
  .export-filter-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 767px) {
  .export-filter-grid {
    grid-template-columns: 1fr;
  }

  .export-field-span-2 {
    grid-column: auto;
  }
}
</style>
