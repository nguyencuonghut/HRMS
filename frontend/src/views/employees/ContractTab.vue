<template>
  <div class="section-stack">

    <!-- Toolbar -->
    <div class="section-header" style="padding: 0.25rem 0 0.5rem;">
      <span class="section-title">Hợp đồng lao động & Phụ lục</span>
      <Button
        v-if="canEdit"
        label="Thêm hợp đồng"
        icon="pi pi-plus"
        size="small"
        @click="openCreate"
      />
    </div>

    <!-- Loading -->
    <div v-if="loading" style="text-align:center; padding:2rem;">
      <i class="pi pi-spin pi-spinner" style="font-size:1.5rem;" />
    </div>

    <!-- Empty -->
    <div v-else-if="contracts.length === 0" class="empty-state">
      <i class="pi pi-file-edit" />
      <span>Chưa có hợp đồng nào</span>
    </div>

    <!-- Contract cards -->
    <template v-else>
      <div v-for="c in contracts" :key="c.id" class="contract-card" :class="statusClass(c.status)">
        <!-- Header -->
        <div class="contract-card-header">
          <div class="contract-header-left">
            <span class="contract-number">{{ c.contract_number }}</span>
            <Tag :value="c.status_display" :severity="tagSeverity(c.status)" />
            <span class="contract-kind-label">{{ kindLabel(c.document_kind) }}</span>
          </div>
          <div class="contract-actions" v-if="canEdit && c.status !== 'terminated'">
            <Button
              icon="pi pi-pencil"
              text rounded size="small"
              v-tooltip.top="'Sửa'"
              @click="openEdit(c)"
            />
            <Button
              icon="pi pi-upload"
              text rounded size="small"
              v-tooltip.top="'Đính kèm file'"
              @click="openUpload(c)"
            />
            <Button
              icon="pi pi-file-word"
              text rounded size="small"
              v-tooltip.top="'Sinh hợp đồng từ mẫu'"
              @click="openGenerate(c)"
            />
            <Button
              icon="pi pi-ban"
              text rounded size="small"
              severity="danger"
              v-tooltip.top="'Hủy hợp đồng'"
              @click="confirmTerminate(c)"
            />
          </div>
        </div>

        <!-- Info grid -->
        <div class="contract-info-grid">
          <div class="contract-info-item">
            <span class="contract-info-label">Loại hợp đồng</span>
            <span class="contract-info-value">{{ c.category_name }}</span>
          </div>
          <div class="contract-info-item">
            <span class="contract-info-label">Ngày ký</span>
            <span class="contract-info-value">{{ formatDate(c.signed_date) }}</span>
          </div>
          <div class="contract-info-item">
            <span class="contract-info-label">Hiệu lực từ</span>
            <span class="contract-info-value">{{ formatDate(c.effective_from) }}</span>
          </div>
          <div class="contract-info-item">
            <span class="contract-info-label">Hiệu lực đến</span>
            <span class="contract-info-value">{{ c.effective_to ? formatDate(c.effective_to) : 'Vô thời hạn' }}</span>
          </div>
          <div class="contract-info-item" v-if="c.insurance_salary">
            <span class="contract-info-label">Lương đóng BH</span>
            <span class="contract-info-value">{{ formatCurrency(c.insurance_salary) }}</span>
          </div>
          <div class="contract-info-item">
            <span class="contract-info-label">Mode BHXH</span>
            <span class="contract-info-value">
              {{ c.insurance_salary_mode === 'computed_by_position_group' ? 'Theo nhóm vị trí + bậc' : 'Cố định theo thỏa thuận' }}
            </span>
          </div>
          <div
            v-if="c.insurance_salary_mode === 'computed_by_position_group' && c.bhxh_position_group_name"
            class="contract-info-item"
          >
            <span class="contract-info-label">Nhóm vị trí BHXH</span>
            <span class="contract-info-value">
              {{ c.bhxh_position_group_name }}
              <template v-if="c.insurance_salary_grade_no"> - Bậc gốc {{ c.insurance_salary_grade_no }}</template>
              <template
                v-if="
                  c.resolved_insurance_salary_grade_no &&
                  c.resolved_insurance_salary_grade_no !== c.insurance_salary_grade_no
                "
              >
                · Bậc áp dụng {{ c.resolved_insurance_salary_grade_no }}
              </template>
            </span>
          </div>
          <div class="contract-info-item" v-if="c.notes">
            <span class="contract-info-label">Ghi chú</span>
            <span class="contract-info-value">{{ c.notes }}</span>
          </div>
        </div>

        <!-- File attachment row -->
        <div v-if="c.has_file || canEdit" class="contract-file-row">
          <template v-if="c.has_file">
            <i class="pi pi-paperclip" style="font-size:0.85rem;" />
            <span class="contract-file-name">{{ c.file_name }}</span>
            <span class="contract-file-size" v-if="c.file_size">({{ formatSize(c.file_size) }})</span>
            <Button
              icon="pi pi-download"
              text rounded size="small"
              v-tooltip.top="'Tải xuống'"
              @click="doDownload(c)"
            />
            <Button
              v-if="canEdit"
              icon="pi pi-trash"
              text rounded size="small"
              severity="danger"
              v-tooltip.top="'Xóa file'"
              @click="confirmDeleteFile(c)"
            />
          </template>
          <template v-else-if="canEdit">
            <Button
              label="Đính kèm file"
              icon="pi pi-upload"
              text size="small"
              @click="openUpload(c)"
            />
          </template>
        </div>

        <!-- Appendices -->
        <div v-if="c.appendices.length > 0" class="contract-appendices">
          <div class="contract-appendices-title">Phụ lục ({{ c.appendices.length }})</div>
          <div v-for="app in c.appendices" :key="app.id" class="contract-appendix-card">
            <div class="contract-card-header">
              <div class="contract-header-left">
                <span class="contract-number" style="font-size:0.875rem;">{{ app.contract_number }}</span>
                <Tag :value="app.status_display" :severity="tagSeverity(app.status)" style="font-size:0.75rem;" />
                <span class="contract-kind-label">{{ app.category_name }}</span>
              </div>
              <div class="contract-actions" v-if="canEdit && app.status !== 'terminated'">
                <Button icon="pi pi-pencil" text rounded size="small" v-tooltip.top="'Sửa'" @click="openEdit(app)" />
                <Button icon="pi pi-upload" text rounded size="small" v-tooltip.top="'Đính kèm file'" @click="openUpload(app)" />
                <Button icon="pi pi-ban" text rounded size="small" severity="danger" v-tooltip.top="'Hủy'" @click="confirmTerminate(app)" />
              </div>
            </div>
            <div class="contract-info-grid" style="margin-top:0.5rem;">
              <div class="contract-info-item">
                <span class="contract-info-label">Ngày ký</span>
                <span class="contract-info-value">{{ formatDate(app.signed_date) }}</span>
              </div>
              <div class="contract-info-item">
                <span class="contract-info-label">Hiệu lực từ</span>
                <span class="contract-info-value">{{ formatDate(app.effective_from) }}</span>
              </div>
              <div class="contract-info-item">
                <span class="contract-info-label">Hiệu lực đến</span>
                <span class="contract-info-value">{{ app.effective_to ? formatDate(app.effective_to) : 'Vô thời hạn' }}</span>
              </div>
            </div>
            <div v-if="app.has_file || canEdit" class="contract-file-row" style="margin-top:0.5rem;">
              <template v-if="app.has_file">
                <i class="pi pi-paperclip" style="font-size:0.85rem;" />
                <span class="contract-file-name">{{ app.file_name }}</span>
                <Button icon="pi pi-download" text rounded size="small" v-tooltip.top="'Tải xuống'" @click="doDownload(app)" />
                <Button v-if="canEdit" icon="pi pi-trash" text rounded size="small" severity="danger" v-tooltip.top="'Xóa file'" @click="confirmDeleteFile(app)" />
              </template>
              <template v-else-if="canEdit">
                <Button label="Đính kèm file" icon="pi pi-upload" text size="small" @click="openUpload(app)" />
              </template>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>

  <!-- Form dialog -->
  <ContractFormDialog
    v-model="formVisible"
    :employee-id="props.employeeId"
    :contract="editingContract"
    :existing-contracts="contracts"
    @saved="handleSaved"
  />

  <!-- Generate dialog -->
  <ContractGenerateDialog
    v-model="generateVisible"
    :employee-id="props.employeeId"
    :contract="generateTarget"
  />

  <!-- Upload dialog -->
  <Dialog v-model:visible="uploadVisible" modal header="Đính kèm file hợp đồng" style="width:420px;">
    <div class="field">
      <label class="field-label">File <span class="req">*</span></label>
      <input
        ref="fileInput"
        type="file"
        accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
        style="display:none;"
        @change="onFileSelected"
      />
      <div class="attachment-upload-zone" @click="(fileInput as HTMLInputElement)?.click()">
        <template v-if="uploadFile">
          <i class="pi pi-check-circle" style="margin-right:0.4rem;" />
          {{ uploadFile.name }} ({{ formatSize(uploadFile.size) }})
        </template>
        <template v-else>
          <i class="pi pi-upload" style="margin-right:0.4rem;" />
          Nhấn để chọn file (PDF, Word, ảnh — tối đa 20 MB)
        </template>
      </div>
      <small v-if="uploadError" class="p-error">{{ uploadError }}</small>
    </div>
    <template #footer>
      <Button label="Hủy" text @click="uploadVisible = false" />
      <Button label="Tải lên" icon="pi pi-upload" :loading="uploading" @click="submitUpload" />
    </template>
  </Dialog>

  <ConfirmDialog group="employee-contracts" />
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import ConfirmDialog from 'primevue/confirmdialog'
import Dialog from 'primevue/dialog'
import Tag from 'primevue/tag'

import { usePermissionGate } from '@/composables/usePermissionGate'
import contractService, { type ContractRead, statusSeverity } from '@/services/contractService'
import ContractFormDialog from './ContractFormDialog.vue'
import ContractGenerateDialog from './ContractGenerateDialog.vue'

const props   = defineProps<{ employeeId: number }>()
const emit    = defineEmits<{ refresh: [] }>()
const confirm = useConfirm()
const toast   = useToast()
const permissionGate = usePermissionGate()
const canEdit = computed(() => permissionGate.canEdit('contracts') || permissionGate.canCreate('contracts'))

// ── State ──────────────────────────────────────────────────────────
const loading   = ref(false)
const contracts = ref<ContractRead[]>([])

// Form dialog
const formVisible     = ref(false)
const editingContract = ref<ContractRead | null>(null)

// Generate dialog
const generateVisible = ref(false)
const generateTarget  = ref<ContractRead | null>(null)

// Upload dialog
const uploadVisible   = ref(false)
const uploadTargetId  = ref<number | null>(null)
const uploadFile      = ref<File | null>(null)
const uploadError     = ref('')
const uploading       = ref(false)
const fileInput       = ref<HTMLInputElement | null>(null)

// ── Helpers ────────────────────────────────────────────────────────
function tagSeverity(status: string) { return statusSeverity(status) }

function kindLabel(kind: string) {
  return kind === 'labor_contract' ? 'Hợp đồng lao động' : 'Phụ lục'
}

function statusClass(status: string) {
  if (status === 'terminated') return 'contract-card--terminated'
  if (status === 'draft')      return 'contract-card--draft'
  return ''
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

function formatCurrency(val: string | null): string {
  if (!val) return '—'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(parseFloat(val))
}

function formatSize(bytes: number | null): string {
  if (!bytes) return ''
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// ── Load ───────────────────────────────────────────────────────────
async function load() {
  loading.value = true
  try {
    const res = await contractService.listContracts(props.employeeId)
    contracts.value = res.data
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không tải được danh sách hợp đồng', life: 3000 })
  } finally {
    loading.value = false
  }
}
load()

async function refreshContractsAndNotify() {
  await load()
  emit('refresh')
}

// ── Create / Edit ──────────────────────────────────────────────────
function openCreate() {
  editingContract.value = null
  formVisible.value = true
}

function openEdit(c: ContractRead) {
  editingContract.value = c
  formVisible.value = true
}

async function handleSaved() {
  await refreshContractsAndNotify()
}

// ── Generate ──────────────────────────────────────────────────────
function openGenerate(c: ContractRead) {
  generateTarget.value = c
  generateVisible.value = true
}

// ── Terminate ─────────────────────────────────────────────────────
function confirmTerminate(c: ContractRead) {
  confirm.require({
    group: 'employee-contracts',
    message: `Hủy hợp đồng "${c.contract_number}"? Thao tác này không thể hoàn tác.`,
    header: 'Xác nhận hủy hợp đồng',
    icon: 'pi pi-exclamation-triangle',
    rejectProps:  { label: 'Không', severity: 'secondary', outlined: true },
    acceptProps:  { label: 'Hủy hợp đồng', severity: 'danger' },
    accept: async () => {
      try {
        await contractService.terminateContract(props.employeeId, c.id)
        toast.add({ severity: 'success', summary: 'Đã hủy hợp đồng', life: 3000 })
        await refreshContractsAndNotify()
      } catch {
        toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không hủy được hợp đồng', life: 4000 })
      }
    },
  })
}

// ── Upload file ────────────────────────────────────────────────────
function openUpload(c: ContractRead) {
  uploadTargetId.value = c.id
  uploadFile.value = null
  uploadError.value = ''
  uploadVisible.value = true
}

function onFileSelected(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (!f) return
  if (f.size > 20 * 1024 * 1024) {
    uploadError.value = 'File vượt quá 20 MB'
    return
  }
  uploadError.value = ''
  uploadFile.value = f
}

async function submitUpload() {
  if (!uploadFile.value || !uploadTargetId.value) {
    uploadError.value = 'Vui lòng chọn file'
    return
  }
  uploading.value = true
  try {
    await contractService.uploadFile(props.employeeId, uploadTargetId.value, uploadFile.value)
    toast.add({ severity: 'success', summary: 'Đã tải lên', life: 3000 })
    uploadVisible.value = false
    await refreshContractsAndNotify()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: unknown } } }
    const detail = err.response?.data?.detail
    toast.add({ severity: 'error', summary: 'Lỗi', detail: typeof detail === 'string' ? detail : 'Không tải được file', life: 4000 })
  } finally {
    uploading.value = false
  }
}

// ── Download file ──────────────────────────────────────────────────
async function doDownload(c: ContractRead) {
  if (!c.file_name) return
  try {
    await contractService.downloadFile(props.employeeId, c.id, c.file_name)
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không tải được file', life: 3000 })
  }
}

// ── Delete file ────────────────────────────────────────────────────
function confirmDeleteFile(c: ContractRead) {
  confirm.require({
    group: 'employee-contracts',
    message: `Xóa file "${c.file_name}" khỏi hợp đồng?`,
    header: 'Xác nhận xóa file',
    icon: 'pi pi-trash',
    rejectProps:  { label: 'Hủy', severity: 'secondary', outlined: true },
    acceptProps:  { label: 'Xóa', severity: 'danger' },
    accept: async () => {
      try {
        await contractService.deleteFile(props.employeeId, c.id)
        toast.add({ severity: 'success', summary: 'Đã xóa file', life: 2000 })
        await refreshContractsAndNotify()
      } catch {
        toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không xóa được file', life: 3000 })
      }
    },
  })
}
</script>
