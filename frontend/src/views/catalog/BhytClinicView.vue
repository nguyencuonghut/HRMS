<template>
  <div class="bhyt-clinic-view">
    <div class="page-header">
      <div>
        <h2>Danh mục bệnh viện KCB</h2>
        <span class="subtitle">Danh sách cơ sở khám chữa bệnh ban đầu (nguồn VNPT/BHYT)</span>
      </div>
      <div class="page-header-actions">
        <Button label="Thêm bệnh viện" icon="pi pi-plus" @click="openCreate" />
        <Button
          label="Về tổng quan danh mục"
          icon="pi pi-th-large"
          severity="secondary"
          outlined
          @click="router.push('/catalog')"
        />
      </div>
    </div>

    <!-- Filter toolbar -->
    <div class="toolbar">
      <IconField class="toolbar-search">
        <InputIcon class="pi pi-search" />
        <InputText
          v-model="filters.keyword"
          placeholder="Tìm mã hoặc tên bệnh viện..."
          class="w-full"
          @keyup.enter="applyFilter"
        />
      </IconField>
      <InputText
        v-model="filters.province_code"
        placeholder="Mã tỉnh (vd: 01)"
        class="toolbar-filter-sm"
        @keyup.enter="applyFilter"
      />
      <Button label="Lọc" icon="pi pi-filter" @click="applyFilter" />
      <Button icon="pi pi-refresh" severity="secondary" text rounded :loading="loading" @click="reset" />
    </div>

    <!-- DataTable -->
    <div class="card">
      <DataTable
        :value="items"
        :loading="loading"
        responsive-layout="scroll"
        :rows="pageSize"
        :total-records="total"
        :lazy="true"
        paginator
        paginator-template="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
        current-page-report-template="Hiển thị từ {first} đến {last} trên tổng số {totalRecords} dòng"
        :rows-per-page-options="[20, 50, 100]"
        @page="onPage"
      >
        <Column field="code" header="Mã BV" style="min-width: 90px; font-family: monospace" />
        <Column field="name" header="Tên bệnh viện / phòng khám" style="min-width: 280px" />
        <Column header="Tên tỉnh" style="min-width: 160px">
          <template #body="{ data }">{{ data.province_name ?? '—' }}</template>
        </Column>
        <Column field="province_code" header="Mã tỉnh" style="min-width: 80px">
          <template #body="{ data }">{{ data.province_code ?? '—' }}</template>
        </Column>
        <Column header="" style="width: 80px; text-align: right">
          <template #body="{ data }">
            <div class="row-actions">
              <Button icon="pi pi-pencil" text rounded severity="secondary" @click="openEdit(data)" />
              <Button icon="pi pi-trash" text rounded severity="danger" @click="confirmDelete(data)" />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Create/Edit Dialog -->
    <Dialog
      v-model:visible="showDialog"
      :header="editingId ? 'Sửa thông tin bệnh viện' : 'Thêm bệnh viện mới'"
      modal
      :style="{ width: '480px' }"
      :closable="!saving"
    >
      <div class="dialog-fields">
        <div class="field">
          <label>Mã bệnh viện <span class="req">*</span></label>
          <InputText
            v-model="form.code"
            :disabled="!!editingId"
            placeholder="VD: 01001"
            class="w-full"
          />
          <small v-if="editingId" class="text-muted">Mã không thể thay đổi sau khi tạo</small>
        </div>
        <div class="field">
          <label>Tên cơ sở KCB <span class="req">*</span></label>
          <InputText v-model="form.name" placeholder="Tên đầy đủ..." class="w-full" />
        </div>
        <div class="field">
          <label>Mã tỉnh</label>
          <InputText v-model="form.province_code" placeholder="VD: 01" class="w-full" />
        </div>
      </div>

      <template #footer>
        <Button label="Hủy" severity="secondary" text :disabled="saving" @click="closeDialog" />
        <Button label="Lưu" icon="pi pi-save" :loading="saving" @click="submitForm" />
      </template>
    </Dialog>

    <!-- Delete Confirm Dialog -->
    <ConfirmDialog />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Column from 'primevue/column'
import ConfirmDialog from 'primevue/confirmdialog'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import bhytClinicService, { type BhytClinicRead } from '@/services/bhytClinicService'

const router = useRouter()
const confirm = useConfirm()
const toast = useToast()

// ── State ─────────────────────────────────────────────────────────────────────

const loading  = ref(false)
const saving   = ref(false)
const items    = ref<BhytClinicRead[]>([])
const total    = ref(0)
const page     = ref(1)
const pageSize = ref(20)

const filters = ref({
  keyword:      '' as string | null,
  province_code: '' as string | null,
})

// ── Load ──────────────────────────────────────────────────────────────────────

async function load() {
  loading.value = true
  try {
    const params = {
      page: page.value,
      page_size: pageSize.value,
      keyword: filters.value.keyword || undefined,
      province_code: filters.value.province_code || undefined,
    }
    const res = await bhytClinicService.list(params)
    items.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

function applyFilter() {
  page.value = 1
  load()
}

function reset() {
  filters.value = { keyword: null, province_code: null }
  page.value = 1
  load()
}

function onPage(e: { page: number; rows: number }) {
  page.value = e.page + 1
  pageSize.value = e.rows
  load()
}

onMounted(load)

// ── Dialog ────────────────────────────────────────────────────────────────────

const showDialog = ref(false)
const editingId  = ref<number | null>(null)

const form = ref({ code: '', name: '', province_code: '' })

function openCreate() {
  editingId.value = null
  form.value = { code: '', name: '', province_code: '' }
  showDialog.value = true
}

function openEdit(item: BhytClinicRead) {
  editingId.value = item.id
  form.value = { code: item.code, name: item.name, province_code: item.province_code ?? '' }
  showDialog.value = true
}

function closeDialog() {
  showDialog.value = false
}

async function submitForm() {
  if (!form.value.code.trim() || !form.value.name.trim()) {
    toast.add({ severity: 'warn', summary: 'Thiếu thông tin', detail: 'Mã và tên bệnh viện là bắt buộc', life: 3000 })
    return
  }
  saving.value = true
  try {
    const payload = {
      code: form.value.code.trim(),
      name: form.value.name.trim(),
      province_code: form.value.province_code.trim() || null,
    }
    if (editingId.value) {
      await bhytClinicService.update(editingId.value, { name: payload.name, province_code: payload.province_code })
    } else {
      await bhytClinicService.create(payload)
    }
    toast.add({ severity: 'success', summary: 'Đã lưu', life: 2000 })
    closeDialog()
    load()
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Lỗi không xác định'
    toast.add({ severity: 'error', summary: 'Lỗi', detail: msg, life: 4000 })
  } finally {
    saving.value = false
  }
}

function confirmDelete(item: BhytClinicRead) {
  confirm.require({
    message: `Xóa bệnh viện "${item.name}" (${item.code})?`,
    header: 'Xác nhận xóa',
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        await bhytClinicService.delete(item.id)
        toast.add({ severity: 'success', summary: 'Đã xóa', life: 2000 })
        load()
      } catch {
        toast.add({ severity: 'error', summary: 'Không thể xóa', life: 3000 })
      }
    },
  })
}
</script>
