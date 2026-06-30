<template>
  <div>
    <!-- Page header -->
    <div class="page-header">
      <div>
        <h2>Vị trí công việc</h2>
        <span class="subtitle">Quản lý vị trí dùng riêng hoặc dùng chung cho nhiều đơn vị</span>
      </div>
      <Button v-can:edit="'org'" label="Thêm mới" icon="pi pi-plus" @click="openCreate" />
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
      <Select
        v-model="filterProbationConfigured"
        :options="probationConfiguredOptions"
        option-label="label"
        option-value="value"
        class="toolbar-filter"
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

    <!-- Warning Alert -->
    <div v-if="unconfiguredCount > 0" class="config-alert">
      <div class="config-alert__content">
        <i class="pi pi-exclamation-triangle" />
        <span>
          Còn <strong>{{ unconfiguredCount }}</strong> vị trí chưa cấu hình
          <strong>nhóm thử việc pháp lý</strong>.
        </span>
      </div>
      <Button
        v-if="filterProbationConfigured !== false"
        label="Chỉ xem chưa cấu hình"
        size="small"
        severity="warn"
        outlined
        @click="filterProbationConfigured = false"
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

        <Column field="code"            header="Mã"           sortable style="width: 110px" />
        <Column field="name"            header="Tên vị trí"   sortable style="min-width: 180px" />
        <Column field="department_name" header="Đơn vị quản lý" sortable style="min-width: 170px" />
        <Column header="Phạm vi áp dụng" style="min-width: 240px">
          <template #body="{ data }">
            <div class="scope-cell">
              <Tag
                :value="data.is_shared ? 'Dùng chung' : 'Dùng riêng'"
                :severity="data.is_shared ? 'info' : 'secondary'"
              />
              <span class="scope-summary">
                {{ data.assigned_departments.length }} đơn vị
              </span>
            </div>
            <div class="scope-departments">
              <Tag
                v-for="department in data.assigned_departments.slice(0, 3)"
                :key="department.id"
                :value="department.name"
                severity="contrast"
              />
              <span
                v-if="data.assigned_departments.length > 3"
                class="scope-more"
              >
                +{{ data.assigned_departments.length - 3 }}
              </span>
            </div>
          </template>
        </Column>
        <Column field="job_title_name"  header="Chức danh"    sortable style="width: 140px">
          <template #body="{ data }">{{ data.job_title_name ?? '—' }}</template>
        </Column>
        <Column field="probation_legal_group_label" header="Nhóm thử việc pháp lý" sortable style="min-width: 220px">
          <template #body="{ data }">
            <Tag
              v-if="data.probation_legal_group_label"
              :value="`${data.probation_legal_group_label} (${data.probation_days_limit} ngày)`"
              severity="contrast"
            />
            <Tag
              v-else
              value="Chưa cấu hình"
              severity="warn"
            />
          </template>
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
              <Button v-can:edit="'org'" icon="pi pi-pencil" severity="secondary" text rounded size="small" v-tooltip.top="'Chỉnh sửa'" @click="openEdit(data)" />
              <Button v-can:edit="'org'" icon="pi pi-trash"  severity="danger"    text rounded size="small" v-tooltip.top="'Xóa'"       @click="confirmDelete(data)" />
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

        <!-- Đơn vị quản lý + Chức danh -->
        <div class="field-row">
          <div class="field">
            <label>Đơn vị quản lý <span class="req">*</span></label>
            <Select v-model="form.department_id" :options="deptOptions" option-label="label" option-value="value"
              placeholder="Chọn đơn vị quản lý" class="w-full" filter filter-placeholder="Tìm..." :invalid="!!errors.department_id" @change="onOwnerDepartmentChange" />
            <small v-if="errors.department_id" class="error-msg">{{ errors.department_id }}</small>
          </div>
          <div class="field">
            <label>Chức danh</label>
            <Select v-model="form.job_title_id" :options="jtOptions" option-label="label" option-value="value"
              placeholder="— Không có —" show-clear class="w-full" filter filter-placeholder="Tìm..." />
          </div>
        </div>

        <div class="field">
          <label>Đơn vị áp dụng <span class="req">*</span></label>
          <MultiSelect
            v-model="form.assigned_department_ids"
            :options="deptOptions"
            option-label="label"
            option-value="value"
            filter
            display="chip"
            placeholder="Chọn các đơn vị được phép dùng vị trí này"
            class="w-full"
            :invalid="!!errors.assigned_department_ids"
          />
          <small class="help-msg">
            Đơn vị quản lý sẽ luôn được đưa vào danh sách áp dụng. Nếu chọn nhiều đơn vị, vị trí này sẽ là vị trí dùng chung.
          </small>
          <small v-if="errors.assigned_department_ids" class="error-msg">{{ errors.assigned_department_ids }}</small>
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

        <div class="field">
          <label>Nhóm thử việc pháp lý</label>
          <Select
            v-model="form.probation_legal_group"
            :options="probationLegalGroupOptions"
            option-label="label"
            option-value="value"
            placeholder="— Chưa cấu hình —"
            show-clear
            class="w-full"
          />
          <small class="help-msg">
            Dùng để đối chiếu giới hạn thử việc theo Điều 25 Bộ luật Lao động 2019.
          </small>
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
        <Button v-if="canEditOrg" :label="editingItem ? 'Lưu thay đổi' : 'Tạo mới'" icon="pi pi-check" :loading="submitting" @click="submitForm" />
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
              <div class="detail-row"><span class="detail-label">Đơn vị quản lý</span><span>{{ detailItem.department_name }}</span></div>
              <div class="detail-row">
                <span class="detail-label">Phạm vi áp dụng</span>
                <div class="detail-departments">
                  <Tag
                    :value="detailItem.is_shared ? 'Dùng chung nhiều đơn vị' : 'Dùng riêng một đơn vị'"
                    :severity="detailItem.is_shared ? 'info' : 'secondary'"
                  />
                  <Tag
                    v-for="department in detailItem.assigned_departments"
                    :key="department.id"
                    :value="department.name"
                    severity="contrast"
                  />
                </div>
              </div>
              <div class="detail-row"><span class="detail-label">Bậc mặc định</span><span>{{ detailItem.default_grade }}</span></div>
              <div class="detail-row"><span class="detail-label">PC tính BHXH</span><span>{{ formatVND(detailItem.bhxh_allowance) }}</span></div>
              <div class="detail-row"><span class="detail-label">PC không BHXH</span><span>{{ formatVND(detailItem.non_bhxh_allowance) }}</span></div>
              <div class="detail-row">
                <span class="detail-label">Nhóm thử việc pháp lý</span>
                <span>{{ detailItem.probation_legal_group_label ? `${detailItem.probation_legal_group_label} (${detailItem.probation_days_limit} ngày)` : '—' }}</span>
              </div>
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
import { ref, computed, onMounted, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import { usePermissionGate } from '@/composables/usePermissionGate'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import MultiSelect from 'primevue/multiselect'
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
import jobPositionService, {
  type JobPositionListItem,
  type JobPositionRead,
  type ProbationLegalGroupOption,
} from '@/services/jobPositionService'
import departmentService, { type DepartmentRead } from '@/services/departmentService'
import jobTitleService, { type JobTitleRead } from '@/services/jobTitleService'

interface FormState {
  code:               string
  name:               string
  department_id:      number | null
  assigned_department_ids: number[]
  job_title_id:       number | null
  default_grade:      number
  bhxh_allowance:     number
  non_bhxh_allowance: number
  description:        string
  requirements:       string
  probation_legal_group: string | null
  is_active:          boolean
  employee_code_sequence_id: number | null
  employee_code_rule_note: string
}

// ── State ──────────────────────────────────────────────────────────────────────

const toast   = useToast()
const confirm = useConfirm()
const permissionGate = usePermissionGate()
const canEditOrg = computed(() => permissionGate.canEdit('org'))

const loading      = ref(false)
const list         = ref<JobPositionListItem[]>([])
const flatDepts    = ref<DepartmentRead[]>([])
const jobTitles    = ref<JobTitleRead[]>([])
const sequences    = ref<EmployeeCodeSequenceRead[]>([])
const probationLegalGroups = ref<ProbationLegalGroupOption[]>([])
const filterDeptId = ref<number | null>(null)
const filterActive = ref<boolean | null>(null)
const filterProbationConfigured = ref<boolean | null>(null)
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
  assigned_department_ids: [],
  default_grade: 1, bhxh_allowance: 0, non_bhxh_allowance: 0,
  description: '', requirements: '', probation_legal_group: null, is_active: true,
  employee_code_sequence_id: null, employee_code_rule_note: '',
})
const errors = ref<Partial<Record<keyof FormState, string>>>({})

// ── Constants ──────────────────────────────────────────────────────────────────

const activeFilterOptions = [
  { label: 'Tất cả trạng thái', value: null },
  { label: 'Đang hoạt động',    value: true },
  { label: 'Đã khóa',           value: false },
]

const probationConfiguredOptions = [
  { label: 'Tất cả nhóm thử việc', value: null },
  { label: 'Đã cấu hình', value: true },
  { label: 'Chưa cấu hình', value: false },
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

const probationLegalGroupOptions = computed(() =>
  probationLegalGroups.value.map(item => ({
    label: `${item.label} (${item.probation_days_limit} ngày)`,
    value: item.code,
  }))
)

const filteredList = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  return list.value.filter((item) => {
    if (filterProbationConfigured.value === true && !item.probation_legal_group) return false
    if (filterProbationConfigured.value === false && item.probation_legal_group) return false
    if (!q) return true
    return (
      item.name.toLowerCase().includes(q) ||
      item.code.toLowerCase().includes(q) ||
      item.department_name.toLowerCase().includes(q) ||
      (item.job_title_name ?? '').toLowerCase().includes(q)
    )
  })
})

const unconfiguredCount = computed(() =>
  list.value.filter((item) => !item.probation_legal_group).length
)

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
    const [posRes, deptRes, probationGroupRes] = await Promise.all([
      jobPositionService.getList({
        department_id: filterDeptId.value ?? undefined,
        is_active:     filterActive.value ?? undefined,
      }),
      departmentService.getList(),
      jobPositionService.getProbationLegalGroups(),
    ])
    list.value      = posRes.data
    flatDepts.value = deptRes.data
    probationLegalGroups.value = probationGroupRes.data
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 })
  } finally {
    loading.value = false
  }
}

async function ensureFormLookupsLoaded() {
  if (!canEditOrg.value) return
  const requests: Promise<unknown>[] = []

  if (jobTitles.value.length === 0) {
    requests.push(
      jobTitleService.getList(true).then((response) => {
        jobTitles.value = response.data
      }),
    )
  }

  if (sequences.value.length === 0) {
    requests.push(
      employeeCodeRuleService.getSequences().then((response) => {
        sequences.value = response.data
      }),
    )
  }

  if (requests.length === 0) return
  await Promise.all(requests)
}

// ── CRUD ───────────────────────────────────────────────────────────────────────

function openCreate() {
  editingItem.value = null
  form.value = {
    code: '', name: '', department_id: null, job_title_id: null,
    assigned_department_ids: [],
    default_grade: 1, bhxh_allowance: 0, non_bhxh_allowance: 0,
    description: '', requirements: '', probation_legal_group: null, is_active: true,
    employee_code_sequence_id: null, employee_code_rule_note: '',
  }
  errors.value = {}
  ensureFormLookupsLoaded()
    .then(() => {
      dialogVisible.value = true
    })
    .catch((e) => {
      toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 })
    })
}

async function openEdit(item: JobPositionListItem) {
  try {
    await ensureFormLookupsLoaded()
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 })
    return
  }
  editingItem.value = item
  form.value = {
    code:               item.code,
    name:               item.name,
    department_id:      item.department_id,
    assigned_department_ids: [...item.assigned_department_ids],
    job_title_id:       item.job_title_id,
    default_grade:      1,
    bhxh_allowance:     item.bhxh_allowance,
    non_bhxh_allowance: item.non_bhxh_allowance,
    description:        '',
    requirements:       '',
    probation_legal_group: item.probation_legal_group,
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
    form.value.probation_legal_group = detailRes.data.probation_legal_group
    form.value.assigned_department_ids = [...detailRes.data.assigned_department_ids]
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
  if (!form.value.department_id)                      errors.value.department_id = 'Vui lòng chọn đơn vị quản lý'
  if (!form.value.assigned_department_ids.length)     errors.value.assigned_department_ids = 'Vui lòng chọn ít nhất 1 đơn vị áp dụng'
  return Object.keys(errors.value).length === 0
}

function onOwnerDepartmentChange() {
  if (!form.value.department_id) return
  const nextIds = new Set(form.value.assigned_department_ids)
  nextIds.add(form.value.department_id)
  form.value.assigned_department_ids = Array.from(nextIds)
}

async function submitForm() {
  if (!validate()) return
  submitting.value = true
  try {
    if (editingItem.value) {
      await jobPositionService.update(editingItem.value.id, {
        name:               form.value.name.trim(),
        department_id:      form.value.department_id!,
        assigned_department_ids: form.value.assigned_department_ids,
        job_title_id:       form.value.job_title_id,
        default_grade:      form.value.default_grade,
        bhxh_allowance:     form.value.bhxh_allowance,
        non_bhxh_allowance: form.value.non_bhxh_allowance,
        description:        form.value.description.trim() || null,
        requirements:       form.value.requirements.trim() || null,
        probation_legal_group: form.value.probation_legal_group,
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
        assigned_department_ids: form.value.assigned_department_ids,
        job_title_id:       form.value.job_title_id,
        default_grade:      form.value.default_grade,
        bhxh_allowance:     form.value.bhxh_allowance,
        non_bhxh_allowance: form.value.non_bhxh_allowance,
        description:        form.value.description.trim() || null,
        requirements:       form.value.requirements.trim() || null,
        probation_legal_group: form.value.probation_legal_group,
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

watch([searchQuery, filterProbationConfigured], () => {
  first.value = 0
})
</script>

<style scoped>
.pos-form { display: flex; flex-direction: column; gap: 0.1rem; }
.pos-form .field-row-3 {
  align-items: start;
}
.pos-form .field-row-3 > .field {
  min-width: 0;
}
.pos-form .field-row-3 :deep(.p-inputnumber),
.pos-form .field-row-3 :deep(.p-inputtext) {
  width: 100%;
}
.pos-form .field-row-3 :deep(.p-inputnumber-input) {
  width: 100%;
}
.config-alert {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
  padding: 0.875rem 1rem;
  border: 1px solid color-mix(in srgb, var(--p-orange-400) 40%, transparent);
  border-radius: 0.875rem;
  background: color-mix(in srgb, var(--p-orange-500) 10%, var(--l-surface));
}
.config-alert__content {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: var(--l-text);
}
.config-alert__content i {
  color: var(--p-orange-400);
}
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

.scope-cell {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.scope-summary,
.scope-more {
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}

.scope-departments,
.detail-departments {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-top: 0.35rem;
}

.detail-grid { display: flex; flex-direction: column; gap: 0.75rem; }
.detail-row {
  display: grid; grid-template-columns: 140px 1fr; gap: 0.5rem; align-items: start;
}
.detail-row--full { grid-template-columns: 1fr; }
.detail-label { font-weight: 600; font-size: 0.875rem; color: var(--p-text-muted-color); }
.detail-text  { white-space: pre-wrap; font-size: 0.875rem; }

@media (max-width: 768px) {
  .config-alert {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
