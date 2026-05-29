<template>
  <div>
    <!-- Page header -->
    <div class="page-header">
      <div>
        <h2>Chức danh</h2>
        <span class="subtitle">Quản lý chức danh nhân sự</span>
      </div>
      <Button label="Thêm mới" icon="pi pi-plus" @click="openCreate" />
    </div>

    <!-- Toolbar -->
    <div class="toolbar">
      <Select
        v-model="filterActive"
        :options="activeFilterOptions"
        option-label="label"
        option-value="value"
        filter
        class="toolbar-filter"
        @change="loadData"
      />
      <IconField class="toolbar-search">
        <InputIcon class="pi pi-search" />
        <InputText v-model="searchQuery" placeholder="Tìm kiếm theo mã, tên..." class="w-full" />
      </IconField>
      <Button
        icon="pi pi-refresh"
        severity="secondary"
        text
        rounded
        v-tooltip.top="'Làm mới'"
        :loading="loading"
        @click="loadData"
      />
    </div>

    <!-- DataTable -->
    <div class="card">
      <DataTable
        :value="filteredList"
        :loading="loading"
        responsive-layout="scroll"
        :paginator="true"
        :rows="pageRows"
        :rows-per-page-options="[10, 25, 50]"
        :first="first"
        paginator-template="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
        current-page-report-template="Hiển thị từ {first} đến {last} trên tổng số {totalRecords} dòng"
        sort-mode="single"
        @page="handlePage"
      >
        <template #paginatorstart>
          <span class="paginator-info" v-if="paginatorInfo">{{ paginatorInfo }}</span>
        </template>

        <template #empty>
          <div class="empty-state">
            <i class="pi pi-inbox" />
            <span>{{ searchQuery.trim() ? 'Không tìm thấy kết quả phù hợp' : 'Không có dữ liệu' }}</span>
          </div>
        </template>

        <Column field="code"      header="Mã"         sortable style="width: 120px" />
        <Column field="name"      header="Tên chức danh" sortable style="min-width: 200px" />
        <Column field="level"     header="Cấp bậc"    sortable style="width: 100px">
          <template #body="{ data }">
            <span class="center-text">{{ data.level }}</span>
          </template>
        </Column>
        <Column field="is_active" header="Trạng thái" sortable style="width: 130px">
          <template #body="{ data }">
            <Tag
              :value="data.is_active ? 'Hoạt động' : 'Đã khóa'"
              :severity="data.is_active ? 'success' : 'danger'"
            />
          </template>
        </Column>
        <Column header="" style="width: 100px">
          <template #body="{ data }">
            <div class="action-cell">
              <Button
                icon="pi pi-pencil"
                severity="secondary"
                text rounded size="small"
                v-tooltip.top="'Chỉnh sửa'"
                @click="openEdit(data)"
              />
              <Button
                icon="pi pi-trash"
                severity="danger"
                text rounded size="small"
                v-tooltip.top="'Xóa'"
                @click="confirmDelete(data)"
              />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Create / Edit Dialog -->
    <Dialog
      v-model:visible="dialogVisible"
      :header="editingItem ? 'Chỉnh sửa chức danh' : 'Thêm chức danh mới'"
      :style="{ width: '460px' }"
      modal
      :close-on-escape="!submitting"
      :closable="!submitting"
    >
      <form class="jt-form" @submit.prevent="submitForm">
        <!-- Mã (create only) -->
        <div v-if="!editingItem" class="field">
          <label for="f-code">Mã chức danh <span class="req">*</span></label>
          <InputText
            id="f-code"
            v-model="form.code"
            class="w-full"
            placeholder="VD: GD, TP, NV"
            :invalid="!!errors.code"
            autocomplete="off"
          />
          <small v-if="errors.code" class="error-msg">{{ errors.code }}</small>
        </div>

        <!-- Tên chức danh -->
        <div class="field">
          <label for="f-name">Tên chức danh <span class="req">*</span></label>
          <InputText
            id="f-name"
            v-model="form.name"
            class="w-full"
            placeholder="VD: Giám đốc, Trưởng phòng"
            :invalid="!!errors.name"
            autocomplete="off"
          />
          <small v-if="errors.name" class="error-msg">{{ errors.name }}</small>
        </div>

        <!-- Cấp bậc -->
        <div class="field">
          <label for="f-level">Cấp bậc <span class="req">*</span></label>
          <InputNumber
            id="f-level"
            v-model="form.level"
            :min="1"
            :max-fraction-digits="0"
            class="w-full"
            :invalid="!!errors.level"
          />
          <small class="field-hint">1 = cấp cao nhất (Giám đốc), số càng lớn càng thấp</small>
          <small v-if="errors.level" class="error-msg">{{ errors.level }}</small>
        </div>

        <!-- Trạng thái (edit only) -->
        <div v-if="editingItem" class="field field-switch">
          <label>Trạng thái</label>
          <div class="switch-row">
            <ToggleSwitch v-model="form.is_active" />
            <span :class="form.is_active ? 'active-label' : 'inactive-label'">
              {{ form.is_active ? 'Hoạt động' : 'Đã khóa' }}
            </span>
          </div>
        </div>
      </form>

      <template #footer>
        <Button label="Hủy" severity="secondary" outlined :disabled="submitting" @click="dialogVisible = false" />
        <Button
          :label="editingItem ? 'Lưu thay đổi' : 'Tạo mới'"
          icon="pi pi-check"
          :loading="submitting"
          @click="submitForm"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'

import jobTitleService, { type JobTitleRead } from '@/services/jobTitleService'

interface FormState {
  code:      string
  name:      string
  level:     number
  is_active: boolean
}

// ── State ──────────────────────────────────────────────────────────────────────

const toast   = useToast()
const confirm = useConfirm()

const loading     = ref(false)
const list        = ref<JobTitleRead[]>([])
const filterActive = ref<boolean | null>(null)
const searchQuery  = ref('')
const pageRows     = ref(10)
const first        = ref(0)

const dialogVisible = ref(false)
const submitting    = ref(false)
const editingItem   = ref<JobTitleRead | null>(null)

const form = ref<FormState>({ code: '', name: '', level: 1, is_active: true })
const errors = ref<Partial<Record<keyof FormState, string>>>({})

// ── Constants ──────────────────────────────────────────────────────────────────

const activeFilterOptions = [
  { label: 'Tất cả trạng thái', value: null },
  { label: 'Đang hoạt động',    value: true },
  { label: 'Đã khóa',           value: false },
]

// ── Computed ───────────────────────────────────────────────────────────────────

const filteredList = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return list.value
  return list.value.filter(
    i => i.name.toLowerCase().includes(q) || i.code.toLowerCase().includes(q),
  )
})

const paginatorInfo = computed(() => {
  const total = filteredList.value.length
  if (total === 0) return ''
  const from = first.value + 1
  const to   = Math.min(first.value + pageRows.value, total)
  return `Hiển thị ${from}–${to} trên tổng số ${total} dòng`
})

// ── Helpers ────────────────────────────────────────────────────────────────────

function apiError(e: unknown): string {
  const err = e as { response?: { data?: { detail?: unknown } } }
  const detail = err.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((d: { msg: string }) => d.msg).join('; ')
  return typeof detail === 'string' ? detail : 'Đã xảy ra lỗi, vui lòng thử lại'
}

// ── Data loading ───────────────────────────────────────────────────────────────

async function loadData() {
  loading.value = true
  try {
    const resp = await jobTitleService.getList(filterActive.value ?? undefined)
    list.value = resp.data
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 })
  } finally {
    loading.value = false
  }
}

// ── CRUD ───────────────────────────────────────────────────────────────────────

function handlePage(e: { first: number; rows: number }) {
  first.value    = e.first
  pageRows.value = e.rows
}

function openCreate() {
  editingItem.value = null
  form.value = { code: '', name: '', level: 1, is_active: true }
  errors.value = {}
  dialogVisible.value = true
}

function openEdit(item: JobTitleRead) {
  editingItem.value = item
  form.value = { code: item.code, name: item.name, level: item.level, is_active: item.is_active }
  errors.value = {}
  dialogVisible.value = true
}

function validate(): boolean {
  errors.value = {}
  if (!editingItem.value && !form.value.code.trim()) errors.value.code = 'Mã không được để trống'
  if (!form.value.name.trim()) errors.value.name = 'Tên không được để trống'
  if (!form.value.level || form.value.level < 1) errors.value.level = 'Cấp bậc phải ≥ 1'
  return Object.keys(errors.value).length === 0
}

async function submitForm() {
  if (!validate()) return
  submitting.value = true
  try {
    if (editingItem.value) {
      await jobTitleService.update(editingItem.value.id, {
        name:      form.value.name.trim(),
        level:     form.value.level,
        is_active: form.value.is_active,
      })
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã cập nhật chức danh', life: 3000 })
    } else {
      await jobTitleService.create({
        code:  form.value.code.trim(),
        name:  form.value.name.trim(),
        level: form.value.level,
      })
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã tạo chức danh mới', life: 3000 })
    }
    dialogVisible.value = false
    await loadData()
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
  } finally {
    submitting.value = false
  }
}

function confirmDelete(item: JobTitleRead) {
  confirm.require({
    message:     `Bạn có chắc chắn muốn xóa chức danh "${item.name}"?`,
    header:      'Xác nhận xóa',
    icon:        'pi pi-exclamation-triangle',
    acceptLabel: 'Xóa',
    rejectLabel: 'Hủy',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        const res = await jobTitleService.delete(item.id)
        toast.add({ severity: 'success', summary: 'Thành công', detail: res.data.message, life: 3000 })
        await loadData()
      } catch (e) {
        toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
      }
    },
  })
}

onMounted(loadData)
</script>

<style scoped>
.jt-form { display: flex; flex-direction: column; gap: 0.1rem; }
</style>
