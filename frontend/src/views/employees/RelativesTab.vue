<template>
  <div class="section-stack">

    <!-- ── Banner người liên hệ khẩn cấp ──────────────────────────────── -->
    <div v-if="emergencyContacts.length" class="info-notice is-primary">
      <i class="pi pi-phone" />
      <div>
        <div class="info-label">Người liên hệ khẩn cấp</div>
        <div v-for="ec in emergencyContacts" :key="ec.id" class="info-value">
          {{ ec.full_name }}
          <span class="muted-text"> · {{ relationLabel(ec.relationship_type) }}</span>
          <span v-if="ec.phone_number" class="muted-text"> · {{ ec.phone_number }}</span>
        </div>
      </div>
    </div>

    <!-- ── Danh sách người thân ─────────────────────────────────────────── -->
    <div class="section-card">
      <div class="section-header">
        <span class="section-title">Danh sách người thân</span>
        <Button
          label="Thêm người thân"
          icon="pi pi-plus"
          size="small"
          @click="openCreate"
        />
      </div>

      <div v-if="loading" class="loading-state">
        <i class="pi pi-spin pi-spinner" />
        <span>Đang tải...</span>
      </div>

      <div v-else-if="!relatives.length" class="empty-state">
        <i class="pi pi-users" />
        <span>Chưa có thông tin người thân</span>
      </div>

      <DataTable v-else :value="relatives" size="small" row-hover>
        <Column header="Họ và tên">
          <template #body="{ data }">
            <span class="info-value">{{ data.full_name }}</span>
          </template>
        </Column>
        <Column header="Quan hệ" style="width:110px">
          <template #body="{ data }">{{ relationLabel(data.relationship_type) }}</template>
        </Column>
        <Column header="Ngày sinh" style="width:120px">
          <template #body="{ data }">{{ formatDate(data.date_of_birth) }}</template>
        </Column>
        <Column header="Nghề nghiệp">
          <template #body="{ data }">{{ data.occupation ?? '—' }}</template>
        </Column>
        <Column header="SĐT" style="width:130px">
          <template #body="{ data }">{{ data.phone_number ?? '—' }}</template>
        </Column>
        <Column header="" style="width:40px">
          <template #body="{ data }">
            <Tag v-if="data.is_emergency_contact" value="LH khẩn" severity="warn" />
          </template>
        </Column>
        <Column header="" style="width:80px">
          <template #body="{ data }">
            <div class="action-cell">
              <Button icon="pi pi-pencil" severity="secondary" text rounded size="small" v-tooltip.top="'Sửa'" @click="openEdit(data)" />
              <Button icon="pi pi-trash" severity="danger" text rounded size="small" v-tooltip.top="'Xóa'" @click="confirmDelete(data)" />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- ── Dialog Thêm / Sửa ───────────────────────────────────────────── -->
    <Dialog
      v-model:visible="dialogVisible"
      :header="editingId ? 'Cập nhật người thân' : 'Thêm người thân'"
      :style="{ width: '480px' }"
      modal
      :closable="!submitting"
    >
      <div class="form-grid">
        <div class="field col-full">
          <label>Họ và tên <span class="req">*</span></label>
          <InputText v-model="form.full_name" class="w-full" :invalid="!!errors.full_name" />
          <small v-if="errors.full_name" class="error-msg">{{ errors.full_name }}</small>
        </div>

        <div class="field">
          <label>Quan hệ <span class="req">*</span></label>
          <Select
            v-model="form.relationship_type"
            :options="relationshipOptions"
            option-label="label"
            option-value="value"
            class="w-full"
            :invalid="!!errors.relationship_type"
          />
          <small v-if="errors.relationship_type" class="error-msg">{{ errors.relationship_type }}</small>
        </div>

        <div class="field">
          <label>Ngày sinh</label>
          <DatePicker v-model="form.date_of_birth" class="w-full" dateFormat="dd/mm/yy" :show-clear="true" />
        </div>

        <div class="field">
          <label>Nghề nghiệp</label>
          <InputText v-model="form.occupation" class="w-full" />
        </div>

        <div class="field">
          <label>Số điện thoại</label>
          <InputText v-model="form.phone_number" class="w-full" />
        </div>

        <div class="field col-full">
          <div class="switch-row">
            <ToggleSwitch v-model="form.is_emergency_contact" />
            <label>Người liên hệ khẩn cấp</label>
          </div>
        </div>

        <div class="field col-full">
          <label>Ghi chú</label>
          <Textarea v-model="form.note" class="w-full" rows="2" auto-resize />
        </div>
      </div>

      <template #footer>
        <Button label="Hủy" severity="secondary" outlined :disabled="submitting" @click="dialogVisible = false" />
        <Button :label="editingId ? 'Lưu thay đổi' : 'Thêm'" icon="pi pi-check" :loading="submitting" @click="submit" />
      </template>
    </Dialog>

  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import ToggleSwitch from 'primevue/toggleswitch'

import employeeService, {
  type EmployeeRelativeRead,
  type RelationshipType,
  RELATIONSHIP_LABELS,
} from '@/services/employeeService'

const props = defineProps<{ employeeId: number }>()
const emit  = defineEmits<{ (e: 'refresh'): void }>()

const toast   = useToast()
const confirm = useConfirm()

// ── State ──────────────────────────────────────────────────────────────────────
const loading    = ref(false)
const submitting = ref(false)
const relatives  = ref<EmployeeRelativeRead[]>([])

const emergencyContacts = computed(() => relatives.value.filter(r => r.is_emergency_contact))

const relationshipOptions = Object.entries(RELATIONSHIP_LABELS).map(([value, label]) => ({ value, label }))

// ── Helpers ────────────────────────────────────────────────────────────────────
function relationLabel(type: string): string {
  return RELATIONSHIP_LABELS[type as RelationshipType] ?? type
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
async function loadRelatives() {
  loading.value = true
  try {
    const resp = await employeeService.getRelatives(props.employeeId)
    relatives.value = resp.data
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 })
  } finally {
    loading.value = false
  }
}

onMounted(loadRelatives)
watch(() => props.employeeId, loadRelatives)

// ── Form ───────────────────────────────────────────────────────────────────────
const dialogVisible = ref(false)
const editingId     = ref<number | null>(null)
const errors        = ref<Record<string, string>>({})

const form = ref({
  full_name:            '',
  relationship_type:    null as RelationshipType | null,
  date_of_birth:        null as Date | null,
  occupation:           '',
  phone_number:         '',
  is_emergency_contact: false,
  note:                 '',
})

function resetForm() {
  form.value = {
    full_name: '', relationship_type: null, date_of_birth: null,
    occupation: '', phone_number: '', is_emergency_contact: false, note: '',
  }
  errors.value = {}
}

function openCreate() {
  editingId.value = null
  resetForm()
  dialogVisible.value = true
}

function openEdit(rel: EmployeeRelativeRead) {
  editingId.value = rel.id
  errors.value = {}
  form.value = {
    full_name:            rel.full_name,
    relationship_type:    rel.relationship_type,
    date_of_birth:        rel.date_of_birth ? new Date(rel.date_of_birth) : null,
    occupation:           rel.occupation ?? '',
    phone_number:         rel.phone_number ?? '',
    is_emergency_contact: rel.is_emergency_contact,
    note:                 rel.note ?? '',
  }
  dialogVisible.value = true
}

function validate(): boolean {
  errors.value = {}
  if (!form.value.full_name.trim()) errors.value.full_name = 'Nhập họ và tên'
  if (!form.value.relationship_type)  errors.value.relationship_type = 'Chọn quan hệ'
  return Object.keys(errors.value).length === 0
}

async function submit() {
  if (!validate()) return
  submitting.value = true
  try {
    const payload = {
      full_name:            form.value.full_name.trim(),
      relationship_type:    form.value.relationship_type!,
      date_of_birth:        toIso(form.value.date_of_birth),
      occupation:           form.value.occupation.trim() || null,
      phone_number:         form.value.phone_number.trim() || null,
      is_emergency_contact: form.value.is_emergency_contact,
      note:                 form.value.note.trim() || null,
    }
    if (editingId.value) {
      await employeeService.updateRelative(props.employeeId, editingId.value, payload)
      toast.add({ severity: 'success', summary: 'Đã lưu', detail: 'Thông tin người thân đã được cập nhật', life: 3000 })
    } else {
      await employeeService.createRelative(props.employeeId, payload)
      toast.add({ severity: 'success', summary: 'Đã thêm', detail: 'Người thân đã được thêm vào hồ sơ', life: 3000 })
    }
    dialogVisible.value = false
    await loadRelatives()
    emit('refresh')
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
  } finally {
    submitting.value = false
  }
}

// ── Delete ─────────────────────────────────────────────────────────────────────
function confirmDelete(rel: EmployeeRelativeRead) {
  confirm.require({
    message: `Xóa người thân "${rel.full_name}" khỏi hồ sơ?`,
    header: 'Xác nhận xóa',
    icon: 'pi pi-exclamation-triangle',
    rejectLabel: 'Hủy',
    acceptLabel: 'Xóa',
    acceptSeverity: 'danger',
    accept: async () => {
      try {
        await employeeService.deleteRelative(props.employeeId, rel.id)
        toast.add({ severity: 'success', summary: 'Đã xóa', detail: `Đã xóa ${rel.full_name}`, life: 3000 })
        await loadRelatives()
        emit('refresh')
      } catch (e) {
        toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 })
      }
    },
  })
}
</script>
