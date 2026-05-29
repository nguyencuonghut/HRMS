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
        v-model="filterType"
        :options="[{ label: 'Nội bộ', value: 'internal' }, { label: 'Bên ngoài', value: 'external' }]"
        option-label="label"
        option-value="value"
        placeholder="Loại tin"
        show-clear
        style="width: 140px"
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
      <Button label="Tạo tin tuyển dụng" icon="pi pi-plus" class="ml-auto" @click="openCreate" />
    </div>

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
        current-page-report-template="Hiển thị từ {first} đến {last} trên tổng số {totalRecords} dòng"
        :rows-per-page-options="[20, 50, 100]"
        @page="onPage"
      >
        <template #empty>
          <div class="rc-empty">Không có tin tuyển dụng nào</div>
        </template>

        <Column header="Tiêu đề" style="min-width: 200px">
          <template #body="{ data }: { data: JobPostingRead }">
            <RouterLink :to="`/recruitment/postings/${data.id}`" class="rc-code-link">
              {{ data.title }}
            </RouterLink>
            <div class="rc-muted" style="font-size: 0.78rem">{{ data.job_requisition_code }}</div>
          </template>
        </Column>

        <Column header="Vị trí / Phòng ban" style="min-width: 160px">
          <template #body="{ data }: { data: JobPostingRead }">
            <span>{{ data.job_position_name }}</span>
            <div class="rc-muted" style="font-size: 0.78rem">{{ data.department_name }}</div>
          </template>
        </Column>

        <Column header="Loại" style="width: 90px">
          <template #body="{ data }: { data: JobPostingRead }">
            <Tag
              :value="data.posting_type_label"
              :severity="data.posting_type === 'internal' ? 'info' : 'secondary'"
            />
          </template>
        </Column>

        <Column header="Kênh" style="min-width: 120px">
          <template #body="{ data }: { data: JobPostingRead }">
            <span v-if="data.channels.length" class="rc-muted">
              {{ data.channels.map(c => c.name).join(', ') }}
            </span>
            <span v-else class="rc-muted">—</span>
          </template>
        </Column>

        <Column header="Hạn nộp" style="width: 110px">
          <template #body="{ data }: { data: JobPostingRead }">
            <span :class="deadlineClass(data.deadline)">
              {{ data.deadline ? formatDate(data.deadline) : '—' }}
            </span>
          </template>
        </Column>

        <Column header="UV" style="width: 60px; text-align: center">
          <template #body="{ data }: { data: JobPostingRead }">
            {{ data.candidate_count }}
          </template>
        </Column>

        <Column header="Trạng thái" style="width: 130px">
          <template #body="{ data }: { data: JobPostingRead }">
            <Tag :value="data.status_label" :severity="statusSeverity(data.status)" />
          </template>
        </Column>

        <Column header="" style="width: 130px; text-align: right">
          <template #body="{ data }: { data: JobPostingRead }">
            <RouterLink :to="`/recruitment/postings/${data.id}`">
              <Button icon="pi pi-eye" text rounded size="small" severity="secondary" v-tooltip.top="'Xem'" />
            </RouterLink>
            <Button
              v-if="data.status === 'draft' || data.status === 'active'"
              icon="pi pi-pencil"
              text rounded size="small" severity="secondary"
              v-tooltip.top="'Sửa'"
              @click="openEdit(data)"
            />
            <Button
              v-if="data.status === 'draft'"
              icon="pi pi-send"
              text rounded size="small" severity="success"
              v-tooltip.top="'Đăng tin'"
              @click="confirmPublish(data)"
            />
            <Button
              v-if="data.status === 'active'"
              icon="pi pi-times-circle"
              text rounded size="small" severity="warn"
              v-tooltip.top="'Đóng tin'"
              @click="confirmClose(data)"
            />
            <Button
              v-if="data.status === 'closed'"
              icon="pi pi-refresh"
              text rounded size="small" severity="info"
              v-tooltip.top="'Mở lại'"
              @click="confirmReopen(data)"
            />
          </template>
        </Column>
      </DataTable>
    </div>

    <JobPostingFormDialog
      v-model:visible="showDialog"
      :editing="editingPosting"
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

import recruitmentService, { type JobPostingRead } from '@/services/recruitmentService'
import JobPostingFormDialog from './JobPostingFormDialog.vue'

const confirm = useConfirm()
const toast   = useToast()

const loading  = ref(false)
const items    = ref<JobPostingRead[]>([])
const total    = ref(0)
const page     = ref(1)
const pageSize = ref(20)

const filterStatus = ref<string | null>(null)
const filterType   = ref<string | null>(null)

const showDialog    = ref(false)
const editingPosting = ref<JobPostingRead | null>(null)

const statusOptions = [
  { label: 'Nháp',       value: 'draft' },
  { label: 'Đang tuyển', value: 'active' },
  { label: 'Đã đóng',    value: 'closed' },
  { label: 'Hết hạn',    value: 'expired' },
]

function statusSeverity(st: string): string {
  const map: Record<string, string> = {
    draft: 'secondary', active: 'success', closed: 'warn', expired: 'danger',
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
    const res = await recruitmentService.listPostings({
      status:       filterStatus.value ?? undefined,
      posting_type: filterType.value   ?? undefined,
      page:         page.value,
      page_size:    pageSize.value,
    })
    items.value = res.data.items
    total.value = res.data.total
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể tải danh sách tin tuyển dụng', life: 4000 })
  } finally {
    loading.value = false
  }
}

function applyFilter() { page.value = 1; load() }
function reset() { filterStatus.value = null; filterType.value = null; page.value = 1; load() }
function onPage(e: { page: number; rows: number }) { page.value = e.page + 1; pageSize.value = e.rows; load() }

function openCreate() { editingPosting.value = null; showDialog.value = true }
function openEdit(p: JobPostingRead) { editingPosting.value = p; showDialog.value = true }
function onSaved() { showDialog.value = false; load() }

function confirmPublish(p: JobPostingRead) {
  confirm.require({
    message: `Đăng tin "${p.title}"?`,
    header: 'Xác nhận đăng tin',
    icon: 'pi pi-send',
    acceptLabel: 'Đăng',
    rejectLabel: 'Hủy',
    accept: () => doPublish(p.id),
  })
}

async function doPublish(id: number) {
  try {
    await recruitmentService.publishPosting(id)
    toast.add({ severity: 'success', summary: 'Đã đăng tin', life: 3000 })
    load()
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể đăng tin', life: 4000 })
  }
}

function confirmClose(p: JobPostingRead) {
  confirm.require({
    message: `Đóng tin "${p.title}"?`,
    header: 'Xác nhận đóng tin',
    icon: 'pi pi-times-circle',
    acceptLabel: 'Đóng tin',
    rejectLabel: 'Hủy',
    accept: () => doClose(p.id),
  })
}

async function doClose(id: number) {
  try {
    await recruitmentService.closePosting(id)
    toast.add({ severity: 'warn', summary: 'Đã đóng tin', life: 3000 })
    load()
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể đóng tin', life: 4000 })
  }
}

function confirmReopen(p: JobPostingRead) {
  confirm.require({
    message: `Mở lại tin "${p.title}"?`,
    header: 'Xác nhận mở lại',
    icon: 'pi pi-refresh',
    acceptLabel: 'Mở lại',
    rejectLabel: 'Hủy',
    accept: () => doReopen(p.id),
  })
}

async function doReopen(id: number) {
  try {
    await recruitmentService.reopenPosting(id)
    toast.add({ severity: 'success', summary: 'Đã mở lại tin', life: 3000 })
    load()
  } catch (err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    toast.add({ severity: 'error', summary: 'Lỗi', detail: typeof detail === 'string' ? detail : 'Không thể mở lại', life: 4000 })
  }
}

onMounted(() => load())
</script>
