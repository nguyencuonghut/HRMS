<template>
  <div>
    <!-- Fulfillment summary -->
    <div v-if="fulfillment" class="rc-fulfillment">
      <div class="rc-fulfillment-rate">{{ fulfillment.fulfillment_rate.toFixed(0) }}%</div>
      <div class="rc-fulfillment-meta">
        <strong>Tỷ lệ hoàn thành kế hoạch {{ filterYear }}</strong>
        <span class="rc-fulfillment-label">{{ fulfillment.completed_jr }} / {{ fulfillment.total_planned }} vị trí đã tuyển xong</span>
      </div>
    </div>

    <!-- Toolbar -->
    <div class="rc-toolbar">
      <Select
        v-model="filterYear"
        :options="yearOptions"
        option-label="label"
        option-value="value"
        placeholder="Năm"
        style="width: 110px"
        @change="load"
      />
      <Select
        v-model="filterDeptId"
        :options="departments"
        option-label="name"
        option-value="id"
        placeholder="Tất cả phòng ban"
        show-clear
        filter
        style="width: 210px"
        @change="load"
      />
      <Button
        icon="pi pi-refresh"
        severity="secondary"
        text
        rounded
        :loading="loading"
        v-tooltip.top="'Làm mới'"
        @click="load"
      />
      <Button label="Thêm kế hoạch" icon="pi pi-plus" class="ml-auto" @click="openCreate" />
    </div>

    <div class="card">
      <DataTable :value="items" :loading="loading" striped-rows size="small" responsive-layout="scroll">
        <template #empty>
          <div class="rc-empty">Không có dữ liệu kế hoạch nhân sự</div>
        </template>

        <Column header="Phòng ban" style="min-width: 160px">
          <template #body="{ data }: { data: HeadcountPlanRead }">
            {{ data.department_name ?? '(Toàn công ty)' }}
          </template>
        </Column>

        <Column header="Vị trí" style="min-width: 160px">
          <template #body="{ data }: { data: HeadcountPlanRead }">
            <span class="rc-muted">{{ data.job_position_name ?? '—' }}</span>
          </template>
        </Column>

        <Column header="Hiện tại" style="width: 90px; text-align: center">
          <template #body="{ data }: { data: HeadcountPlanRead }">
            {{ data.current_count }}
          </template>
        </Column>

        <Column header="Kế hoạch" style="width: 90px; text-align: center">
          <template #body="{ data }: { data: HeadcountPlanRead }">
            <strong>{{ data.planned_count }}</strong>
          </template>
        </Column>

        <Column header="Lý do" style="min-width: 200px">
          <template #body="{ data }: { data: HeadcountPlanRead }">
            <span class="rc-muted">{{ data.reason ?? '—' }}</span>
          </template>
        </Column>

        <Column header="" style="width: 90px; text-align: right">
          <template #body="{ data }: { data: HeadcountPlanRead }">
            <Button icon="pi pi-pencil" text rounded size="small" severity="secondary" v-tooltip.top="'Sửa'" @click="openEdit(data)" />
            <Button icon="pi pi-trash"  text rounded size="small" severity="danger"    v-tooltip.top="'Xóa'" @click="confirmDelete(data)" />
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Create/Edit Dialog -->
    <Dialog
      :visible="showDialog"
      @update:visible="showDialog = $event"
      :header="editingPlan ? 'Sửa kế hoạch nhân sự' : 'Thêm kế hoạch nhân sự'"
      modal
      :style="{ width: '500px' }"
      :closable="!saving"
    >
      <div class="rc-form">
        <div class="rc-row">
          <div class="rc-field">
            <label class="rc-label">Năm <span class="rc-req">*</span></label>
            <InputNumber
              v-model="form.year"
              :min="2020"
              :max="2100"
              :use-grouping="false"
              class="w-full"
              :disabled="!!editingPlan"
            />
          </div>
          <div class="rc-field">
            <label class="rc-label">Nhân sự hiện tại</label>
            <InputNumber v-model="form.current_count" :min="0" :use-grouping="false" class="w-full" />
          </div>
        </div>

        <div class="rc-field">
          <label class="rc-label">Phòng ban</label>
          <Select
            v-model="form.department_id"
            :options="departments"
            option-label="name"
            option-value="id"
            placeholder="Toàn công ty"
            show-clear
            filter
            class="w-full"
            :disabled="!!editingPlan"
          />
        </div>

        <div class="rc-field">
          <label class="rc-label">Vị trí công việc</label>
          <Select
            v-model="form.job_position_id"
            :options="positions"
            option-label="name"
            option-value="id"
            placeholder="Không chỉ định"
            show-clear
            filter
            class="w-full"
            :disabled="!!editingPlan"
          />
        </div>

        <div class="rc-field">
          <label class="rc-label">Số lượng kế hoạch <span class="rc-req">*</span></label>
          <InputNumber v-model="form.planned_count" :min="0" :use-grouping="false" class="w-full" />
          <span v-if="formErrors.planned_count" class="rc-error">{{ formErrors.planned_count }}</span>
        </div>

        <div class="rc-field">
          <label class="rc-label">Lý do / Ghi chú</label>
          <Textarea v-model="form.reason" rows="2" class="w-full" auto-resize />
        </div>

        <p v-if="apiError" class="rc-api-error">
          <i class="pi pi-exclamation-triangle" /> {{ apiError }}
        </p>
      </div>

      <template #footer>
        <Button label="Hủy" severity="secondary" text :disabled="saving" @click="showDialog = false" />
        <Button :label="editingPlan ? 'Lưu thay đổi' : 'Thêm'" :loading="saving" @click="submitPlan" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'

import recruitmentService, { type HeadcountPlanRead } from '@/services/recruitmentService'
import departmentService, { type DepartmentRead } from '@/services/departmentService'
import jobPositionService, { type JobPositionListItem } from '@/services/jobPositionService'

const confirm = useConfirm()
const toast   = useToast()

const loading     = ref(false)
const items       = ref<HeadcountPlanRead[]>([])
const departments = ref<DepartmentRead[]>([])
const positions   = ref<JobPositionListItem[]>([])

const currentYear = new Date().getFullYear()
const yearOptions = Array.from({ length: 5 }, (_, i) => ({
  label: String(currentYear - i + 1),
  value: currentYear - i + 1,
}))

const filterYear   = ref<number>(currentYear)
const filterDeptId = ref<number | null>(null)

const fulfillment = ref<{ year: number; total_planned: number; completed_jr: number; fulfillment_rate: number } | null>(null)

const showDialog  = ref(false)
const saving      = ref(false)
const apiError    = ref('')
const formErrors  = ref<Record<string, string>>({})
const editingPlan = ref<HeadcountPlanRead | null>(null)

const form = ref({
  year:           currentYear,
  department_id:  null as number | null,
  job_position_id: null as number | null,
  current_count:  0,
  planned_count:  1,
  reason:         '',
})

async function load() {
  loading.value = true
  try {
    const [planRes, fulfillRes] = await Promise.all([
      recruitmentService.listPlans({
        year:          filterYear.value,
        department_id: filterDeptId.value ?? undefined,
        page_size:     200,
      }),
      recruitmentService.getFulfillmentRate(filterYear.value, filterDeptId.value),
    ])
    items.value       = planRes.data.items
    fulfillment.value = fulfillRes.data
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể tải kế hoạch nhân sự', life: 4000 })
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingPlan.value = null
  apiError.value    = ''
  formErrors.value  = {}
  form.value = {
    year:            filterYear.value,
    department_id:   filterDeptId.value,
    job_position_id: null,
    current_count:   0,
    planned_count:   1,
    reason:          '',
  }
  showDialog.value = true
}

function openEdit(plan: HeadcountPlanRead) {
  editingPlan.value = plan
  apiError.value    = ''
  formErrors.value  = {}
  form.value = {
    year:            plan.year,
    department_id:   plan.department_id,
    job_position_id: plan.job_position_id,
    current_count:   plan.current_count,
    planned_count:   plan.planned_count,
    reason:          plan.reason ?? '',
  }
  showDialog.value = true
}

function validatePlan(): boolean {
  formErrors.value = {}
  if (!form.value.planned_count && form.value.planned_count !== 0) {
    formErrors.value.planned_count = 'Vui lòng nhập số lượng'
  }
  return Object.keys(formErrors.value).length === 0
}

async function submitPlan() {
  if (!validatePlan()) return
  saving.value   = true
  apiError.value = ''
  try {
    if (editingPlan.value) {
      await recruitmentService.updatePlan(editingPlan.value.id, {
        current_count: form.value.current_count,
        planned_count: form.value.planned_count,
        reason:        form.value.reason.trim() || null,
      })
      toast.add({ severity: 'success', summary: 'Đã cập nhật', life: 3000 })
    } else {
      await recruitmentService.createPlan({
        year:            form.value.year,
        department_id:   form.value.department_id,
        job_position_id: form.value.job_position_id,
        current_count:   form.value.current_count,
        planned_count:   form.value.planned_count,
        reason:          form.value.reason.trim() || null,
      })
      toast.add({ severity: 'success', summary: 'Đã thêm kế hoạch', life: 3000 })
    }
    showDialog.value = false
    load()
  } catch (err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    apiError.value = typeof detail === 'string' ? detail : 'Có lỗi xảy ra'
  } finally {
    saving.value = false
  }
}

function confirmDelete(plan: HeadcountPlanRead) {
  const label = plan.department_name ?? 'Toàn công ty'
  confirm.require({
    message:     `Xóa kế hoạch nhân sự "${label} - ${plan.year}"?`,
    header:      'Xác nhận xóa',
    icon:        'pi pi-trash',
    acceptLabel: 'Xóa',
    rejectLabel: 'Hủy',
    acceptClass: 'p-button-danger',
    accept:      () => doDelete(plan.id),
  })
}

async function doDelete(id: number) {
  try {
    await recruitmentService.deletePlan(id)
    toast.add({ severity: 'success', summary: 'Đã xóa', life: 3000 })
    load()
  } catch (err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    toast.add({ severity: 'error', summary: 'Lỗi', detail: typeof detail === 'string' ? detail : 'Không thể xóa', life: 4000 })
  }
}

onMounted(async () => {
  try {
    const [deptsRes, posRes] = await Promise.all([
      departmentService.getList(true),
      jobPositionService.getList({ is_active: true }),
    ])
    departments.value = deptsRes.data
    positions.value   = posRes.data
  } catch { /* ignore */ }
  load()
})
</script>
