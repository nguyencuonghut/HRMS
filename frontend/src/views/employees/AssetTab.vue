<template>
  <div class="section-stack">

    <!-- ── Danh sách tài sản cấp phát ───────────────────────────────────── -->
    <div class="section-card">
      <div class="section-header">
        <span class="section-title">Tài sản đã cấp phát</span>
        <Button
          v-can:edit="'employees'"
          label="Cấp phát tài sản"
          icon="pi pi-plus"
          size="small"
          @click="openCreate"
        />
      </div>

      <div v-if="loading" class="loading-state">
        <i class="pi pi-spin pi-spinner" />
        <span>Đang tải...</span>
      </div>

      <div v-else-if="!assets.length" class="empty-state">
        <i class="pi pi-desktop" />
        <span>Chưa cấp phát tài sản nào</span>
      </div>

      <DataTable v-else :value="assets" size="small" row-hover>
        <Column header="Tên tài sản">
          <template #body="{ data }">
            <span class="info-value">{{ data.asset_name }}</span>
          </template>
        </Column>
        <Column header="Phân loại" style="width:140px">
          <template #body="{ data }">
            <Tag :value="typeLabel(data.asset_type)" :severity="typeSeverity(data.asset_type)" />
          </template>
        </Column>
        <Column header="Ngày cấp" style="width:120px">
          <template #body="{ data }">{{ formatDate(data.handover_date) }}</template>
        </Column>
        <Column header="Ngày thu hồi" style="width:120px">
          <template #body="{ data }">{{ formatDate(data.return_date) }}</template>
        </Column>
        <Column header="Trạng thái" style="width:130px">
          <template #body="{ data }">
            <Tag :value="statusLabel(data.status)" :severity="statusSeverity(data.status)" />
          </template>
        </Column>
        <Column header="Ghi chú">
          <template #body="{ data }">
            <span class="text-sm text-muted">{{ data.note ?? '—' }}</span>
          </template>
        </Column>
        <Column header="" style="width:80px">
          <template #body="{ data }">
            <div class="action-cell">
              <Button v-can:edit="'employees'" icon="pi pi-pencil" severity="secondary" text rounded size="small" v-tooltip.top="'Sửa'" @click="openEdit(data)" />
              <Button v-can:edit="'employees'" icon="pi pi-trash" severity="danger" text rounded size="small" v-tooltip.top="'Xóa'" @click="confirmDelete(data)" />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- ── Dialog Cấp phát / Cập nhật tài sản ───────────────────────────────── -->
    <Dialog
      v-model:visible="dialogVisible"
      :header="editingId ? 'Cập nhật cấp phát tài sản' : 'Cấp phát tài sản mới'"
      :style="{ width: '480px' }"
      modal
      :closable="!submitting"
    >
      <div class="form-grid">
        <div class="field col-full">
          <label>Tên tài sản <span class="req">*</span></label>
          <InputText v-model="form.asset_name" class="w-full" placeholder="Ví dụ: Laptop Dell Latitude 5420" :invalid="!!errors.asset_name" />
          <small v-if="errors.asset_name" class="error-msg">{{ errors.asset_name }}</small>
        </div>

        <div class="field">
          <label>Phân loại tài sản <span class="req">*</span></label>
          <Select
            v-model="form.asset_type"
            :options="typeOptions"
            option-label="label"
            option-value="value"
            class="w-full"
            placeholder="Chọn phân loại..."
            :invalid="!!errors.asset_type"
          />
          <small v-if="errors.asset_type" class="error-msg">{{ errors.asset_type }}</small>
        </div>

        <div class="field">
          <label>Trạng thái <span class="req">*</span></label>
          <Select
            v-model="form.status"
            :options="statusOptions"
            option-label="label"
            option-value="value"
            class="w-full"
            :invalid="!!errors.status"
          />
          <small v-if="errors.status" class="error-msg">{{ errors.status }}</small>
        </div>

        <div class="field">
          <label>Ngày cấp phát <span class="req">*</span></label>
          <DatePicker v-model="form.handover_date" class="w-full" dateFormat="dd/mm/yy" :invalid="!!errors.handover_date" />
          <small v-if="errors.handover_date" class="error-msg">{{ errors.handover_date }}</small>
        </div>

        <div class="field">
          <label>Ngày thu hồi</label>
          <DatePicker v-model="form.return_date" class="w-full" dateFormat="dd/mm/yy" :show-clear="true" />
        </div>

        <div class="field col-full">
          <label>Ghi chú</label>
          <Textarea v-model="form.note" class="w-full" rows="3" placeholder="Ghi chú thêm thông tin (như tình trạng, cấu hình sơ bộ)..." auto-resize />
        </div>
      </div>

      <template #footer>
        <Button label="Hủy" severity="secondary" outlined :disabled="submitting" @click="dialogVisible = false" />
        <Button v-can:edit="'employees'" :label="editingId ? 'Lưu thay đổi' : 'Cấp phát'" icon="pi pi-check" :loading="submitting" @click="submit" />
      </template>
    </Dialog>

  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'

import employeeService, {
  type EmployeeAssetRead,
  type AssetType,
  type AssetStatus,
  ASSET_TYPE_LABELS,
  ASSET_STATUS_LABELS,
} from '@/services/employeeService'

const props = defineProps<{ employeeId: number }>()

const toast   = useToast()
const confirm = useConfirm()

// ── State ──────────────────────────────────────────────────────────────────────
const loading    = ref(false)
const submitting = ref(false)
const assets     = ref<EmployeeAssetRead[]>([])

const typeOptions = Object.entries(ASSET_TYPE_LABELS).map(([value, label]) => ({ value, label }))
const statusOptions = Object.entries(ASSET_STATUS_LABELS).map(([value, label]) => ({ value, label }))

// ── Helpers ────────────────────────────────────────────────────────────────────
function typeLabel(type: string): string {
  return ASSET_TYPE_LABELS[type as AssetType] ?? type
}

function typeSeverity(type: string): string {
  switch (type) {
    case 'laptop':
    case 'pc':
      return 'info'
    case 'projector':
      return 'warn'
    case 'phone_sim':
      return 'success'
    default:
      return 'secondary'
  }
}

function statusLabel(status: string): string {
  return ASSET_STATUS_LABELS[status as AssetStatus] ?? status
}

function statusSeverity(status: string): string {
  switch (status) {
    case 'allocated': return 'info'
    case 'returned':  return 'success'
    case 'lost':
    case 'damaged':   return 'danger'
    default:          return 'secondary'
  }
}

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
async function loadAssets() {
  loading.value = true
  try {
    const resp = await employeeService.getAssets(props.employeeId)
    assets.value = resp.data
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 })
  } finally {
    loading.value = false
  }
}

onMounted(loadAssets)
watch(() => props.employeeId, loadAssets)

// ── Form ───────────────────────────────────────────────────────────────────────
const dialogVisible = ref(false)
const editingId     = ref<number | null>(null)
const errors        = ref<Record<string, string>>({})

const form = ref({
  asset_name:    '',
  asset_type:    null as AssetType | null,
  handover_date: null as Date | null,
  return_date:   null as Date | null,
  status:        'allocated' as AssetStatus,
  note:          '',
})

function openCreate() {
  editingId.value = null
  errors.value = {}
  form.value = {
    asset_name:    '',
    asset_type:    null,
    handover_date: new Date(),
    return_date:   null,
    status:        'allocated',
    note:          '',
  }
  dialogVisible.value = true
}

function openEdit(item: EmployeeAssetRead) {
  editingId.value = item.id
  errors.value = {}
  form.value = {
    asset_name:    item.asset_name,
    asset_type:    item.asset_type,
    handover_date: item.handover_date ? new Date(item.handover_date) : null,
    return_date:   item.return_date ? new Date(item.return_date) : null,
    status:        item.status,
    note:          item.note ?? '',
  }
  dialogVisible.value = true
}

function validate(): boolean {
  const err: Record<string, string> = {}
  if (!form.value.asset_name.trim()) err.asset_name = 'Tên tài sản là bắt buộc'
  if (!form.value.asset_type) err.asset_type = 'Phân loại tài sản là bắt buộc'
  if (!form.value.handover_date) err.handover_date = 'Ngày cấp phát là bắt buộc'
  if (!form.value.status) err.status = 'Trạng thái là bắt buộc'

  errors.value = err
  return Object.keys(err).length === 0
}

async function submit() {
  if (!validate()) return
  submitting.value = true
  try {
    const payload = {
      asset_name:    form.value.asset_name.trim(),
      asset_type:    form.value.asset_type!,
      handover_date: toIso(form.value.handover_date)!,
      return_date:   toIso(form.value.return_date),
      status:        form.value.status,
      note:          form.value.note.trim() || null,
    }

    if (editingId.value) {
      await employeeService.updateAsset(props.employeeId, editingId.value, payload)
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã cập nhật tài sản cấp phát', life: 2000 })
    } else {
      await employeeService.createAsset(props.employeeId, payload)
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã cấp phát tài sản mới', life: 2000 })
    }
    dialogVisible.value = false
    await loadAssets()
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 })
  } finally {
    submitting.value = false
  }
}

// ── Delete ─────────────────────────────────────────────────────────────────────
function confirmDelete(item: EmployeeAssetRead) {
  confirm.require({
    message: `Bạn có chắc chắn muốn xóa bản ghi cấp phát tài sản "${item.asset_name}"?`,
    header: 'Xác nhận xóa',
    icon: 'pi pi-exclamation-triangle',
    rejectProps: {
      label: 'Hủy',
      severity: 'secondary',
      outlined: true,
    },
    acceptProps: {
      label: 'Xóa',
      severity: 'danger',
    },
    accept: async () => {
      try {
        await employeeService.deleteAsset(props.employeeId, item.id)
        toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã xóa bản ghi cấp phát', life: 2000 })
        await loadAssets()
      } catch (e) {
        toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 })
      }
    },
  })
}
</script>

<style scoped>
.action-cell {
  display: flex;
  justify-content: flex-end;
  gap: 0.25rem;
}
</style>
