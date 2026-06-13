<template>
  <div class="dept-detail-view">
    <Toast />

    <div class="page-header">
      <div>
        <h2>{{ detail?.department.name ?? 'Chi tiết phòng / ban' }}</h2>
        <span class="subtitle">
          <template v-if="detail">
            {{ detail.department.code }} · {{ detail.department.dept_type_label }}
            <template v-if="detail.parent">
              · Thuộc {{ detail.parent.name }}
            </template>
          </template>
          <template v-else>
            Đang tải thông tin đơn vị
          </template>
        </span>
      </div>
      <div class="page-header-actions">
        <Button
          label="Làm mới"
          icon="pi pi-refresh"
          severity="secondary"
          outlined
          :loading="loadingDetail || loadingHead"
          @click="refreshAll"
        />
        <Button
          label="Quay lại"
          icon="pi pi-arrow-left"
          severity="secondary"
          text
          @click="goBack"
        />
      </div>
    </div>

    <div v-if="detail" class="dept-meta-strip">
      <Tag
        :value="detail.department.is_active ? 'Hoạt động' : 'Đã khóa'"
        :severity="detail.department.is_active ? 'success' : 'danger'"
      />
      <span v-if="detail.parent" class="dept-meta-item">
        Đơn vị cha:
        <button type="button" class="dept-inline-link" @click="goToDepartment(detail.parent.id)">
          {{ detail.parent.name }}
        </button>
      </span>
      <span class="dept-meta-item">Mã: {{ detail.department.code }}</span>
    </div>

    <div class="dept-summary-grid">
      <article v-for="card in summaryCards" :key="card.label" class="dept-summary-card card">
        <span class="dept-summary-label">{{ card.label }}</span>
        <strong class="dept-summary-value">{{ card.value }}</strong>
        <small v-if="card.note" class="dept-summary-note">{{ card.note }}</small>
      </article>
    </div>

    <div class="card dept-head-card">
      <div class="dept-section-head">
        <div>
          <h3>Người đứng đầu hiện tại</h3>
          <p>Quản lý một head hiện hành cho đơn vị này. Một nhân sự có thể phụ trách nhiều đơn vị khác nhau.</p>
        </div>
        <div v-if="canEditHead" class="dept-head-actions">
          <Button
            v-if="!head"
            label="Gán người đứng đầu"
            icon="pi pi-user-plus"
            size="small"
            @click="openHeadDialog"
          />
          <template v-else>
            <Button
              label="Thay đổi"
              icon="pi pi-pencil"
              severity="secondary"
              outlined
              size="small"
              @click="openHeadDialog"
            />
            <Button
              label="Gỡ"
              icon="pi pi-times"
              severity="danger"
              outlined
              size="small"
              :loading="deletingHead"
              @click="confirmDeleteHead"
            />
          </template>
        </div>
      </div>

      <div v-if="loadingHead" class="dept-head-loading">
        <i class="pi pi-spin pi-spinner" />
        <span>Đang tải người đứng đầu hiện tại...</span>
      </div>

      <div v-else-if="!head" class="empty-state dept-head-empty">
        <i class="pi pi-user-minus" />
        <span>Đơn vị này chưa được gán người đứng đầu.</span>
      </div>

      <div v-else class="dept-head-body">
        <div class="dept-head-identity">
          <div class="dept-head-avatar">
            {{ head.employee.full_name.charAt(0).toUpperCase() }}
          </div>
          <div class="dept-head-main">
            <button type="button" class="dept-inline-link dept-head-name" @click="goToEmployee(head.employee.id)">
              {{ head.employee.full_name }}
            </button>
            <div class="dept-head-subline">
              <span class="dept-head-code">{{ head.employee.display_code }}</span>
              <Tag :value="statusLabel(head.employee.status)" :severity="statusSeverity(head.employee.status)" />
            </div>
          </div>
        </div>

        <div class="dept-head-grid">
          <div class="dept-head-item">
            <span class="dept-head-label">Vai trò hiển thị</span>
            <strong>{{ head.display_position_label }}</strong>
          </div>
          <div class="dept-head-item">
            <span class="dept-head-label">Ngày hiệu lực</span>
            <strong>{{ formatDate(head.effective_from) }}</strong>
          </div>
          <div class="dept-head-item">
            <span class="dept-head-label">Phòng ban hiện tại của nhân sự</span>
            <strong>{{ head.employee.current_department_name || 'Chưa có bản ghi công việc hiện hành' }}</strong>
          </div>
          <div class="dept-head-item">
            <span class="dept-head-label">Vị trí / Chức danh hiện tại</span>
            <strong>{{ head.employee.current_job_position_name || head.employee.current_job_title_name || '—' }}</strong>
          </div>
        </div>

        <div
          v-if="head.employee.is_cross_department_assignment"
          class="dept-head-warning"
        >
          <i class="pi pi-exclamation-triangle" />
          <span>
            Nhân sự này đang thuộc đơn vị
            <strong>{{ head.employee.current_department_name }}</strong>,
            không thuộc đúng đơn vị đang xem.
          </span>
        </div>
      </div>
    </div>

    <div class="card dept-employees-card">
      <div class="dept-section-head">
        <div>
          <h3>Nhân sự trực tiếp</h3>
          <p>Danh sách nhân sự hiện đang thuộc đúng đơn vị này.</p>
        </div>
      </div>

      <DataTable
        :value="detail?.direct_employees ?? []"
        :loading="loadingDetail"
        responsive-layout="scroll"
      >
        <template #empty>
          <div class="empty-state">
            <i class="pi pi-users" />
            <span>Đơn vị này chưa có nhân sự trực tiếp.</span>
          </div>
        </template>

        <Column field="display_code" header="Mã NV" style="width: 120px" />

        <Column field="full_name" header="Họ và tên" style="min-width: 220px">
          <template #body="{ data }">
            <button type="button" class="dept-inline-link" @click="goToEmployee(data.id)">
              {{ data.full_name }}
            </button>
          </template>
        </Column>

        <Column field="job_position_name" header="Vị trí" style="min-width: 220px">
          <template #body="{ data }">
            {{ data.job_position_name || data.job_title_name || '—' }}
          </template>
        </Column>

        <Column field="status" header="Trạng thái" style="width: 140px">
          <template #body="{ data }">
            <Tag :value="statusLabel(data.status)" :severity="statusSeverity(data.status)" />
          </template>
        </Column>

        <Column field="start_date" header="Ngày vào làm" style="width: 140px">
          <template #body="{ data }">
            {{ formatDate(data.start_date) }}
          </template>
        </Column>
      </DataTable>
    </div>

    <Dialog
      v-model:visible="headDialogVisible"
      header="Gán người đứng đầu đơn vị"
      :style="{ width: '720px' }"
      modal
      :closable="!savingHead"
      @hide="resetHeadDialog"
    >
      <div class="dept-head-dialog">
        <div class="dept-head-dialog-grid">
          <div class="field field-span-2">
            <label>Nhân sự <span class="req">*</span></label>
            <AutoComplete
              v-model="selectedEmployee"
              :suggestions="employeeSuggestions"
              option-label="full_name"
              dropdown
              force-selection
              :loading="searchingEmployees"
              fluid
              placeholder="Tìm theo mã nhân viên, họ tên hoặc mã số nhân viên"
              @complete="searchEmployees"
              @option-select="handleEmployeeSelect"
              @clear="handleEmployeeClear"
            >
              <template #option="{ option }">
                <div class="dept-head-option">
                  <strong>{{ option.full_name }}</strong>
                  <small>{{ option.display_code }} · {{ statusLabel(option.status) }}</small>
                </div>
              </template>
            </AutoComplete>
            <small v-if="headFormErrors.employee_id" class="error-msg">{{ headFormErrors.employee_id }}</small>
          </div>

          <div class="field">
            <label>Vai trò hiển thị</label>
            <InputText
              v-model.trim="headForm.head_role_label"
              class="w-full"
              maxlength="100"
              placeholder="VD: Trưởng phòng, Phụ trách khối..."
            />
            <small class="help-msg">Nếu để trống, hệ thống fallback sang vị trí công việc hiện tại của nhân sự.</small>
          </div>

          <div class="field">
            <label>Ngày hiệu lực <span class="req">*</span></label>
            <DatePicker
              v-model="headForm.effective_from_date"
              class="w-full"
              date-format="dd/mm/yy"
              :show-icon="true"
            />
            <small v-if="headFormErrors.effective_from" class="error-msg">{{ headFormErrors.effective_from }}</small>
          </div>
        </div>

          <div v-if="selectedEmployeeOption" class="dept-head-selected card">
            <div class="dept-head-selected-row">
              <span class="dept-head-selected-label">Nhân sự đã chọn</span>
              <strong>{{ selectedEmployeeOption.full_name }}</strong>
            </div>
            <div class="dept-head-selected-row">
              <span class="dept-head-selected-label">Mã nhân viên</span>
              <span>{{ selectedEmployeeOption.display_code }}</span>
            </div>
          <div v-if="selectedEmployeeOption.status !== 'official'" class="dept-head-warning subtle">
            <i class="pi pi-info-circle" />
            <span>Nhân sự này hiện có trạng thái {{ statusLabel(selectedEmployeeOption.status).toLowerCase() }}.</span>
          </div>
          <div
            v-if="head?.employee.id === selectedEmployeeOption.id"
            class="dept-head-warning subtle"
          >
            <i class="pi pi-info-circle" />
            <span>Đây là người đang được gán hiện tại. Lưu sẽ cập nhật vai trò hoặc ngày hiệu lực.</span>
          </div>
        </div>
      </div>

      <template #footer>
        <Button label="Hủy" text :disabled="savingHead" @click="headDialogVisible = false" />
        <Button
          label="Lưu người đứng đầu"
          icon="pi pi-save"
          :loading="savingHead"
          @click="submitHead"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AutoComplete from 'primevue/autocomplete'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import Toast from 'primevue/toast'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'

import departmentService, {
  type DepartmentDetailRead,
  type DepartmentHeadRead,
} from '@/services/departmentService'
import employeeService, { type EmployeeLookupItem } from '@/services/employeeService'
import { useAuthStore } from '@/stores/auth'
import { toLocalIso } from '@/utils/format'

type HeadFormErrors = {
  employee_id?: string
  effective_from?: string
}

const route = useRoute()
const router = useRouter()
const toast = useToast()
const confirm = useConfirm()
const auth = useAuthStore()

const loadingDetail = ref(false)
const loadingHead = ref(false)
const savingHead = ref(false)
const deletingHead = ref(false)

const detail = ref<DepartmentDetailRead | null>(null)
const head = ref<DepartmentHeadRead | null>(null)

const headDialogVisible = ref(false)
const employeeSuggestions = ref<EmployeeLookupItem[]>([])
const searchingEmployees = ref(false)
const selectedEmployee = ref<EmployeeLookupItem | string | null>(null)

const headForm = ref({
  employee_id: null as number | null,
  head_role_label: '',
  effective_from_date: new Date(),
})
const headFormErrors = ref<HeadFormErrors>({})

const departmentId = computed(() => Number(route.params.id))
const canEditHead = computed(() => auth.hasPermission('org:edit'))
const selectedEmployeeOption = computed<EmployeeLookupItem | null>(() =>
  selectedEmployee.value && typeof selectedEmployee.value === 'object' ? selectedEmployee.value : null
)

const summaryCards = computed(() => {
  if (!detail.value) {
    return [
      { label: 'Nhân sự trực tiếp', value: '—', note: null },
      { label: 'Nhân sự toàn cây', value: '—', note: null },
      { label: 'Đơn vị con trực tiếp', value: '—', note: null },
      { label: 'Vị trí công việc', value: '—', note: null },
    ]
  }
  return [
    {
      label: 'Nhân sự trực tiếp',
      value: String(detail.value.summary.direct_headcount),
      note: 'Đang thuộc đúng đơn vị hiện tại',
    },
    {
      label: 'Nhân sự toàn cây',
      value: String(detail.value.summary.total_headcount),
      note: 'Bao gồm tất cả đơn vị con',
    },
    {
      label: 'Đơn vị con trực tiếp',
      value: String(detail.value.summary.direct_child_count),
      note: null,
    },
    {
      label: 'Vị trí công việc',
      value: String(detail.value.summary.job_position_count),
      note: 'Thuộc riêng đơn vị hiện tại',
    },
  ]
})

function apiError(e: unknown): string {
  const err = e as { response?: { data?: { detail?: unknown } } }
  const detail = err.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((d: { msg: string }) => d.msg).join('; ')
  return typeof detail === 'string' ? detail : 'Đã xảy ra lỗi, vui lòng thử lại'
}

function formatDate(value: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString('vi-VN')
}

function statusLabel(status: string) {
  switch (status) {
    case 'official':
      return 'Chính thức'
    case 'probation':
      return 'Thử việc'
    case 'long_leave':
      return 'Nghỉ dài hạn'
    case 'resigned':
      return 'Đã nghỉ việc'
    default:
      return status
  }
}

function statusSeverity(status: string) {
  switch (status) {
    case 'official':
      return 'success'
    case 'probation':
      return 'warn'
    case 'long_leave':
      return 'info'
    case 'resigned':
      return 'danger'
    default:
      return 'secondary'
  }
}

function resetHeadDialog() {
  selectedEmployee.value = null
  employeeSuggestions.value = []
  headFormErrors.value = {}
  headForm.value = {
    employee_id: null,
    head_role_label: '',
    effective_from_date: new Date(),
  }
}

function openHeadDialog() {
  headFormErrors.value = {}
  if (head.value) {
    selectedEmployee.value = {
      id: head.value.employee.id,
      employee_seq: Number(head.value.employee.display_code.replace(/\D/g, '')) || head.value.employee.id,
      display_code: head.value.employee.display_code,
      full_name: head.value.employee.full_name,
      status: head.value.employee.status as EmployeeLookupItem['status'],
    }
    headForm.value = {
      employee_id: head.value.employee.id,
      head_role_label: head.value.head_role_label ?? '',
      effective_from_date: new Date(head.value.effective_from),
    }
  } else {
    resetHeadDialog()
  }
  headDialogVisible.value = true
}

function validateHeadForm(): boolean {
  const errors: HeadFormErrors = {}
  if (!headForm.value.employee_id) {
    errors.employee_id = 'Cần chọn một nhân sự'
  }
  if (!headForm.value.effective_from_date || Number.isNaN(headForm.value.effective_from_date.getTime())) {
    errors.effective_from = 'Cần chọn ngày hiệu lực hợp lệ'
  }
  headFormErrors.value = errors
  return Object.keys(errors).length === 0
}

async function searchEmployees(event: { query: string }) {
  searchingEmployees.value = true
  try {
    const response = await employeeService.lookup({
      keyword: event.query.trim() || undefined,
      limit: 20,
    })
    employeeSuggestions.value = response.data
  } catch (e) {
    employeeSuggestions.value = []
    toast.add({
      severity: 'error',
      summary: 'Không tìm được nhân sự',
      detail: apiError(e),
      life: 4000,
    })
  } finally {
    searchingEmployees.value = false
  }
}

function handleEmployeeSelect() {
  headForm.value.employee_id = selectedEmployeeOption.value?.id ?? null
  delete headFormErrors.value.employee_id
}

function handleEmployeeClear() {
  selectedEmployee.value = null
  headForm.value.employee_id = null
}

async function loadDetail() {
  if (!Number.isFinite(departmentId.value)) {
    toast.add({ severity: 'error', summary: 'Không hợp lệ', detail: 'ID phòng / ban không hợp lệ', life: 4000 })
    return
  }

  loadingDetail.value = true
  try {
    const response = await departmentService.getDetail(departmentId.value)
    detail.value = response.data
  } catch (e) {
    detail.value = null
    toast.add({
      severity: 'error',
      summary: 'Không tải được chi tiết phòng / ban',
      detail: apiError(e),
      life: 5000,
    })
  } finally {
    loadingDetail.value = false
  }
}

async function loadHead() {
  if (!Number.isFinite(departmentId.value)) {
    return
  }
  loadingHead.value = true
  try {
    const response = await departmentService.getHead(departmentId.value)
    head.value = response.data
  } catch (e) {
    head.value = null
    toast.add({
      severity: 'error',
      summary: 'Không tải được người đứng đầu',
      detail: apiError(e),
      life: 5000,
    })
  } finally {
    loadingHead.value = false
  }
}

async function refreshAll() {
  await Promise.all([loadDetail(), loadHead()])
}

async function submitHead() {
  if (!validateHeadForm()) return

  savingHead.value = true
  try {
    const response = await departmentService.upsertHead(departmentId.value, {
      employee_id: headForm.value.employee_id as number,
      head_role_label: headForm.value.head_role_label.trim() || null,
      effective_from: toLocalIso(headForm.value.effective_from_date),
    })
    head.value = response.data
    headDialogVisible.value = false
    toast.add({
      severity: 'success',
      summary: 'Đã lưu người đứng đầu',
      detail: `${response.data.employee.full_name} đã được gán cho đơn vị này`,
      life: 4000,
    })
    resetHeadDialog()
  } catch (e) {
    toast.add({
      severity: 'error',
      summary: 'Không lưu được người đứng đầu',
      detail: apiError(e),
      life: 5000,
    })
  } finally {
    savingHead.value = false
  }
}

function confirmDeleteHead() {
  if (!head.value) return
  confirm.require({
    header: 'Gỡ người đứng đầu hiện hành',
    message: `Gỡ "${head.value.employee.full_name}" khỏi vai trò người đứng đầu của đơn vị này?`,
    icon: 'pi pi-exclamation-triangle',
    rejectProps: {
      label: 'Hủy',
      severity: 'secondary',
      outlined: true,
    },
    acceptProps: {
      label: 'Gỡ',
      severity: 'danger',
    },
    accept: async () => {
      deletingHead.value = true
      try {
        const response = await departmentService.deleteHead(departmentId.value)
        head.value = null
        toast.add({
          severity: 'success',
          summary: 'Đã gỡ người đứng đầu',
          detail: response.data.message,
          life: 4000,
        })
      } catch (e) {
        toast.add({
          severity: 'error',
          summary: 'Không gỡ được người đứng đầu',
          detail: apiError(e),
          life: 5000,
        })
      } finally {
        deletingHead.value = false
      }
    },
  })
}

function goToDepartment(id: number) {
  router.push({ name: 'org-department-detail', params: { id } })
}

function goToEmployee(id: number) {
  router.push({ name: 'employee-detail', params: { id } })
}

function goBack() {
  router.push({ name: 'org-departments' })
}

watch(() => route.params.id, refreshAll)

onMounted(refreshAll)
</script>

<style scoped>
.dept-detail-view {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.dept-meta-strip {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
}

.dept-meta-item {
  color: var(--p-text-muted-color);
  font-size: 0.95rem;
}

.dept-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1rem;
}

.dept-summary-card {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.dept-summary-label {
  color: var(--p-text-muted-color);
  font-size: 0.9rem;
}

.dept-summary-value {
  font-size: 1.8rem;
  line-height: 1;
}

.dept-summary-note {
  color: var(--p-text-muted-color);
}

.dept-section-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1rem;
}

.dept-section-head h3 {
  margin: 0;
}

.dept-section-head p {
  margin: 0.35rem 0 0;
  color: var(--p-text-muted-color);
}

.dept-head-actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.dept-inline-link {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--p-primary-color);
  cursor: pointer;
  font: inherit;
}

.dept-inline-link:hover,
.dept-inline-link:focus-visible {
  text-decoration: underline;
}

.dept-head-loading,
.dept-head-empty {
  min-height: 7rem;
}

.dept-head-body {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.dept-head-identity {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.dept-head-avatar {
  width: 3.25rem;
  height: 3.25rem;
  border-radius: 999px;
  background: linear-gradient(135deg, #0f766e, #14b8a6);
  color: #fff;
  display: grid;
  place-items: center;
  font-size: 1.3rem;
  font-weight: 700;
}

.dept-head-main {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.dept-head-name {
  font-size: 1.125rem;
  font-weight: 700;
  text-align: left;
}

.dept-head-subline {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.dept-head-code {
  color: var(--p-text-muted-color);
  font-weight: 600;
}

.dept-head-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.dept-head-item {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  padding: 0.9rem 1rem;
  border-radius: 16px;
  background: color-mix(in srgb, var(--p-surface-100) 75%, transparent);
}

.dept-head-label {
  color: var(--p-text-muted-color);
  font-size: 0.9rem;
}

.dept-head-warning {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.9rem 1rem;
  border-radius: 16px;
  border: 1px solid color-mix(in srgb, #f59e0b 45%, var(--p-surface-border));
  background: color-mix(in srgb, #fef3c7 55%, var(--p-surface-card));
  color: #92400e;
}

.dept-head-warning.subtle {
  margin-top: 0.75rem;
}

.dept-head-dialog {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.dept-head-dialog-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.field-span-2 {
  grid-column: 1 / -1;
}

.dept-head-option {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.dept-head-option small {
  color: var(--p-text-muted-color);
}

.dept-head-selected {
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.dept-head-selected-row {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.dept-head-selected-label {
  color: var(--p-text-muted-color);
  font-size: 0.85rem;
}

.error-msg {
  color: var(--p-red-500);
}

.help-msg {
  color: var(--p-text-muted-color);
}

@media (max-width: 960px) {
  .dept-summary-grid,
  .dept-head-grid,
  .dept-head-dialog-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .dept-summary-grid,
  .dept-head-grid,
  .dept-head-dialog-grid {
    grid-template-columns: 1fr;
  }

  .dept-section-head {
    flex-direction: column;
  }
}
</style>
