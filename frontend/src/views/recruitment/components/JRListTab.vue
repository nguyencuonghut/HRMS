<template>
  <div>
    <!-- Toolbar -->
    <div class="rc-toolbar">
      <Select
        v-model="filterStatus"
        :options="statusOptions"
        option-label="label"
        option-value="value"
        placeholder="Tất cả trạng thái"
        show-clear
        style="width: 180px"
        @change="applyFilter"
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
        @change="applyFilter"
      />
      <Select
        v-model="filterYear"
        :options="yearOptions"
        option-label="label"
        option-value="value"
        placeholder="Năm"
        show-clear
        style="width: 110px"
        @change="applyFilter"
      />

      <Button
        icon="pi pi-refresh"
        severity="secondary"
        text
        rounded
        :loading="loading"
        v-tooltip.top="'Làm mới'"
        @click="reset"
      />

      <Button
        label="Tạo yêu cầu tuyển dụng"
        icon="pi pi-plus"
        class="ml-auto"
        @click="openCreate"
      />
    </div>

    <!-- Table -->
    <div class="card">
      <DataTable
        :value="items"
        :loading="loading"
        responsive-layout="scroll"
        striped-rows
        size="small"
        :rows="pageSize"
        :total-records="total"
        :lazy="true"
        paginator
        paginator-template="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
        current-page-report-template="{first}–{last} / {totalRecords}"
        :rows-per-page-options="[20, 50, 100]"
        @page="onPage"
      >
        <template #empty>
          <div class="rc-empty">Không có yêu cầu tuyển dụng nào</div>
        </template>

        <Column header="Mã JR" style="width: 140px">
          <template #body="{ data }: { data: JobRequisitionListItem }">
            <RouterLink :to="`/recruitment/jr/${data.id}`" class="rc-code-link">
              {{ data.code }}
            </RouterLink>
          </template>
        </Column>

        <Column header="Vị trí" style="min-width: 160px">
          <template #body="{ data }: { data: JobRequisitionListItem }">
            <span>{{ data.job_position_name }}</span>
          </template>
        </Column>

        <Column header="Phòng ban" style="min-width: 140px">
          <template #body="{ data }: { data: JobRequisitionListItem }">
            <span class="rc-muted">{{ data.department_name }}</span>
          </template>
        </Column>

        <Column header="SL" style="width: 60px; text-align: center">
          <template #body="{ data }: { data: JobRequisitionListItem }">
            <span>{{ data.quantity }}</span>
          </template>
        </Column>

        <Column header="Hạn cần" style="width: 110px">
          <template #body="{ data }: { data: JobRequisitionListItem }">
            <span :class="deadlineClass(data.deadline)">
              {{ data.deadline ? formatDate(data.deadline) : '—' }}
            </span>
          </template>
        </Column>

        <Column header="Trạng thái" style="width: 140px">
          <template #body="{ data }: { data: JobRequisitionListItem }">
            <Tag :value="data.status_label" :severity="statusSeverity(data.status)" />
          </template>
        </Column>

        <Column header="" style="width: 120px; text-align: right">
          <template #body="{ data }: { data: JobRequisitionListItem }">
            <RouterLink :to="`/recruitment/jr/${data.id}`">
              <Button icon="pi pi-eye" text rounded size="small" severity="secondary" v-tooltip.top="'Xem chi tiết'" />
            </RouterLink>
            <Button
              v-if="data.status === 'draft'"
              icon="pi pi-pencil"
              text rounded size="small" severity="secondary"
              v-tooltip.top="'Sửa'"
              @click="openEdit(data)"
            />
            <Button
              v-if="data.status === 'draft'"
              icon="pi pi-send"
              text rounded size="small" severity="info"
              v-tooltip.top="'Gửi duyệt'"
              @click="confirmSubmit(data)"
            />
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Dialog tạo/sửa JR -->
    <JRFormDialog
      v-model:visible="showDialog"
      :editing-jr="editingJr"
      @saved="onSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'

import recruitmentService, { type JobRequisitionListItem, type JobRequisitionRead } from '@/services/recruitmentService'
import departmentService, { type DepartmentRead } from '@/services/departmentService'
import JRFormDialog from './JRFormDialog.vue'

const confirm = useConfirm()
const toast   = useToast()

const loading  = ref(false)
const items    = ref<JobRequisitionListItem[]>([])
const total    = ref(0)
const page     = ref(1)
const pageSize = ref(20)

const departments = ref<DepartmentRead[]>([])

const filterStatus = ref<string | null>(null)
const filterDeptId = ref<number | null>(null)
const filterYear   = ref<number | null>(new Date().getFullYear())

const showDialog = ref(false)
const editingJr  = ref<JobRequisitionRead | null>(null)

const currentYear = new Date().getFullYear()
const yearOptions = Array.from({ length: 5 }, (_, i) => ({
  label: String(currentYear - i),
  value: currentYear - i,
}))

const statusOptions = [
  { label: 'Nháp',         value: 'draft' },
  { label: 'Chờ duyệt',   value: 'pending_review' },
  { label: 'Đã duyệt',    value: 'approved' },
  { label: 'Đang tuyển',  value: 'in_progress' },
  { label: 'Hoàn thành',  value: 'completed' },
  { label: 'Đã hủy',      value: 'cancelled' },
]

function statusSeverity(st: string): string {
  const map: Record<string, string> = {
    draft:          'secondary',
    pending_review: 'warn',
    approved:       'info',
    in_progress:    'contrast',
    completed:      'success',
    cancelled:      'danger',
  }
  return map[st] ?? 'secondary'
}

function formatDate(d: string) {
  return new Date(d).toLocaleDateString('vi-VN')
}

function deadlineClass(d: string | null) {
  if (!d) return ''
  const diff = (new Date(d).getTime() - Date.now()) / 86400000
  if (diff < 0) return 'rc-deadline-past'
  if (diff < 7) return 'rc-deadline-near'
  return ''
}

async function load() {
  loading.value = true
  try {
    const res = await recruitmentService.listJR({
      status:        filterStatus.value ?? undefined,
      department_id: filterDeptId.value ?? undefined,
      year:          filterYear.value ?? undefined,
      page:          page.value,
      page_size:     pageSize.value,
    })
    items.value = res.data.items
    total.value = res.data.total
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể tải danh sách JR', life: 4000 })
  } finally {
    loading.value = false
  }
}

function applyFilter() { page.value = 1; load() }
function reset() {
  filterStatus.value = null
  filterDeptId.value = null
  filterYear.value   = new Date().getFullYear()
  page.value = 1
  load()
}
function onPage(e: { page: number; rows: number }) {
  page.value = e.page + 1
  pageSize.value = e.rows
  load()
}

function openCreate() {
  editingJr.value = null
  showDialog.value = true
}

async function openEdit(item: JobRequisitionListItem) {
  try {
    const res = await recruitmentService.getJR(item.id)
    editingJr.value = res.data
    showDialog.value = true
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể tải thông tin JR', life: 3000 })
  }
}

function confirmSubmit(item: JobRequisitionListItem) {
  confirm.require({
    message: `Gửi duyệt yêu cầu tuyển dụng ${item.code}?`,
    header: 'Xác nhận gửi duyệt',
    icon: 'pi pi-send',
    acceptLabel: 'Gửi duyệt',
    rejectLabel: 'Hủy',
    accept: () => doSubmit(item.id),
  })
}

async function doSubmit(id: number) {
  try {
    await recruitmentService.submitJR(id)
    toast.add({ severity: 'success', summary: 'Đã gửi duyệt', detail: 'Yêu cầu tuyển dụng đã được gửi đi', life: 3000 })
    load()
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể gửi duyệt', life: 4000 })
  }
}

function onSaved() {
  showDialog.value = false
  load()
}

onMounted(async () => {
  try {
    const res = await departmentService.getList(true)
    departments.value = res.data
  } catch { /* ignore */ }
  load()
})
</script>
