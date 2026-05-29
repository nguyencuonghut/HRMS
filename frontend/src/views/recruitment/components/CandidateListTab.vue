<template>
  <div>
    <!-- Toolbar -->
    <div class="rc-toolbar">
      <InputText
        v-model="searchText"
        placeholder="Tìm tên, email cá nhân, SĐT..."
        style="width: 220px"
        @keyup.enter="applyFilter"
      />
      <Select
        v-model="filterChannel"
        :options="channels"
        option-label="name"
        option-value="id"
        placeholder="Tất cả kênh nguồn"
        show-clear
        style="width: 180px"
        @change="applyFilter"
      />
      <Button
        icon="pi pi-search"
        severity="secondary"
        outlined
        @click="applyFilter"
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
        label="Import Excel"
        icon="pi pi-upload"
        severity="secondary"
        outlined
        class="ml-auto"
        @click="showImport = true"
      />
      <Button label="Thêm ứng viên" icon="pi pi-plus" @click="openCreate" />
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
          <div class="rc-empty">Không có ứng viên nào</div>
        </template>

        <Column header="Họ và tên" style="min-width: 180px">
          <template #body="{ data }: { data: CandidateListItem }">
            <div style="display: flex; flex-direction: column; gap: 0.35rem">
              <RouterLink :to="`/recruitment/candidates/${data.id}`" class="rc-code-link">
                {{ data.full_name }}
              </RouterLink>
              <Tag
                :value="data.identity_strength_label"
                :severity="identityStrengthSeverity(data.identity_strength)"
                style="align-self: flex-start; font-size: 0.72rem"
              />
            </div>
          </template>
        </Column>

        <Column header="Liên hệ" style="min-width: 160px">
          <template #body="{ data }: { data: CandidateListItem }">
            <div>{{ data.phone_number ?? '—' }}</div>
            <div class="rc-muted" style="font-size: 0.78rem">{{ data.personal_email ?? '' }}</div>
          </template>
        </Column>

        <Column header="Vị trí / Công ty hiện tại" style="min-width: 180px">
          <template #body="{ data }: { data: CandidateListItem }">
            <span>{{ data.current_position ?? '—' }}</span>
            <div class="rc-muted" style="font-size: 0.78rem">{{ data.current_company ?? '' }}</div>
          </template>
        </Column>

        <Column header="Quốc tịch / Kênh" style="min-width: 140px">
          <template #body="{ data }: { data: CandidateListItem }">
            <div>{{ data.nationality_name ?? '—' }}</div>
            <div class="rc-muted" style="font-size: 0.78rem">{{ data.source_channel_name ?? '' }}</div>
          </template>
        </Column>

        <Column header="Đang xét" style="width: 80px; text-align: center">
          <template #body="{ data }: { data: CandidateListItem }">
            <Badge
              v-if="data.active_applications"
              :value="String(data.active_applications)"
              severity="info"
            />
            <span v-else class="rc-muted">0</span>
          </template>
        </Column>

        <Column header="Số đợt tuyển dụng" style="width: 130px; text-align: center">
          <template #body="{ data }: { data: CandidateListItem }">
            <Badge
              v-if="data.total_jr_participated"
              :value="String(data.total_jr_participated)"
              severity="secondary"
            />
            <span v-else class="rc-muted">0</span>
          </template>
        </Column>

        <Column header="Ngày tạo" style="width: 110px">
          <template #body="{ data }: { data: CandidateListItem }">
            <span class="rc-muted">{{ formatDate(data.created_at) }}</span>
          </template>
        </Column>

        <Column header="" style="width: 110px; text-align: right">
          <template #body="{ data }: { data: CandidateListItem }">
            <RouterLink :to="`/recruitment/candidates/${data.id}`">
              <Button icon="pi pi-eye" text rounded size="small" severity="secondary" v-tooltip.top="'Xem'" />
            </RouterLink>
            <Button
              icon="pi pi-pencil"
              text rounded size="small" severity="secondary"
              v-tooltip.top="'Sửa'"
              @click="openEdit(data)"
            />
            <Button
              icon="pi pi-trash"
              text rounded size="small" severity="danger"
              v-tooltip.top="'Xóa'"
              @click="confirmDelete(data)"
            />
          </template>
        </Column>
      </DataTable>
    </div>

    <CandidateFormDialog
      v-model:visible="showForm"
      :editing="editingCandidate"
      @saved="onSaved"
    />
    <CandidateImportDialog
      v-model:visible="showImport"
      @imported="onSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import Badge from 'primevue/badge'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'

import recruitmentService, {
  type CandidateListItem,
  type RecruitmentChannelRead,
} from '@/services/recruitmentService'
import CandidateFormDialog from './CandidateFormDialog.vue'
import CandidateImportDialog from './CandidateImportDialog.vue'

const confirm = useConfirm()
const toast = useToast()

const loading = ref(false)
const items = ref<CandidateListItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const searchText = ref('')
const filterChannel = ref<number | null>(null)
const channels = ref<RecruitmentChannelRead[]>([])

const showForm = ref(false)
const showImport = ref(false)
const editingCandidate = ref<import('@/services/recruitmentService').CandidateRead | null>(null)

function formatDate(d: string) {
  return new Date(d).toLocaleDateString('vi-VN')
}

function identityStrengthSeverity(strength: CandidateListItem['identity_strength']) {
  const map = {
    strong: 'success',
    medium: 'warn',
    weak: 'danger',
  } as const
  return map[strength] ?? 'secondary'
}

async function load() {
  loading.value = true
  try {
    const res = await recruitmentService.listCandidates({
      search: searchText.value || undefined,
      source_channel_id: filterChannel.value ?? undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    items.value = res.data.items
    total.value = res.data.total
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể tải danh sách ứng viên', life: 4000 })
  } finally {
    loading.value = false
  }
}

function applyFilter() { page.value = 1; load() }
function reset() { searchText.value = ''; filterChannel.value = null; page.value = 1; load() }
function onPage(e: { page: number; rows: number }) { page.value = e.page + 1; pageSize.value = e.rows; load() }

function openCreate() { editingCandidate.value = null; showForm.value = true }
async function openEdit(item: CandidateListItem) {
  try {
    const res = await recruitmentService.getCandidate(item.id)
    editingCandidate.value = res.data
    showForm.value = true
  } catch {}
}
function onSaved() { showForm.value = false; load() }

function confirmDelete(item: CandidateListItem) {
  confirm.require({
    message: `Xóa ứng viên "${item.full_name}"? Thao tác này không thể hoàn tác.`,
    header: 'Xác nhận xóa',
    icon: 'pi pi-trash',
    acceptLabel: 'Xóa',
    rejectLabel: 'Hủy',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        await recruitmentService.deleteCandidate(item.id)
        toast.add({ severity: 'warn', summary: 'Đã xóa', life: 3000 })
        load()
      } catch {
        toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể xóa', life: 4000 })
      }
    },
  })
}

onMounted(async () => {
  try {
    const res = await recruitmentService.listChannels()
    channels.value = (res.data as unknown as RecruitmentChannelRead[])
  } catch {}
  load()
})
</script>
