<template>
  <div class="section-stack" style="padding-top: 0.75rem">
    <!-- Loading -->
    <div v-if="loading" style="text-align:center; padding:2rem;">
      <i class="pi pi-spin pi-spinner" style="font-size:1.5rem;" />
    </div>

    <template v-else>
      <!-- Empty state: chưa có checklist -->
      <div v-if="!items.length" class="section-card" style="text-align:center; padding:2rem;">
        <i class="pi pi-folder-open" style="font-size:2rem; color:var(--l-text-muted); display:block; margin-bottom:0.75rem" />
        <p style="margin:0 0 1rem; color:var(--l-text-muted)">Chưa có danh mục giấy tờ. Khởi tạo danh mục mặc định hoặc thêm từng loại.</p>
        <Button
          label="Khởi tạo danh mục mặc định"
          icon="pi pi-list-check"
          :loading="initializing"
          @click="initChecklist"
        />
      </div>

      <template v-else>
        <!-- Progress summary -->
        <div class="section-card" style="margin-bottom: 0.5rem">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem">
            <span>{{ submittedCount }} / {{ requiredCount }} giấy tờ bắt buộc đã nộp</span>
            <span style="font-size:0.85rem; color:var(--l-text-muted)">{{ completionRate }}%</span>
          </div>
          <ProgressBar :value="completionRate" :show-value="false" style="height:8px" />
        </div>

        <!-- DataTable -->
        <div class="section-card">
          <div class="section-header" style="margin-bottom:0.5rem">
            <span />
            <Button
              label="Thêm giấy tờ"
              icon="pi pi-plus"
              size="small"
              outlined
              @click="openAddItem"
            />
          </div>
          <DataTable :value="items" size="small" striped-rows>
          <!-- Loại giấy tờ -->
          <Column header="Loại giấy tờ" style="min-width:180px">
            <template #body="{ data }">
              <div style="display:flex; flex-direction:column; gap:0.2rem">
                <span>{{ data.document_type_name }}</span>
                <Tag v-if="data.is_required" value="Bắt buộc" severity="warn" style="font-size:0.7rem; width:fit-content" />
              </div>
            </template>
          </Column>

          <!-- Trạng thái -->
          <Column header="Trạng thái" style="min-width:120px">
            <template #body="{ data }">
              <Tag :value="statusLabel(data.status)" :severity="statusSeverity(data.status)" />
            </template>
          </Column>

          <!-- Ngày nộp -->
          <Column header="Ngày nộp" style="min-width:110px">
            <template #body="{ data }">
              <span>{{ data.submitted_at ? formatDate(data.submitted_at) : '—' }}</span>
            </template>
          </Column>

          <!-- Ngày hết hạn -->
          <Column header="Ngày hết hạn" style="min-width:110px">
            <template #body="{ data }">
              <span :style="(data.is_expiring_soon || data.status === 'expired') ? 'color:var(--p-red-500); font-weight:600' : ''">
                {{ data.expires_at ? formatDate(data.expires_at) : '—' }}
              </span>
              <span v-if="data.is_expiring_soon && data.days_until_expiry !== null" style="font-size:0.75rem; color:var(--p-red-500); display:block">
                Còn {{ data.days_until_expiry }} ngày
              </span>
            </template>
          </Column>

          <!-- File -->
          <Column header="File" style="min-width:80px">
            <template #body="{ data }">
              <Button
                v-if="data.has_file"
                icon="pi pi-download"
                rounded
                text
                size="small"
                v-tooltip.top="data.file_name ?? 'Tải xuống'"
                :loading="actionLoading[`download-${data.id}`]"
                @click="downloadFile(data)"
              />
              <span v-else style="color:var(--l-text-muted)">—</span>
            </template>
          </Column>

          <!-- Thao tác -->
          <Column header="Thao tác" style="min-width:200px">
            <template #body="{ data }">
              <div style="display:flex; gap:0.4rem; flex-wrap:wrap">
                <Button
                  label="Cập nhật"
                  icon="pi pi-pencil"
                  size="small"
                  text
                  @click="openUpdate(data)"
                />
                <Button
                  label="Upload"
                  icon="pi pi-upload"
                  size="small"
                  text
                  severity="secondary"
                  :loading="actionLoading[`upload-${data.id}`]"
                  @click="triggerFileInput(data)"
                />
                <Button
                  v-if="data.has_file"
                  label="Xóa file"
                  icon="pi pi-trash"
                  size="small"
                  text
                  severity="danger"
                  :loading="actionLoading[`deletefile-${data.id}`]"
                  @click="deleteFile(data)"
                />
                <Button
                  v-if="data.status !== 'waived'"
                  label="Miễn"
                  icon="pi pi-ban"
                  size="small"
                  text
                  severity="warn"
                  @click="openWaive(data)"
                />
              </div>
            </template>
          </Column>
        </DataTable>
        </div>
      </template>
    </template>
  </div>

  <!-- Hidden file input -->
  <input
    type="file"
    ref="fileInputRef"
    style="display:none"
    @change="onFileChange"
  />

  <!-- Update dialog -->
  <Dialog v-model:visible="updateVisible" modal header="Cập nhật giấy tờ" style="width:440px">
    <div class="form-grid" style="gap:1rem">
      <div class="col-full">
        <label class="field-label">Trạng thái</label>
        <Select
          v-model="updateForm.status"
          :options="statusOptions"
          option-label="label"
          option-value="value"
          class="w-full"
        />
      </div>
      <div class="col-full">
        <label class="field-label">Ngày nộp</label>
        <DatePicker
          v-model="updateForm.submitted_at_date"
          class="w-full"
          dateFormat="dd/mm/yy"
          show-button-bar
        />
      </div>
      <div class="col-full">
        <label class="field-label">Ngày hết hạn <small style="color:var(--l-text-muted)">(nếu có)</small></label>
        <DatePicker
          v-model="updateForm.expires_at_date"
          class="w-full"
          dateFormat="dd/mm/yy"
          show-button-bar
        />
      </div>
      <div class="col-full">
        <label class="field-label">Ghi chú</label>
        <Textarea v-model="updateForm.note" class="w-full" rows="3" auto-resize />
      </div>
    </div>
    <template #footer>
      <Button label="Hủy" text @click="updateVisible = false" />
      <Button label="Lưu" icon="pi pi-check" :loading="saving" @click="submitUpdate" />
    </template>
  </Dialog>

  <!-- Add item dialog -->
  <Dialog v-model:visible="addItemVisible" modal header="Thêm giấy tờ" style="width:420px">
    <div class="rc-field" style="margin-top:0.5rem">
      <label class="rc-label">Loại giấy tờ <span class="req">*</span></label>
      <Select
        v-model="addItemTypeId"
        :options="availableTypes"
        option-label="name"
        option-value="id"
        filter
        class="w-full"
        placeholder="Chọn loại giấy tờ..."
      />
    </div>
    <template #footer>
      <Button label="Hủy" text @click="addItemVisible = false" />
      <Button label="Thêm" icon="pi pi-plus" :loading="saving" :disabled="!addItemTypeId" @click="submitAddItem" />
    </template>
  </Dialog>

  <!-- Waive dialog -->
  <Dialog v-model:visible="waiveVisible" modal header="Miễn nộp giấy tờ" style="width:400px">
    <div style="margin-bottom:1rem">
      <p style="margin-bottom:0.75rem; color:var(--l-text-muted)">
        Xác nhận miễn nộp: <strong>{{ editingItem?.document_type_name }}</strong>
      </p>
      <label class="field-label">Lý do miễn <span class="required">*</span></label>
      <Textarea v-model="waiveReason" class="w-full" rows="3" auto-resize placeholder="Nhập lý do miễn nộp..." />
    </div>
    <template #footer>
      <Button label="Hủy" text @click="waiveVisible = false" />
      <Button label="Xác nhận miễn" icon="pi pi-ban" severity="warn" :loading="saving" @click="submitWaive" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import ProgressBar from 'primevue/progressbar'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'

import employeeService, { type ChecklistItemRead, type ChecklistItemUpdate } from '@/services/employeeService'
import { documentChecklistService, type DocumentChecklistType } from '@/services/recruitmentService'

const props = defineProps<{ employeeId: number }>()

const toast = useToast()

// ── State ─────────────────────────────────────────────────────────────────────
const loading = ref(false)
const saving  = ref(false)
const items   = ref<ChecklistItemRead[]>([])

const actionLoading = ref<Record<string, boolean>>({})
const initializing  = ref(false)

const fileInputRef    = ref<HTMLInputElement | null>(null)
const pendingUploadId = ref<number | null>(null)

// Add item
const addItemVisible = ref(false)
const addItemTypeId  = ref<number | null>(null)
const allTypes       = ref<DocumentChecklistType[]>([])
const availableTypes = computed(() =>
  allTypes.value.filter((t: DocumentChecklistType) => !items.value.some((i: ChecklistItemRead) => i.document_type_id === t.id))
)

const updateVisible = ref(false)
const waiveVisible  = ref(false)
const editingItem   = ref<ChecklistItemRead | null>(null)
const waiveReason   = ref('')

const updateForm = ref({
  status: '' as string,
  submitted_at_date: null as Date | null,
  expires_at_date:   null as Date | null,
  note: '' as string | null,
})

// ── Options ───────────────────────────────────────────────────────────────────
const statusOptions = [
  { label: 'Chưa nộp',   value: 'not_submitted' },
  { label: 'Đã nộp',     value: 'submitted' },
  { label: 'Được miễn',  value: 'waived' },
]

// ── Computed ──────────────────────────────────────────────────────────────────
const requiredCount = computed(() => items.value.filter((i: ChecklistItemRead) => i.is_required).length)
const submittedCount = computed(() =>
  items.value.filter((i: ChecklistItemRead) => i.is_required && i.status === 'submitted').length,
)
const completionRate = computed(() =>
  requiredCount.value === 0 ? 0 : Math.round((submittedCount.value / requiredCount.value) * 100),
)

// ── Helpers ───────────────────────────────────────────────────────────────────
function statusLabel(status: string): string {
  switch (status) {
    case 'not_submitted': return 'Chưa nộp'
    case 'submitted':     return 'Đã nộp'
    case 'expired':       return 'Hết hạn'
    case 'waived':        return 'Được miễn'
    default:              return status
  }
}

function statusSeverity(status: string): string {
  switch (status) {
    case 'submitted': return 'success'
    case 'waived':    return 'secondary'
    default:          return 'danger'
  }
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

function dateToIso(d: Date | null): string | null {
  if (!d) return null
  return d.toISOString().slice(0, 10)
}

// ── Init / Add ────────────────────────────────────────────────────────────────
async function initChecklist() {
  initializing.value = true
  try {
    const res = await employeeService.initDocumentChecklist(props.employeeId)
    items.value = res.data
    toast.add({ severity: 'success', summary: 'Đã khởi tạo danh mục giấy tờ', life: 2000 })
  } catch (err: any) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: err?.response?.data?.detail ?? 'Không khởi tạo được', life: 4000 })
  } finally {
    initializing.value = false
  }
}

async function openAddItem() {
  if (!allTypes.value.length) {
    allTypes.value = await documentChecklistService.getTypes()
  }
  addItemTypeId.value = null
  addItemVisible.value = true
}

async function submitAddItem() {
  if (!addItemTypeId.value) return
  saving.value = true
  try {
    await employeeService.addChecklistItem(props.employeeId, addItemTypeId.value)
    toast.add({ severity: 'success', summary: 'Đã thêm giấy tờ', life: 2000 })
    addItemVisible.value = false
    await load()
  } catch (err: any) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: err?.response?.data?.detail ?? 'Không thêm được', life: 4000 })
  } finally {
    saving.value = false
  }
}

// ── Load ──────────────────────────────────────────────────────────────────────
async function load() {
  loading.value = true
  try {
    const res = await employeeService.getDocumentChecklist(props.employeeId)
    items.value = res.data
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không tải được danh sách giấy tờ', life: 3000 })
  } finally {
    loading.value = false
  }
}

load()

// ── Update ────────────────────────────────────────────────────────────────────
function openUpdate(item: ChecklistItemRead) {
  editingItem.value = item
  updateForm.value = {
    status: item.status,
    submitted_at_date: item.submitted_at ? new Date(item.submitted_at) : null,
    expires_at_date:   item.expires_at   ? new Date(item.expires_at)   : null,
    note: item.note ?? '',
  }
  updateVisible.value = true
}

async function submitUpdate() {
  if (!editingItem.value) return
  saving.value = true
  try {
    const data: ChecklistItemUpdate = {
      status:       updateForm.value.status,
      submitted_at: dateToIso(updateForm.value.submitted_at_date),
      expires_at:   dateToIso(updateForm.value.expires_at_date),
      note:         updateForm.value.note || null,
    }
    await employeeService.updateChecklistItem(props.employeeId, editingItem.value.id, data)
    toast.add({ severity: 'success', summary: 'Đã cập nhật', life: 2000 })
    updateVisible.value = false
    await load()
  } catch (err: any) {
    const detail = err?.response?.data?.detail
    toast.add({ severity: 'error', summary: 'Lỗi', detail: detail ?? 'Không cập nhật được', life: 4000 })
  } finally {
    saving.value = false
  }
}

// ── Upload file ───────────────────────────────────────────────────────────────
function triggerFileInput(item: ChecklistItemRead) {
  pendingUploadId.value = item.id
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
    fileInputRef.value.click()
  }
}

async function onFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file || pendingUploadId.value === null) return
  const itemId = pendingUploadId.value
  const key = `upload-${itemId}`
  actionLoading.value[key] = true
  try {
    await employeeService.uploadChecklistFile(props.employeeId, itemId, file)
    toast.add({ severity: 'success', summary: 'Đã tải lên', life: 2000 })
    await load()
  } catch (err: any) {
    const detail = err?.response?.data?.detail
    toast.add({ severity: 'error', summary: 'Lỗi', detail: detail ?? 'Không tải lên được file', life: 4000 })
  } finally {
    actionLoading.value[key] = false
    pendingUploadId.value = null
  }
}

// ── Download file ─────────────────────────────────────────────────────────────
async function downloadFile(item: ChecklistItemRead) {
  const key = `download-${item.id}`
  actionLoading.value[key] = true
  try {
    await employeeService.downloadChecklistFile(props.employeeId, item.id, item.file_name ?? `file_${item.id}`)
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không tải xuống được file', life: 3000 })
  } finally {
    actionLoading.value[key] = false
  }
}

// ── Delete file ───────────────────────────────────────────────────────────────
async function deleteFile(item: ChecklistItemRead) {
  const key = `deletefile-${item.id}`
  actionLoading.value[key] = true
  try {
    await employeeService.deleteChecklistFile(props.employeeId, item.id)
    toast.add({ severity: 'success', summary: 'Đã xóa file', life: 2000 })
    await load()
  } catch (err: any) {
    const detail = err?.response?.data?.detail
    toast.add({ severity: 'error', summary: 'Lỗi', detail: detail ?? 'Không xóa được file', life: 4000 })
  } finally {
    actionLoading.value[key] = false
  }
}

// ── Waive ─────────────────────────────────────────────────────────────────────
function openWaive(item: ChecklistItemRead) {
  editingItem.value = item
  waiveReason.value = ''
  waiveVisible.value = true
}

async function submitWaive() {
  if (!editingItem.value) return
  if (!waiveReason.value.trim()) {
    toast.add({ severity: 'warn', summary: 'Cần nhập lý do miễn', life: 2000 })
    return
  }
  saving.value = true
  try {
    await employeeService.waiveChecklistItem(props.employeeId, editingItem.value.id, waiveReason.value.trim())
    toast.add({ severity: 'success', summary: 'Đã miễn', life: 2000 })
    waiveVisible.value = false
    await load()
  } catch (err: any) {
    const detail = err?.response?.data?.detail
    toast.add({ severity: 'error', summary: 'Lỗi', detail: detail ?? 'Không thực hiện được', life: 4000 })
  } finally {
    saving.value = false
  }
}
</script>
