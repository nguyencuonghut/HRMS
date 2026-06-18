<template>
  <div class="section-stack">

    <!-- ── Vị trí hiện tại ──────────────────────────────────────────────── -->
    <div class="section-card">
      <div class="section-header">
        <span class="section-title">Vị trí hiện tại</span>
        <div class="section-actions" v-if="!isNew">
          <Button
            v-can:edit="'employees'"
            v-if="!currentJob"
            label="Gán phòng ban"
            icon="pi pi-plus"
            size="small"
            @click="openCreate"
          />
          <template v-else>
            <Button
              v-can:edit="'employees'"
              label="Sửa thông tin"
              icon="pi pi-pencil"
              severity="secondary"
              outlined
              size="small"
              @click="openEdit"
            />
            <Button
              v-can:edit="'employees'"
              label="Chuyển công tác"
              icon="pi pi-arrow-right-arrow-left"
              size="small"
              @click="transferDialogVisible = true"
            />
          </template>
        </div>
      </div>

      <div v-if="loading" class="loading-state">
        <i class="pi pi-spin pi-spinner" />
        <span>Đang tải...</span>
      </div>

      <div v-else-if="!currentJob" class="empty-state">
        <i class="pi pi-briefcase" />
        <span>Chưa gán phòng ban</span>
      </div>

      <div v-else class="info-grid">
        <div class="info-row">
          <span class="info-label">Phòng ban</span>
          <span class="info-value">
            <span v-if="currentJob.department.display_prefix" class="label-chip">
              {{ currentJob.department.display_prefix }}
            </span>
            {{ currentJob.department.name }}
          </span>
        </div>
        <div class="info-row" v-if="currentJob.job_title">
          <span class="info-label">Chức danh</span>
          <span class="info-value">{{ currentJob.job_title.name }}</span>
        </div>
        <div class="info-row" v-if="currentJob.job_position">
          <span class="info-label">Vị trí công việc</span>
          <span class="info-value">{{ currentJob.job_position.name }}</span>
        </div>
        <div class="info-row" v-if="currentJob.effective_from">
          <span class="info-label">Hiệu lực từ</span>
          <span class="info-value">{{ formatDate(currentJob.effective_from) }}</span>
        </div>
        <div class="info-row" v-if="currentJob.probation_start_date">
          <span class="info-label">Ngày thử việc</span>
          <span class="info-value">
            {{ formatDate(currentJob.probation_start_date) }}
            <template v-if="currentJob.probation_end_date">
              → {{ formatDate(currentJob.probation_end_date) }}
            </template>
          </span>
        </div>
        <div class="info-row" v-if="currentJob.official_date">
          <span class="info-label">Ngày chính thức</span>
          <span class="info-value">{{ formatDate(currentJob.official_date) }}</span>
        </div>
        <div class="info-row" v-if="currentJob.notes">
          <span class="info-label">Ghi chú</span>
          <span class="info-value muted-text">{{ currentJob.notes }}</span>
        </div>
      </div>
    </div>

    <!-- ── Lịch sử công việc ──────────────────────────────────────────────── -->
    <div class="section-card" v-if="historyRecords.length > 0">
      <div class="section-header">
        <span class="section-title">Lịch sử công việc</span>
      </div>
      <DataTable :value="historyRecords" size="small" row-hover>
        <Column header="Phòng ban">
          <template #body="{ data }">
            <span v-if="data.department.display_prefix" class="label-chip">
              {{ data.department.display_prefix }}
            </span>
            {{ data.department.name }}
          </template>
        </Column>
        <Column header="Chức danh">
          <template #body="{ data }">{{ data.job_title?.name ?? '—' }}</template>
        </Column>
        <Column header="Từ ngày" style="width:120px">
          <template #body="{ data }">{{ formatDate(data.effective_from) }}</template>
        </Column>
        <Column header="Đến ngày" style="width:120px">
          <template #body="{ data }">{{ data.effective_to ? formatDate(data.effective_to) : '(hiện tại)' }}</template>
        </Column>
      </DataTable>
    </div>

    <!-- ── Dialog: Gán phòng ban / Sửa thông tin ─────────────────────────── -->
    <Dialog
      v-model:visible="formDialogVisible"
      :header="isEditing ? 'Sửa thông tin công việc' : 'Gán phòng ban'"
      :style="{ width: '520px' }"
      modal
      :closable="!submitting"
    >
      <div class="form-grid">
        <div class="field col-full">
          <label>Phòng ban <span class="req">*</span></label>
          <Select
            v-model="form.department_id"
            :options="departments"
            option-label="name"
            option-value="id"
            filter
            filter-placeholder="Tìm phòng ban..."
            class="w-full"
            :invalid="!!formErrors.department_id"
            @change="onDeptChange"
          />
          <small v-if="formErrors.department_id" class="error-msg">{{ formErrors.department_id }}</small>
        </div>

        <div class="field">
          <label>Chức danh</label>
          <Select
            v-model="form.job_title_id"
            :options="jobTitles"
            option-label="name"
            option-value="id"
            filter
            filter-placeholder="Tìm chức danh..."
            class="w-full"
            :show-clear="true"
          />
        </div>

        <div class="field">
          <label>Vị trí công việc</label>
          <Select
            v-model="form.job_position_id"
            :options="filteredPositions"
            option-label="name"
            option-value="id"
            filter
            filter-placeholder="Tìm vị trí..."
            class="w-full"
            :show-clear="true"
            :disabled="!form.department_id"
            :placeholder="form.department_id ? 'Chọn vị trí' : 'Chọn phòng ban trước'"
          />
        </div>

        <div class="field" v-if="!isEditing">
          <label>Ngày hiệu lực <span class="req">*</span></label>
          <DatePicker
            v-model="form.effective_from_date"
            class="w-full"
            dateFormat="dd/mm/yy"
            :invalid="!!formErrors.effective_from"
          />
          <small v-if="formErrors.effective_from" class="error-msg">{{ formErrors.effective_from }}</small>
        </div>

        <div class="field">
          <label>Ngày bắt đầu thử việc</label>
          <DatePicker v-model="form.probation_start_date" class="w-full" dateFormat="dd/mm/yy" :show-clear="true" />
        </div>

        <div class="field">
          <label>Ngày kết thúc thử việc</label>
          <DatePicker v-model="form.probation_end_date" class="w-full" dateFormat="dd/mm/yy" :show-clear="true" />
        </div>

        <div class="field col-full">
          <label>Ngày chính thức</label>
          <DatePicker v-model="form.official_date" class="w-full" dateFormat="dd/mm/yy" :show-clear="true" />
        </div>

        <div class="field col-full">
          <label>Ghi chú</label>
          <Textarea v-model="form.notes" class="w-full" rows="2" auto-resize />
        </div>
      </div>

      <template #footer>
        <Button label="Hủy" severity="secondary" outlined :disabled="submitting" @click="formDialogVisible = false" />
        <Button v-can:edit="'employees'" :label="isEditing ? 'Lưu thay đổi' : 'Gán phòng ban'" icon="pi pi-check" :loading="submitting" @click="submitForm" />
      </template>
    </Dialog>

    <!-- ── Dialog: Chuyển công tác ───────────────────────────────────────── -->
    <Dialog
      v-model:visible="transferDialogVisible"
      header="Chuyển công tác / Thăng chức"
      :style="{ width: '520px' }"
      modal
      :closable="!submitting"
    >
      <div class="info-notice is-primary" v-if="currentJob">
        <span class="info-label">Vị trí hiện tại</span>
        <span class="info-value">
          {{ currentJob.department.name }}
          <template v-if="currentJob.job_title"> · {{ currentJob.job_title.name }}</template>
        </span>
      </div>

      <div class="form-grid no-top-pad">
        <div class="field col-full">
          <label>Phòng ban mới <span class="req">*</span></label>
          <Select
            v-model="transferForm.department_id"
            :options="departments"
            option-label="name"
            option-value="id"
            filter
            filter-placeholder="Tìm phòng ban..."
            class="w-full"
            :invalid="!!transferErrors.department_id"
            @change="onTransferDeptChange"
          />
          <small v-if="transferErrors.department_id" class="error-msg">{{ transferErrors.department_id }}</small>
        </div>

        <div class="field">
          <label>Chức danh mới</label>
          <Select
            v-model="transferForm.job_title_id"
            :options="jobTitles"
            option-label="name"
            option-value="id"
            filter
            class="w-full"
            :show-clear="true"
          />
        </div>

        <div class="field">
          <label>Vị trí công việc mới</label>
          <Select
            v-model="transferForm.job_position_id"
            :options="transferFilteredPositions"
            option-label="name"
            option-value="id"
            filter
            class="w-full"
            :show-clear="true"
            :disabled="!transferForm.department_id"
          />
        </div>

        <div class="field col-full">
          <label>Ngày hiệu lực <span class="req">*</span></label>
          <DatePicker
            v-model="transferForm.effective_from_date"
            class="w-full"
            dateFormat="dd/mm/yy"
            :invalid="!!transferErrors.effective_from"
          />
          <small v-if="transferErrors.effective_from" class="error-msg">{{ transferErrors.effective_from }}</small>
        </div>

        <div class="field col-full">
          <label>Ghi chú</label>
          <Textarea v-model="transferForm.notes" class="w-full" rows="2" auto-resize />
        </div>
      </div>

      <template #footer>
        <Button label="Hủy" severity="secondary" outlined :disabled="submitting" @click="transferDialogVisible = false" />
        <Button v-can:edit="'employees'" label="Xác nhận chuyển" icon="pi pi-check" :loading="submitting" @click="submitTransfer" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'

import employeeService, { type JobRecordRead } from '@/services/employeeService'
import departmentService from '@/services/departmentService'
import jobTitleService, { type JobTitleRead } from '@/services/jobTitleService'
import jobPositionService, { type JobPositionListItem } from '@/services/jobPositionService'

const props = defineProps<{ employeeId: number; isNew: boolean }>()
const emit  = defineEmits<{ (e: 'refresh'): void }>()

const toast = useToast()

// ── State ──────────────────────────────────────────────────────────────────────
const loading   = ref(false)
const submitting = ref(false)
const records   = ref<JobRecordRead[]>([])

const departments    = ref<{ id: number; name: string; code: string }[]>([])
const jobTitles      = ref<JobTitleRead[]>([])
const allPositions   = ref<JobPositionListItem[]>([])

// ── Computed ───────────────────────────────────────────────────────────────────
const currentJob = computed(() => records.value.find(r => r.is_current) ?? null)
const historyRecords = computed(() => records.value.filter(r => !r.is_current))

const filteredPositions = computed(() =>
  form.value.department_id
    ? allPositions.value.filter(p => p.department_id === form.value.department_id)
    : []
)

const transferFilteredPositions = computed(() =>
  transferForm.value.department_id
    ? allPositions.value.filter(p => p.department_id === transferForm.value.department_id)
    : []
)

// ── Helpers ────────────────────────────────────────────────────────────────────
function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('vi-VN')
}

function toIso(d: Date | null | undefined): string | null {
  if (!d) return null
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function apiError(e: unknown): string {
  const err = e as { response?: { data?: { detail?: unknown } } }
  const detail = err.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((d: { msg: string }) => d.msg).join('; ')
  return typeof detail === 'string' ? detail : 'Đã xảy ra lỗi'
}

// ── Load ───────────────────────────────────────────────────────────────────────
async function loadRecords() {
  if (props.isNew) return
  loading.value = true
  try {
    const resp = await employeeService.getJobRecords(props.employeeId)
    records.value = resp.data
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 })
  } finally {
    loading.value = false
  }
}

async function loadCatalogs() {
  const [depts, titles, positions] = await Promise.all([
    departmentService.getList(true),
    jobTitleService.getList(true),
    jobPositionService.getList({ is_active: true }),
  ])
  departments.value  = depts.data
  jobTitles.value    = titles.data
  allPositions.value = positions.data
}

onMounted(async () => {
  await Promise.all([loadRecords(), loadCatalogs()])
})

watch(() => props.employeeId, () => loadRecords())

// ── Create / Edit form ─────────────────────────────────────────────────────────
const formDialogVisible = ref(false)
const isEditing = ref(false)
const formErrors = ref<Record<string, string>>({})

const form = ref({
  department_id:        null as number | null,
  job_title_id:         null as number | null,
  job_position_id:      null as number | null,
  effective_from_date:  null as Date | null,
  probation_start_date: null as Date | null,
  probation_end_date:   null as Date | null,
  official_date:        null as Date | null,
  notes:                '',
})

function resetForm() {
  form.value = {
    department_id: null, job_title_id: null, job_position_id: null,
    effective_from_date: null, probation_start_date: null,
    probation_end_date: null, official_date: null, notes: '',
  }
  formErrors.value = {}
}

function openCreate() {
  isEditing.value = false
  resetForm()
  formDialogVisible.value = true
}

function openEdit() {
  if (!currentJob.value) return
  isEditing.value = true
  formErrors.value = {}
  const j = currentJob.value
  form.value = {
    department_id:        j.department_id,
    job_title_id:         j.job_title_id,
    job_position_id:      j.job_position_id,
    effective_from_date:  j.effective_from ? new Date(j.effective_from) : null,
    probation_start_date: j.probation_start_date ? new Date(j.probation_start_date) : null,
    probation_end_date:   j.probation_end_date ? new Date(j.probation_end_date) : null,
    official_date:        j.official_date ? new Date(j.official_date) : null,
    notes:                j.notes ?? '',
  }
  formDialogVisible.value = true
}

function onDeptChange() {
  form.value.job_position_id = null
}

function validateForm(): boolean {
  formErrors.value = {}
  if (!form.value.department_id) formErrors.value.department_id = 'Chọn phòng ban'
  if (!isEditing.value && !form.value.effective_from_date) formErrors.value.effective_from = 'Chọn ngày hiệu lực'
  return Object.keys(formErrors.value).length === 0
}

async function submitForm() {
  if (!validateForm()) return
  submitting.value = true
  try {
    if (isEditing.value) {
      await employeeService.updateCurrentJobRecord(props.employeeId, {
        department_id:        form.value.department_id,
        job_title_id:         form.value.job_title_id,
        job_position_id:      form.value.job_position_id,
        probation_start_date: toIso(form.value.probation_start_date),
        probation_end_date:   toIso(form.value.probation_end_date),
        official_date:        toIso(form.value.official_date),
        notes:                form.value.notes || null,
      })
      toast.add({ severity: 'success', summary: 'Đã lưu', detail: 'Thông tin công việc đã được cập nhật', life: 3000 })
    } else {
      await employeeService.createJobRecord(props.employeeId, {
        department_id:        form.value.department_id!,
        job_title_id:         form.value.job_title_id,
        job_position_id:      form.value.job_position_id,
        probation_start_date: toIso(form.value.probation_start_date),
        probation_end_date:   toIso(form.value.probation_end_date),
        official_date:        toIso(form.value.official_date),
        effective_from:       toIso(form.value.effective_from_date)!,
        notes:                form.value.notes || null,
      })
      toast.add({ severity: 'success', summary: 'Đã gán', detail: 'Phòng ban đã được gán thành công', life: 3000 })
    }
    formDialogVisible.value = false
    await loadRecords()
    emit('refresh')
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
  } finally {
    submitting.value = false
  }
}

// ── Transfer form ──────────────────────────────────────────────────────────────
const transferDialogVisible = ref(false)
const transferErrors = ref<Record<string, string>>({})

const transferForm = ref({
  department_id:       null as number | null,
  job_title_id:        null as number | null,
  job_position_id:     null as number | null,
  effective_from_date: null as Date | null,
  notes:               '',
})

watch(transferDialogVisible, (v) => {
  if (v) {
    transferErrors.value = {}
    transferForm.value = {
      department_id: null, job_title_id: null, job_position_id: null,
      effective_from_date: null, notes: '',
    }
  }
})

function onTransferDeptChange() {
  transferForm.value.job_position_id = null
}

function validateTransfer(): boolean {
  transferErrors.value = {}
  if (!transferForm.value.department_id) transferErrors.value.department_id = 'Chọn phòng ban'
  if (!transferForm.value.effective_from_date) transferErrors.value.effective_from = 'Chọn ngày hiệu lực'
  return Object.keys(transferErrors.value).length === 0
}

async function submitTransfer() {
  if (!validateTransfer()) return
  submitting.value = true
  try {
    await employeeService.transferJobRecord(props.employeeId, {
      department_id:    transferForm.value.department_id!,
      job_title_id:     transferForm.value.job_title_id,
      job_position_id:  transferForm.value.job_position_id,
      effective_from:   toIso(transferForm.value.effective_from_date)!,
      notes:            transferForm.value.notes || null,
    })
    toast.add({ severity: 'success', summary: 'Đã chuyển', detail: 'Chuyển công tác đã được ghi nhận', life: 3000 })
    transferDialogVisible.value = false
    await loadRecords()
    emit('refresh')
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
  } finally {
    submitting.value = false
  }
}
</script>
