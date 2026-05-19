<template>
  <div>
    <!-- Page header -->
    <div class="page-header">
      <div>
        <h2>Vị trí công việc</h2>
        <span class="subtitle">Quản lý vị trí công việc theo phòng/ban</span>
      </div>
      <Button label="Thêm mới" icon="pi pi-plus" @click="openCreate" />
    </div>

    <!-- Toolbar -->
    <div class="toolbar">
      <Select
        v-model="filterDeptId"
        :options="deptOptions"
        option-label="label"
        option-value="value"
        placeholder="Tất cả phòng/ban"
        show-clear
        filter
        class="toolbar-filter"
        @change="loadData"
      />
      <Select
        v-model="filterActive"
        :options="activeFilterOptions"
        option-label="label"
        option-value="value"
        filter
        class="toolbar-filter-sm"
        @change="loadData"
      />
      <IconField class="toolbar-search">
        <InputIcon class="pi pi-search" />
        <InputText v-model="searchQuery" placeholder="Tìm theo mã, tên..." class="w-full" />
      </IconField>
      <Button
        icon="pi pi-refresh"
        severity="secondary"
        text rounded
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
        paginator-template="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink"
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

        <Column field="code"            header="Mã"           sortable style="width: 110px" />
        <Column field="name"            header="Tên vị trí"   sortable style="min-width: 180px" />
        <Column field="department_name" header="Phòng/Ban"    sortable style="min-width: 150px" />
        <Column field="job_title_name"  header="Chức danh"    sortable style="width: 140px">
          <template #body="{ data }">{{ data.job_title_name ?? '—' }}</template>
        </Column>
        <Column field="bhxh_allowance"  header="PC BHXH"      sortable style="width: 120px">
          <template #body="{ data }">
            <span class="right-text">{{ formatVND(data.bhxh_allowance) }}</span>
          </template>
        </Column>
        <Column field="is_active"       header="Trạng thái"   sortable style="width: 120px">
          <template #body="{ data }">
            <Tag :value="data.is_active ? 'Hoạt động' : 'Đã khóa'" :severity="data.is_active ? 'success' : 'danger'" />
          </template>
        </Column>
        <Column header="" style="width: 110px">
          <template #body="{ data }">
            <div class="action-cell">
              <Button icon="pi pi-eye"    severity="secondary" text rounded size="small" v-tooltip.top="'Chi tiết'" @click="openDetail(data)" />
              <Button icon="pi pi-pencil" severity="secondary" text rounded size="small" v-tooltip.top="'Chỉnh sửa'" @click="openEdit(data)" />
              <Button icon="pi pi-trash"  severity="danger"    text rounded size="small" v-tooltip.top="'Xóa'"       @click="confirmDelete(data)" />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Create / Edit Dialog -->
    <Dialog
      v-model:visible="dialogVisible"
      :header="editingItem ? 'Chỉnh sửa vị trí' : 'Thêm vị trí mới'"
      :style="{ width: '580px' }"
      modal
      :close-on-escape="!submitting"
      :closable="!submitting"
    >
      <form class="pos-form" @submit.prevent="submitForm">
        <!-- Mã (create only) -->
        <div v-if="!editingItem" class="field">
          <label for="f-code">Mã vị trí <span class="req">*</span></label>
          <InputText id="f-code" v-model="form.code" class="w-full" placeholder="VD: TP_KT, NV_HC"
            :invalid="!!errors.code" autocomplete="off" />
          <small v-if="errors.code" class="error-msg">{{ errors.code }}</small>
        </div>

        <!-- Tên vị trí -->
        <div class="field">
          <label for="f-name">Tên vị trí <span class="req">*</span></label>
          <InputText id="f-name" v-model="form.name" class="w-full" placeholder="VD: Trưởng phòng Kế toán"
            :invalid="!!errors.name" autocomplete="off" />
          <small v-if="errors.name" class="error-msg">{{ errors.name }}</small>
        </div>

        <!-- Phòng/Ban + Chức danh -->
        <div class="field-row">
          <div class="field">
            <label>Phòng/Ban <span class="req">*</span></label>
            <Select v-model="form.department_id" :options="deptOptions" option-label="label" option-value="value"
              placeholder="Chọn phòng/ban" class="w-full" filter filter-placeholder="Tìm..." :invalid="!!errors.department_id" />
            <small v-if="errors.department_id" class="error-msg">{{ errors.department_id }}</small>
          </div>
          <div class="field">
            <label>Chức danh</label>
            <Select v-model="form.job_title_id" :options="jtOptions" option-label="label" option-value="value"
              placeholder="— Không có —" show-clear class="w-full" filter filter-placeholder="Tìm..." />
          </div>
        </div>

        <!-- Bậc + Phụ cấp BHXH + Phụ cấp không BHXH -->
        <div class="field-row-3">
          <div class="field">
            <label>Bậc mặc định <span class="req">*</span></label>
            <InputNumber v-model="form.default_grade" :min="1" :max-fraction-digits="0" class="w-full" />
          </div>
          <div class="field">
            <label>PC tính BHXH (₫)</label>
            <InputNumber v-model="form.bhxh_allowance" :min="0" :max-fraction-digits="0"
              :use-grouping="true" class="w-full" />
          </div>
          <div class="field">
            <label>PC không BHXH (₫)</label>
            <InputNumber v-model="form.non_bhxh_allowance" :min="0" :max-fraction-digits="0"
              :use-grouping="true" class="w-full" />
          </div>
        </div>

        <!-- Mô tả -->
        <div class="field">
          <label>Mô tả công việc</label>
          <Textarea v-model="form.description" rows="3" class="w-full" placeholder="Tóm tắt công việc chính..." auto-resize />
        </div>

        <!-- Yêu cầu -->
        <div class="field">
          <label>Yêu cầu tuyển dụng</label>
          <Textarea v-model="form.requirements" rows="3" class="w-full" placeholder="Kinh nghiệm, bằng cấp..." auto-resize />
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

        <div v-if="editingItem" class="fieldset-block">
          <div class="fieldset-title">Hệ mã nhân viên</div>
          <div class="field">
            <label>Hệ áp dụng trực tiếp</label>
            <Select
              v-model="form.employee_code_sequence_id"
              :options="sequenceOptions"
              option-label="label"
              option-value="value"
              placeholder="— Không cấu hình trực tiếp —"
              show-clear
              filter
              class="w-full"
            />
            <small class="help-msg">Bỏ trống để vị trí này không có rule trực tiếp.</small>
            <small class="help-msg">Hệ 1: mặc định toàn công ty. Hệ 2: công nhân bốc xếp, ra cám, tạp vụ. Hệ 3: công nhân, bảo vệ thuộc Phòng trại.</small>
          </div>
          <div class="field">
            <label>Ghi chú rule</label>
            <InputText
              v-model="form.employee_code_rule_note"
              class="w-full"
              placeholder="Ghi chú nội bộ (không bắt buộc)"
              autocomplete="off"
            />
          </div>
        </div>
      </form>

      <template #footer>
        <Button label="Hủy" severity="secondary" outlined :disabled="submitting" @click="dialogVisible = false" />
        <Button :label="editingItem ? 'Lưu thay đổi' : 'Tạo mới'" icon="pi pi-check" :loading="submitting" @click="submitForm" />
      </template>
    </Dialog>

    <!-- Detail Dialog -->
    <Dialog v-model:visible="detailVisible" header="Chi tiết vị trí công việc" :style="{ width: '620px' }" modal>
      <Tabs v-if="detailItem" value="info">
        <TabList>
          <Tab value="info">Thông tin</Tab>
          <Tab value="attachments">Tài liệu đính kèm</Tab>
        </TabList>
        <TabPanels>
          <TabPanel value="info">
            <div class="detail-grid mt-3">
              <div class="detail-row"><span class="detail-label">Mã</span><span>{{ detailItem.code }}</span></div>
              <div class="detail-row"><span class="detail-label">Tên vị trí</span><span>{{ detailItem.name }}</span></div>
              <div class="detail-row"><span class="detail-label">Bậc mặc định</span><span>{{ detailItem.default_grade }}</span></div>
              <div class="detail-row"><span class="detail-label">PC tính BHXH</span><span>{{ formatVND(detailItem.bhxh_allowance) }}</span></div>
              <div class="detail-row"><span class="detail-label">PC không BHXH</span><span>{{ formatVND(detailItem.non_bhxh_allowance) }}</span></div>
              <div v-if="detailItem.description" class="detail-row detail-row--full">
                <span class="detail-label">Mô tả</span>
                <span class="detail-text">{{ detailItem.description }}</span>
              </div>
              <div v-if="detailItem.requirements" class="detail-row detail-row--full">
                <span class="detail-label">Yêu cầu</span>
                <span class="detail-text">{{ detailItem.requirements }}</span>
              </div>
            </div>
          </TabPanel>
          <TabPanel value="attachments">
            <div class="mt-3">
              <FileAttachmentList :position-id="detailItem.id" />
            </div>
          </TabPanel>
        </TabPanels>
      </Tabs>
      <template #footer>
        <Button label="Đóng" severity="secondary" outlined @click="detailVisible = false" />
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
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Tabs from 'primevue/tabs'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import ToggleSwitch from 'primevue/toggleswitch'

import FileAttachmentList from '@/components/FileAttachmentList.vue'
import employeeCodeRuleService, { type EmployeeCodeSequenceRead } from '@/services/employeeCodeRuleService'
import jobPositionService, { type JobPositionListItem, type JobPositionRead } from '@/services/jobPositionService'
import departmentService, { type DepartmentRead } from '@/services/departmentService'
import jobTitleService, { type JobTitleRead } from '@/services/jobTitleService'

interface FormState {
  code:               string
  name:               string
  department_id:      number | null
  job_title_id:       number | null
  default_grade:      number
  bhxh_allowance:     number
  non_bhxh_allowance: number
  description:        string
  requirements:       string
  is_active:          boolean
  employee_code_sequence_id: number | null
  employee_code_rule_note: string
}

// ── State ──────────────────────────────────────────────────────────────────────

const toast   = useToast()
const confirm = useConfirm()

const loading      = ref(false)
const list         = ref<JobPositionListItem[]>([])
const flatDepts    = ref<DepartmentRead[]>([])
const jobTitles    = ref<JobTitleRead[]>([])
const sequences    = ref<EmployeeCodeSequenceRead[]>([])
const filterDeptId = ref<number | null>(null)
const filterActive = ref<boolean | null>(null)
const searchQuery  = ref('')
const pageRows     = ref(10)
const first        = ref(0)

const dialogVisible = ref(false)
const submitting    = ref(false)
const editingItem   = ref<JobPositionListItem | null>(null)

const detailVisible = ref(false)
const detailItem    = ref<JobPositionRead | null>(null)

const form = ref<FormState>({
  code: '', name: '', department_id: null, job_title_id: null,
  default_grade: 1, bhxh_allowance: 0, non_bhxh_allowance: 0,
  description: '', requirements: '', is_active: true,
  employee_code_sequence_id: null, employee_code_rule_note: '',
})
const errors = ref<Partial<Record<keyof FormState, string>>>({})

// ── Constants ──────────────────────────────────────────────────────────────────

const activeFilterOptions = [
  { label: 'Tất cả trạng thái', value: null },
  { label: 'Đang hoạt động',    value: true },
  { label: 'Đã khóa',           value: false },
]

// ── Computed ───────────────────────────────────────────────────────────────────

const deptOptions = computed(() =>
  flatDepts.value.map(d => ({ label: `${d.name} (${d.code})`, value: d.id }))
)

const jtOptions = computed(() =>
  jobTitles.value.map(jt => ({ label: `${jt.name} (${jt.code})`, value: jt.id }))
)

const sequenceOptions = computed(() =>
  sequences.value.map(s => ({
    label: s.description ? `${s.name} (${s.code}) - ${s.description}` : `${s.name} (${s.code})`,
    value: s.id,
  }))
)

const filteredList = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return list.value
  return list.value.filter(
    i => i.name.toLowerCase().includes(q) || i.code.toLowerCase().includes(q)
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

function formatVND(val: number): string {
  if (!val) return '—'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(val)
}

function apiError(e: unknown): string {
  const err = e as { response?: { data?: { detail?: unknown } } }
  const detail = err.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((d: { msg: string }) => d.msg).join('; ')
  return typeof detail === 'string' ? detail : 'Đã xảy ra lỗi, vui lòng thử lại'
}

// ── Data loading ───────────────────────────────────────────────────────────────

function handlePage(e: { first: number; rows: number }) {
  first.value    = e.first
  pageRows.value = e.rows
}

async function loadData() {
  loading.value = true
  try {
    const [posRes, deptRes, jtRes, seqRes] = await Promise.all([
      jobPositionService.getList({
        department_id: filterDeptId.value ?? undefined,
        is_active:     filterActive.value ?? undefined,
      }),
      departmentService.getList(),
      jobTitleService.getList(true),
      employeeCodeRuleService.getSequences(),
    ])
    list.value      = posRes.data
    flatDepts.value = deptRes.data
    jobTitles.value = jtRes.data
    sequences.value = seqRes.data
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 })
  } finally {
    loading.value = false
  }
}

// ── CRUD ───────────────────────────────────────────────────────────────────────

function openCreate() {
  editingItem.value = null
  form.value = {
    code: '', name: '', department_id: null, job_title_id: null,
    default_grade: 1, bhxh_allowance: 0, non_bhxh_allowance: 0,
    description: '', requirements: '', is_active: true,
    employee_code_sequence_id: null, employee_code_rule_note: '',
  }
  errors.value = {}
  dialogVisible.value = true
}

async function openEdit(item: JobPositionListItem) {
  editingItem.value = item
  form.value = {
    code:               item.code,
    name:               item.name,
    department_id:      item.department_id,
    job_title_id:       item.job_title_id,
    default_grade:      1,
    bhxh_allowance:     item.bhxh_allowance,
    non_bhxh_allowance: item.non_bhxh_allowance,
    description:        '',
    requirements:       '',
    is_active:          item.is_active,
    employee_code_sequence_id: null,
    employee_code_rule_note: '',
  }
  errors.value = {}
  try {
    const [detailRes, ruleRes] = await Promise.all([
      jobPositionService.getById(item.id),
      employeeCodeRuleService.getJobPositionRule(item.id),
    ])
    form.value.default_grade  = detailRes.data.default_grade
    form.value.description    = detailRes.data.description ?? ''
    form.value.requirements   = detailRes.data.requirements ?? ''
    form.value.employee_code_sequence_id = ruleRes.data?.employee_code_sequence_id ?? null
    form.value.employee_code_rule_note = ruleRes.data?.note ?? ''
  } catch (e) {
    toast.add({ severity: 'warn', summary: 'Cảnh báo', detail: `Không tải đủ cấu hình hệ mã: ${apiError(e)}`, life: 4000 })
  }
  dialogVisible.value = true
}

async function openDetail(item: JobPositionListItem) {
  try {
    const res = await jobPositionService.getById(item.id)
    detailItem.value   = res.data
    detailVisible.value = true
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 })
  }
}

function validate(): boolean {
  errors.value = {}
  if (!editingItem.value && !form.value.code.trim()) errors.value.code = 'Mã không được để trống'
  if (!form.value.name.trim())                        errors.value.name = 'Tên không được để trống'
  if (!form.value.department_id)                      errors.value.department_id = 'Vui lòng chọn phòng/ban'
  return Object.keys(errors.value).length === 0
}

async function submitForm() {
  if (!validate()) return
  submitting.value = true
  try {
    if (editingItem.value) {
      await jobPositionService.update(editingItem.value.id, {
        name:               form.value.name.trim(),
        department_id:      form.value.department_id!,
        job_title_id:       form.value.job_title_id,
        default_grade:      form.value.default_grade,
        bhxh_allowance:     form.value.bhxh_allowance,
        non_bhxh_allowance: form.value.non_bhxh_allowance,
        description:        form.value.description.trim() || null,
        requirements:       form.value.requirements.trim() || null,
        is_active:          form.value.is_active,
      })
      if (form.value.employee_code_sequence_id) {
        await employeeCodeRuleService.upsertJobPositionRule(editingItem.value.id, {
          employee_code_sequence_id: form.value.employee_code_sequence_id,
          note: form.value.employee_code_rule_note.trim() || null,
        })
      } else {
        try {
          await employeeCodeRuleService.deleteJobPositionRule(editingItem.value.id)
        } catch {
          // no direct rule to delete
        }
      }
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã cập nhật vị trí công việc', life: 3000 })
    } else {
      await jobPositionService.create({
        code:               form.value.code.trim(),
        name:               form.value.name.trim(),
        department_id:      form.value.department_id!,
        job_title_id:       form.value.job_title_id,
        default_grade:      form.value.default_grade,
        bhxh_allowance:     form.value.bhxh_allowance,
        non_bhxh_allowance: form.value.non_bhxh_allowance,
        description:        form.value.description.trim() || null,
        requirements:       form.value.requirements.trim() || null,
      })
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã tạo vị trí mới', life: 3000 })
    }
    dialogVisible.value = false
    await loadData()
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
  } finally {
    submitting.value = false
  }
}

function confirmDelete(item: JobPositionListItem) {
  confirm.require({
    message:     `Bạn có chắc chắn muốn xóa vị trí "${item.name}"?`,
    header:      'Xác nhận xóa',
    icon:        'pi pi-exclamation-triangle',
    acceptLabel: 'Xóa',
    rejectLabel: 'Hủy',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        const res = await jobPositionService.delete(item.id)
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
.pos-form { display: flex; flex-direction: column; gap: 0.1rem; }
.fieldset-block {
  margin-top: 0.5rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--p-content-border-color);
}
.fieldset-title {
  margin-bottom: 0.75rem;
  font-weight: 600;
}
.help-msg {
  color: var(--p-text-muted-color);
}

.detail-grid { display: flex; flex-direction: column; gap: 0.75rem; }
.detail-row {
  display: grid; grid-template-columns: 140px 1fr; gap: 0.5rem; align-items: start;
}
.detail-row--full { grid-template-columns: 1fr; }
.detail-label { font-weight: 600; font-size: 0.875rem; color: var(--p-text-muted-color); }
.detail-text  { white-space: pre-wrap; font-size: 0.875rem; }
</style>
