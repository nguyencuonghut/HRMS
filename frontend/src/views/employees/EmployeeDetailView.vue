<template>
  <div class="employee-detail-page">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <Button
          icon="pi pi-arrow-left"
          severity="secondary"
          text rounded
          v-tooltip.bottom="'Quay lại danh sách'"
          @click="router.push('/employees')"
        />
        <div>
          <h2 v-if="isNew">Thêm nhân viên mới</h2>
          <template v-else>
            <h2>{{ employee?.full_name }}</h2>
            <div class="header-meta">
              <code class="emp-code">{{ employee?.display_code }}</code>
              <Tag :value="statusLabel(employee?.status)" :severity="statusSeverity(employee?.status)" />
              <Tag v-if="!employee?.is_active" value="Đã vô hiệu hóa" severity="danger" />
            </div>
          </template>
        </div>
      </div>

      <div class="header-actions" v-if="!isNew">
        <Button
          v-if="!editing"
          label="Chỉnh sửa"
          icon="pi pi-pencil"
          @click="startEdit"
        />
        <template v-else>
          <Button label="Hủy" severity="secondary" outlined :disabled="submitting" @click="cancelEdit" />
          <Button label="Lưu" icon="pi pi-check" :loading="submitting" @click="save" />
        </template>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="fetchLoading" class="loading-state">
      <i class="pi pi-spin pi-spinner" />
      <span>Đang tải hồ sơ...</span>
    </div>

    <!-- Error -->
    <div v-else-if="fetchError" class="error-state">
      <i class="pi pi-exclamation-circle" />
      <span>{{ fetchError }}</span>
    </div>

    <!-- Form / Detail -->
    <template v-else>
      <Tabs v-model:value="activeTab">
        <TabList>
          <Tab value="basic">Thông tin cơ bản</Tab>
          <Tab value="docs">Giấy tờ nhận dạng</Tab>
          <Tab value="contact">Liên lạc & Thuế</Tab>
          <Tab value="address">Địa chỉ</Tab>
          <Tab value="bank" :disabled="isNew">Tài khoản ngân hàng</Tab>
          <Tab value="job" :disabled="isNew">Công việc</Tab>
          <Tab value="relatives" :disabled="isNew">Người thân</Tab>
          <Tab value="education" :disabled="isNew">Học vấn & KN</Tab>
          <Tab value="attachments" :disabled="isNew">Tài liệu</Tab>
          <Tab value="contracts" :disabled="isNew">Hợp đồng</Tab>
        </TabList>

        <TabPanels>
          <!-- ── TAB 1: Thông tin cơ bản ──────────────────────────────────── -->
          <TabPanel value="basic">
            <div class="form-grid">
              <div class="field col-full">
                <label>Họ và tên <span class="req">*</span></label>
                <InputText v-model="form.full_name" class="w-full" :disabled="viewOnly" :invalid="!!errors.full_name" />
                <small v-if="errors.full_name" class="error-msg">{{ errors.full_name }}</small>
              </div>

              <div class="field">
                <label>Họ (last name) <span class="req">*</span></label>
                <InputText v-model="form.last_name" class="w-full" :disabled="viewOnly" :invalid="!!errors.last_name" />
                <small v-if="errors.last_name" class="error-msg">{{ errors.last_name }}</small>
              </div>

              <div class="field">
                <label>Tên (first name) <span class="req">*</span></label>
                <InputText v-model="form.first_name" class="w-full" :disabled="viewOnly" :invalid="!!errors.first_name" />
                <small v-if="errors.first_name" class="error-msg">{{ errors.first_name }}</small>
              </div>

              <div class="field">
                <label>Ngày sinh <span class="req">*</span></label>
                <DatePicker v-model="form.date_of_birth_date" class="w-full" dateFormat="dd/mm/yy" :disabled="viewOnly" :invalid="!!errors.date_of_birth" />
                <small v-if="errors.date_of_birth" class="error-msg">{{ errors.date_of_birth }}</small>
              </div>

              <div class="field">
                <label>Giới tính <span class="req">*</span></label>
                <Select
                  v-model="form.gender"
                  :options="genderOptions"
                  option-label="label"
                  option-value="value"
                  filter
                  class="w-full"
                  :disabled="viewOnly"
                  :invalid="!!errors.gender"
                />
                <small v-if="errors.gender" class="error-msg">{{ errors.gender }}</small>
              </div>

              <div class="field">
                <label>Quốc tịch <span class="req">*</span></label>
                <NationalitySelect v-model="form.nationality_id" :disabled="viewOnly" />
                <small v-if="errors.nationality_id" class="error-msg">{{ errors.nationality_id }}</small>
              </div>

              <div class="field">
                <label>Dân tộc</label>
                <EthnicitySelect v-model="form.ethnicity_id" :disabled="viewOnly" />
              </div>

              <div class="field">
                <label>Tôn giáo</label>
                <ReligionSelect v-model="form.religion_id" :disabled="viewOnly" />
              </div>

              <div class="field">
                <label>Trạng thái nhân sự <span class="req">*</span></label>
                <Select
                  v-model="form.status"
                  :options="statusOptions"
                  option-label="label"
                  option-value="value"
                  filter
                  class="w-full"
                  :disabled="viewOnly"
                />
              </div>

              <div class="field">
                <label>Ngày vào làm <span class="req">*</span></label>
                <DatePicker v-model="form.start_date_date" class="w-full" dateFormat="dd/mm/yy" :disabled="viewOnly" :invalid="!!errors.start_date" />
                <small v-if="errors.start_date" class="error-msg">{{ errors.start_date }}</small>
              </div>

              <div class="field" v-if="form.status === 'resigned'">
                <label>Ngày nghỉ việc</label>
                <DatePicker v-model="form.resigned_date_date" class="w-full" dateFormat="dd/mm/yy" :disabled="viewOnly" />
              </div>

              <template v-if="isNew">
                <div class="field-sep col-full">
                  <label class="section-label">Công việc hiện hành khi tạo mới</label>
                </div>

                <div class="field">
                  <label>Phòng ban <span class="req">*</span></label>
                  <Select
                    v-model="form.initial_department_id"
                    :options="departments"
                    option-label="name"
                    option-value="id"
                    filter
                    class="w-full"
                    :invalid="!!errors.initial_department_id"
                    @update:model-value="onInitialDepartmentChange"
                  />
                  <small v-if="errors.initial_department_id" class="error-msg">{{ errors.initial_department_id }}</small>
                </div>

                <div class="field">
                  <label>Chức danh</label>
                  <Select
                    v-model="form.initial_job_title_id"
                    :options="jobTitles"
                    option-label="name"
                    option-value="id"
                    filter
                    show-clear
                    class="w-full"
                  />
                </div>

                <div class="field">
                  <label>Vị trí công việc</label>
                  <Select
                    v-model="form.initial_job_position_id"
                    :options="filteredPositions"
                    option-label="name"
                    option-value="id"
                    filter
                    show-clear
                    class="w-full"
                    :disabled="!form.initial_department_id"
                    @update:model-value="onInitialJobPositionChange"
                  />
                </div>

                <div class="field">
                  <label>Ngày hiệu lực công việc <span class="req">*</span></label>
                  <DatePicker
                    v-model="form.initial_job_effective_from_date"
                    class="w-full"
                    dateFormat="dd/mm/yy"
                    :invalid="!!errors.initial_job_effective_from"
                  />
                  <small v-if="errors.initial_job_effective_from" class="error-msg">{{ errors.initial_job_effective_from }}</small>
                </div>
              </template>
            </div>

            <div class="tab-actions" v-if="isNew">
              <Button label="Tạo nhân viên" icon="pi pi-check" :loading="submitting" @click="save" />
            </div>
          </TabPanel>

          <!-- ── TAB 2: Giấy tờ ───────────────────────────────────────────── -->
          <TabPanel value="docs">
            <div class="form-grid">
              <div class="field">
                <label>Số CCCD / CMND <span class="req">*</span></label>
                <InputText v-model="form.id_number" class="w-full" :disabled="viewOnly" :invalid="!!errors.id_number" />
                <small v-if="errors.id_number" class="error-msg">{{ errors.id_number }}</small>
              </div>

              <div class="field">
                <label>Ngày cấp <span class="req">*</span></label>
                <DatePicker v-model="form.id_issued_on_date" class="w-full" dateFormat="dd/mm/yy" :disabled="viewOnly" :invalid="!!errors.id_issued_on" />
                <small v-if="errors.id_issued_on" class="error-msg">{{ errors.id_issued_on }}</small>
              </div>

              <div class="field col-full">
                <label>Nơi cấp <span class="req">*</span></label>
                <InputText v-model="form.id_issued_by" class="w-full" :disabled="viewOnly" :invalid="!!errors.id_issued_by" />
                <small v-if="errors.id_issued_by" class="error-msg">{{ errors.id_issued_by }}</small>
              </div>

              <div class="field">
                <label>Ngày hết hạn CCCD</label>
                <DatePicker v-model="form.id_expires_on_date" class="w-full" dateFormat="dd/mm/yy" :disabled="viewOnly" />
              </div>

              <div class="field-sep col-full">
                <label class="section-label">
                  <ToggleSwitch v-model="hasPassport" :disabled="viewOnly" />
                  Có hộ chiếu
                </label>
              </div>

              <template v-if="hasPassport">
                <div class="field">
                  <label>Số hộ chiếu</label>
                  <InputText v-model="form.passport_number" class="w-full" :disabled="viewOnly" />
                </div>
                <div class="field">
                  <label>Ngày cấp HC</label>
                  <DatePicker v-model="form.passport_issued_on_date" class="w-full" dateFormat="dd/mm/yy" :disabled="viewOnly" />
                </div>
                <div class="field">
                  <label>Ngày hết hạn HC</label>
                  <DatePicker v-model="form.passport_expires_on_date" class="w-full" dateFormat="dd/mm/yy" :disabled="viewOnly" />
                </div>
              </template>

              <div class="field-sep col-full">
                <label class="section-label">
                  <ToggleSwitch v-model="hasWorkPermit" :disabled="viewOnly" />
                  Có giấy phép lao động (người nước ngoài)
                </label>
              </div>

              <template v-if="hasWorkPermit">
                <div class="field">
                  <label>Số GPLĐ</label>
                  <InputText v-model="form.work_permit_number" class="w-full" :disabled="viewOnly" />
                </div>
                <div class="field">
                  <label>Ngày cấp GPLĐ</label>
                  <DatePicker v-model="form.work_permit_issued_on_date" class="w-full" dateFormat="dd/mm/yy" :disabled="viewOnly" />
                </div>
                <div class="field">
                  <label>Ngày hết hạn GPLĐ</label>
                  <DatePicker v-model="form.work_permit_expires_on_date" class="w-full" dateFormat="dd/mm/yy" :disabled="viewOnly" />
                </div>
              </template>
            </div>

            <div class="tab-actions" v-if="isNew">
              <Button label="Tạo nhân viên" icon="pi pi-check" :loading="submitting" @click="save" />
            </div>
          </TabPanel>

          <!-- ── TAB 3: Liên lạc & Thuế ───────────────────────────────────── -->
          <TabPanel value="contact">
            <div class="form-grid">
              <div class="field">
                <label>Số điện thoại</label>
                <InputText v-model="form.phone_number" class="w-full" :disabled="viewOnly" />
              </div>
              <div class="field">
                <label>Email cá nhân</label>
                <InputText v-model="form.personal_email" class="w-full" :disabled="viewOnly" />
              </div>
              <div class="field">
                <label>Mã số thuế cá nhân</label>
                <InputText v-model="form.personal_tax_code" class="w-full" :disabled="viewOnly" />
              </div>
              <div class="field">
                <label>Mã số BHXH</label>
                <InputText v-model="form.bhxh_code" class="w-full" :disabled="viewOnly" />
              </div>
            </div>
            <div class="tab-actions" v-if="isNew">
              <Button label="Tạo nhân viên" icon="pi pi-check" :loading="submitting" @click="save" />
            </div>
          </TabPanel>

          <!-- ── TAB 4: Địa chỉ ───────────────────────────────────────────── -->
          <TabPanel value="address">
            <div v-if="isNew" class="info-notice">
              <i class="pi pi-info-circle" />
              Tạo nhân viên trước, sau đó quay lại tab này để nhập địa chỉ.
            </div>
            <template v-else>
              <div class="address-section">
                <h4>Hộ khẩu thường trú</h4>
                <AddressEditor
                  :employee-id="employeeId!"
                  address-type="permanent"
                  :initial="permanentAddress"
                  :disabled="viewOnly"
                  @saved="loadAddresses"
                />
              </div>
              <div class="address-section">
                <h4>Địa chỉ liên lạc</h4>
                <AddressEditor
                  :employee-id="employeeId!"
                  address-type="contact"
                  :initial="contactAddress"
                  :disabled="viewOnly"
                  @saved="loadAddresses"
                />
              </div>
            </template>
          </TabPanel>

          <!-- ── TAB 5: Tài khoản ngân hàng ──────────────────────────────── -->
          <TabPanel value="bank">
            <div class="bank-section">
              <div class="bank-header">
                <h4>Tài khoản ngân hàng</h4>
                <Button label="Thêm tài khoản" icon="pi pi-plus" size="small" @click="openBankDialog(null)" />
              </div>

              <div v-if="bankAccounts.length === 0" class="empty-state">
                <i class="pi pi-credit-card" />
                <span>Chưa có tài khoản ngân hàng nào</span>
              </div>

              <div v-else class="bank-list">
                <div v-for="acc in bankAccounts" :key="acc.id" class="bank-card" :class="{ primary: acc.is_primary }">
                  <div class="bank-info">
                    <div class="bank-number">{{ acc.account_number }}</div>
                    <div class="bank-name">{{ acc.account_name }}</div>
                    <div class="bank-meta">
                      <span>Bank ID: {{ acc.bank_id }}</span>
                      <span v-if="acc.branch_name"> · {{ acc.branch_name }}</span>
                    </div>
                  </div>
                  <div class="bank-badges">
                    <Tag v-if="acc.is_primary" value="Nhận lương" severity="success" />
                  </div>
                  <div class="bank-actions">
                    <Button icon="pi pi-pencil" severity="secondary" text rounded size="small" v-tooltip.top="'Sửa'" @click="openBankDialog(acc)" />
                    <Button icon="pi pi-trash" severity="danger" text rounded size="small" v-tooltip.top="'Xóa'" @click="confirmDeleteBank(acc)" />
                  </div>
                </div>
              </div>
            </div>
          </TabPanel>

          <!-- ── TAB: Công việc ──────────────────────────────────────────── -->
          <TabPanel value="job">
            <JobRecordTab
              v-if="!isNew && employeeId"
              :employee-id="employeeId"
              :is-new="isNew"
              @refresh="loadEmployee"
            />
          </TabPanel>

          <!-- ── TAB: Người thân ─────────────────────────────────────────── -->
          <TabPanel value="relatives">
            <RelativesTab
              v-if="!isNew && employeeId"
              :employee-id="employeeId"
              @refresh="loadEmployee"
            />
          </TabPanel>

          <!-- ── TAB: Học vấn & Kinh nghiệm ───────────────────────────────── -->
          <TabPanel value="education">
            <EducationTab
              v-if="!isNew && employeeId"
              :employee-id="employeeId"
              @refresh="loadEmployee"
            />
          </TabPanel>

          <!-- ── TAB: Tài liệu đính kèm ───────────────────────────────────── -->
          <TabPanel value="attachments">
            <AttachmentsTab
              v-if="!isNew && employeeId"
              :employee-id="employeeId"
            />
          </TabPanel>

          <!-- ── TAB: Hợp đồng lao động ──────────────────────────────────── -->
          <TabPanel value="contracts">
            <ContractTab
              v-if="!isNew && employeeId"
              :employee-id="employeeId"
            />
          </TabPanel>
        </TabPanels>
      </Tabs>
    </template>

    <!-- Bank account dialog -->
    <Dialog
      v-model:visible="bankDialogVisible"
      :header="editingBank ? 'Cập nhật tài khoản ngân hàng' : 'Thêm tài khoản ngân hàng'"
      :style="{ width: '480px' }"
      modal
      :closable="!bankSubmitting"
    >
      <div class="form-grid">
        <div class="field col-full">
          <label>Ngân hàng <span class="req">*</span></label>
          <BankSelect v-model="bankForm.bank_id" />
        </div>
        <div class="field">
          <label>Số tài khoản <span class="req">*</span></label>
          <InputText v-model="bankForm.account_number" class="w-full" :invalid="!!bankErrors.account_number" />
          <small v-if="bankErrors.account_number" class="error-msg">{{ bankErrors.account_number }}</small>
        </div>
        <div class="field">
          <label>Tên chủ tài khoản <span class="req">*</span></label>
          <InputText v-model="bankForm.account_name" class="w-full" :invalid="!!bankErrors.account_name" />
          <small v-if="bankErrors.account_name" class="error-msg">{{ bankErrors.account_name }}</small>
        </div>
        <div class="field col-full">
          <label>Chi nhánh</label>
          <InputText v-model="bankForm.branch_name" class="w-full" />
        </div>
        <div class="field col-full">
          <div class="switch-row">
            <ToggleSwitch v-model="bankForm.is_primary" />
            <label>Tài khoản nhận lương mặc định</label>
          </div>
        </div>
      </div>
      <template #footer>
        <Button label="Hủy" severity="secondary" outlined :disabled="bankSubmitting" @click="bankDialogVisible = false" />
        <Button :label="editingBank ? 'Lưu thay đổi' : 'Thêm'" icon="pi pi-check" :loading="bankSubmitting" @click="submitBank" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import Button from 'primevue/button'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Tabs from 'primevue/tabs'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'

import NationalitySelect from '@/components/catalog/NationalitySelect.vue'
import EthnicitySelect from '@/components/catalog/EthnicitySelect.vue'
import ReligionSelect from '@/components/catalog/ReligionSelect.vue'
import BankSelect from '@/components/catalog/BankSelect.vue'
import AddressEditor from './AddressEditor.vue'
import JobRecordTab from './JobRecordTab.vue'
import RelativesTab from './RelativesTab.vue'
import EducationTab from './EducationTab.vue'
import AttachmentsTab from './AttachmentsTab.vue'
import ContractTab from './ContractTab.vue'
import departmentService, { type DepartmentRead } from '@/services/departmentService'
import jobTitleService, { type JobTitleRead } from '@/services/jobTitleService'
import jobPositionService, { type JobPositionListItem } from '@/services/jobPositionService'

import employeeService, {
  type EmployeeRead,
  type EmployeeAddressRead,
  type EmployeeBankAccountRead,
  type GenderType,
  type StatusType,
} from '@/services/employeeService'

const route   = useRoute()
const router  = useRouter()
const toast   = useToast()
const confirm = useConfirm()

// ── Route resolution ───────────────────────────────────────────────────────────
const isNew       = computed(() => route.params.id === 'new')
const employeeId  = computed(() => isNew.value ? null : parseInt(route.params.id as string))

// ── Fetch state ────────────────────────────────────────────────────────────────
const fetchLoading = ref(false)
const fetchError   = ref('')
const employee     = ref<EmployeeRead | null>(null)
const addresses    = ref<EmployeeAddressRead[]>([])
const bankAccounts = ref<EmployeeBankAccountRead[]>([])
const departments  = ref<DepartmentRead[]>([])
const jobTitles    = ref<JobTitleRead[]>([])
const allPositions = ref<JobPositionListItem[]>([])

const permanentAddress = computed(() => addresses.value.find(a => a.address_type === 'permanent') ?? null)
const contactAddress   = computed(() => addresses.value.find(a => a.address_type === 'contact') ?? null)
const filteredPositions = computed(() =>
  form.value.initial_department_id
    ? allPositions.value.filter(p => p.department_id === form.value.initial_department_id)
    : []
)

// ── Edit state ─────────────────────────────────────────────────────────────────
const editing   = ref(false)
const submitting = ref(false)
const activeTab  = ref('basic')
const errors     = ref<Record<string, string>>({})

const viewOnly = computed(() => !isNew.value && !editing.value)

// ── Form model ────────────────────────────────────────────────────────────────
const form = ref({
  full_name: '',
  last_name: '',
  first_name: '',
  date_of_birth_date: null as Date | null,
  gender: 'male' as GenderType,
  nationality_id: null as number | null,
  ethnicity_id: null as number | null,
  religion_id: null as number | null,
  status: 'probation' as StatusType,
  start_date_date: null as Date | null,
  resigned_date_date: null as Date | null,
  initial_department_id: null as number | null,
  initial_job_title_id: null as number | null,
  initial_job_position_id: null as number | null,
  initial_job_effective_from_date: null as Date | null,
  id_number: '',
  id_issued_on_date: null as Date | null,
  id_issued_by: '',
  id_expires_on_date: null as Date | null,
  passport_number: null as string | null,
  passport_issued_on_date: null as Date | null,
  passport_expires_on_date: null as Date | null,
  work_permit_number: null as string | null,
  work_permit_issued_on_date: null as Date | null,
  work_permit_expires_on_date: null as Date | null,
  phone_number: null as string | null,
  personal_email: null as string | null,
  personal_tax_code: null as string | null,
  bhxh_code: null as string | null,
})

const hasPassport   = ref(false)
const hasWorkPermit = ref(false)

// ── Options ────────────────────────────────────────────────────────────────────
const genderOptions = [
  { label: 'Nam', value: 'male' },
  { label: 'Nữ', value: 'female' },
  { label: 'Khác', value: 'other' },
]

const statusOptions = [
  { label: 'Thử việc',    value: 'probation' },
  { label: 'Chính thức',  value: 'official' },
  { label: 'Nghỉ dài hạn', value: 'long_leave' },
  { label: 'Đã nghỉ việc', value: 'resigned' },
]

// ── Helpers ────────────────────────────────────────────────────────────────────
function statusLabel(s?: string): string {
  const map: Record<string, string> = {
    probation: 'Thử việc', official: 'Chính thức',
    long_leave: 'Nghỉ dài hạn', resigned: 'Đã nghỉ',
  }
  return s ? (map[s] ?? s) : ''
}

function statusSeverity(s?: string): 'warn' | 'success' | 'secondary' | 'danger' {
  const map: Record<string, 'warn' | 'success' | 'secondary' | 'danger'> = {
    probation: 'warn', official: 'success',
    long_leave: 'secondary', resigned: 'danger',
  }
  return s ? (map[s] ?? 'secondary') : 'secondary'
}

function toDate(iso: string | null | undefined): Date | null {
  return iso ? new Date(iso) : null
}

function toIso(d: Date | null): string | null {
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

// ── Fill form from employee ────────────────────────────────────────────────────
function fillForm(emp: EmployeeRead) {
  form.value = {
    full_name: emp.full_name,
    last_name: emp.last_name,
    first_name: emp.first_name,
    date_of_birth_date: toDate(emp.date_of_birth),
    gender: emp.gender as GenderType,
    nationality_id: emp.nationality_id,
    ethnicity_id: emp.ethnicity_id,
    religion_id: emp.religion_id,
    status: emp.status as StatusType,
    start_date_date: toDate(emp.start_date),
    resigned_date_date: toDate(emp.resigned_date),
    initial_department_id: null,
    initial_job_title_id: null,
    initial_job_position_id: null,
    initial_job_effective_from_date: null,
    id_number: emp.id_number,
    id_issued_on_date: toDate(emp.id_issued_on),
    id_issued_by: emp.id_issued_by,
    id_expires_on_date: toDate(emp.id_expires_on),
    passport_number: emp.passport_number,
    passport_issued_on_date: toDate(emp.passport_issued_on),
    passport_expires_on_date: toDate(emp.passport_expires_on),
    work_permit_number: emp.work_permit_number,
    work_permit_issued_on_date: toDate(emp.work_permit_issued_on),
    work_permit_expires_on_date: toDate(emp.work_permit_expires_on),
    phone_number: emp.phone_number,
    personal_email: emp.personal_email,
    personal_tax_code: emp.personal_tax_code,
    bhxh_code: emp.bhxh_code,
  }
  hasPassport.value   = !!emp.passport_number
  hasWorkPermit.value = !!emp.work_permit_number
}

// ── Load data ──────────────────────────────────────────────────────────────────
async function loadEmployee() {
  if (isNew.value || !employeeId.value) return
  fetchLoading.value = true
  fetchError.value = ''
  try {
    const resp = await employeeService.get(employeeId.value)
    employee.value = resp.data
    addresses.value = resp.data.addresses
    bankAccounts.value = resp.data.bank_accounts
    fillForm(resp.data)
  } catch {
    fetchError.value = 'Không tìm thấy hoặc không thể tải hồ sơ nhân viên'
  } finally {
    fetchLoading.value = false
  }
}

async function loadAddresses() {
  if (!employeeId.value) return
  const resp = await employeeService.getAddresses(employeeId.value)
  addresses.value = resp.data
}

async function loadCatalogs() {
  const [deptResp, titleResp, positionResp] = await Promise.all([
    departmentService.getList(true),
    jobTitleService.getList(true),
    jobPositionService.getList({ is_active: true }),
  ])
  departments.value = deptResp.data
  jobTitles.value = titleResp.data
  allPositions.value = positionResp.data
}

// ── Edit ───────────────────────────────────────────────────────────────────────
function startEdit() { editing.value = true }

function cancelEdit() {
  editing.value = false
  errors.value = {}
  if (employee.value) fillForm(employee.value)
}

function onInitialDepartmentChange() {
  form.value.initial_job_position_id = null
}

function onInitialJobPositionChange(positionId: number | null) {
  const position = filteredPositions.value.find(item => item.id === positionId)
  if (position?.job_title_id) {
    form.value.initial_job_title_id = position.job_title_id
  }
}

// ── Validate ───────────────────────────────────────────────────────────────────
function validate(): boolean {
  errors.value = {}
  if (!form.value.full_name.trim()) errors.value.full_name = 'Họ tên không được để trống'
  if (!form.value.last_name.trim()) errors.value.last_name = 'Không được để trống'
  if (!form.value.first_name.trim()) errors.value.first_name = 'Không được để trống'
  if (!form.value.date_of_birth_date) errors.value.date_of_birth = 'Ngày sinh không được để trống'
  if (!form.value.gender) errors.value.gender = 'Chọn giới tính'
  if (!form.value.nationality_id) errors.value.nationality_id = 'Chọn quốc tịch'
  if (!form.value.id_number.trim()) errors.value.id_number = 'Số CCCD không được để trống'
  if (!form.value.id_issued_on_date) errors.value.id_issued_on = 'Ngày cấp không được để trống'
  if (!form.value.id_issued_by.trim()) errors.value.id_issued_by = 'Nơi cấp không được để trống'
  if (!form.value.start_date_date) errors.value.start_date = 'Ngày vào làm không được để trống'
  if (isNew.value && !form.value.initial_department_id) errors.value.initial_department_id = 'Chọn phòng ban hiện hành'
  if (isNew.value && !form.value.initial_job_effective_from_date) errors.value.initial_job_effective_from = 'Chọn ngày hiệu lực công việc'
  return Object.keys(errors.value).length === 0
}

// ── Save ───────────────────────────────────────────────────────────────────────
async function save() {
  if (!validate()) {
    if (errors.value.full_name || errors.value.last_name || errors.value.first_name ||
        errors.value.date_of_birth || errors.value.gender || errors.value.nationality_id ||
        errors.value.start_date) {
      activeTab.value = 'basic'
    } else if (errors.value.id_number || errors.value.id_issued_on || errors.value.id_issued_by) {
      activeTab.value = 'docs'
    }
    return
  }

  submitting.value = true
  try {
    const payload = {
      full_name: form.value.full_name.trim(),
      last_name: form.value.last_name.trim(),
      first_name: form.value.first_name.trim(),
      date_of_birth: toIso(form.value.date_of_birth_date)!,
      gender: form.value.gender,
      nationality_id: form.value.nationality_id!,
      ethnicity_id: form.value.ethnicity_id,
      religion_id: form.value.religion_id,
      status: form.value.status,
      start_date: toIso(form.value.start_date_date)!,
      resigned_date: form.value.status === 'resigned' ? toIso(form.value.resigned_date_date) : null,
      initial_department_id: isNew.value ? form.value.initial_department_id : undefined,
      initial_job_title_id: isNew.value ? form.value.initial_job_title_id : undefined,
      initial_job_position_id: isNew.value ? form.value.initial_job_position_id : undefined,
      initial_job_effective_from: isNew.value ? toIso(form.value.initial_job_effective_from_date) : undefined,
      id_number: form.value.id_number.trim(),
      id_issued_on: toIso(form.value.id_issued_on_date)!,
      id_issued_by: form.value.id_issued_by.trim(),
      id_expires_on: toIso(form.value.id_expires_on_date),
      passport_number: hasPassport.value ? form.value.passport_number : null,
      passport_issued_on: hasPassport.value ? toIso(form.value.passport_issued_on_date) : null,
      passport_expires_on: hasPassport.value ? toIso(form.value.passport_expires_on_date) : null,
      work_permit_number: hasWorkPermit.value ? form.value.work_permit_number : null,
      work_permit_issued_on: hasWorkPermit.value ? toIso(form.value.work_permit_issued_on_date) : null,
      work_permit_expires_on: hasWorkPermit.value ? toIso(form.value.work_permit_expires_on_date) : null,
      phone_number: form.value.phone_number || null,
      personal_email: form.value.personal_email || null,
      personal_tax_code: form.value.personal_tax_code || null,
      bhxh_code: form.value.bhxh_code || null,
    }

    if (isNew.value) {
      const resp = await employeeService.create(payload)
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã tạo nhân viên mới', life: 3000 })
      router.replace(`/employees/${resp.data.id}`)
    } else {
      const resp = await employeeService.update(employeeId.value!, payload)
      employee.value = resp.data
      fillForm(resp.data)
      editing.value = false
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã lưu thay đổi', life: 3000 })
    }
    errors.value = {}
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
  } finally {
    submitting.value = false
  }
}

// ── Bank accounts ──────────────────────────────────────────────────────────────
const bankDialogVisible = ref(false)
const bankSubmitting    = ref(false)
const editingBank       = ref<EmployeeBankAccountRead | null>(null)
const bankErrors        = ref<Record<string, string>>({})
const bankForm          = ref({ bank_id: null as number | null, account_number: '', account_name: '', branch_name: '', is_primary: false })

function openBankDialog(acc: EmployeeBankAccountRead | null) {
  editingBank.value = acc
  bankErrors.value = {}
  if (acc) {
    bankForm.value = {
      bank_id: acc.bank_id,
      account_number: acc.account_number,
      account_name: acc.account_name,
      branch_name: acc.branch_name ?? '',
      is_primary: acc.is_primary,
    }
  } else {
    bankForm.value = { bank_id: null, account_number: '', account_name: '', branch_name: '', is_primary: false }
  }
  bankDialogVisible.value = true
}

function validateBank(): boolean {
  bankErrors.value = {}
  if (!bankForm.value.bank_id) bankErrors.value.bank_id = 'Chọn ngân hàng'
  if (!bankForm.value.account_number.trim()) bankErrors.value.account_number = 'Không được để trống'
  if (!bankForm.value.account_name.trim()) bankErrors.value.account_name = 'Không được để trống'
  return Object.keys(bankErrors.value).length === 0
}

async function submitBank() {
  if (!validateBank() || !employeeId.value) return
  bankSubmitting.value = true
  try {
    const payload = {
      bank_id: bankForm.value.bank_id!,
      account_number: bankForm.value.account_number.trim(),
      account_name: bankForm.value.account_name.trim(),
      branch_name: bankForm.value.branch_name.trim() || null,
      is_primary: bankForm.value.is_primary,
    }
    if (editingBank.value) {
      await employeeService.updateBankAccount(employeeId.value, editingBank.value.id, payload)
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã cập nhật tài khoản', life: 3000 })
    } else {
      await employeeService.createBankAccount(employeeId.value, payload)
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã thêm tài khoản ngân hàng', life: 3000 })
    }
    bankDialogVisible.value = false
    const resp = await employeeService.getBankAccounts(employeeId.value)
    bankAccounts.value = resp.data
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
  } finally {
    bankSubmitting.value = false
  }
}

function confirmDeleteBank(acc: EmployeeBankAccountRead) {
  confirm.require({
    message: `Xóa tài khoản "${acc.account_number}"?`,
    header: 'Xác nhận',
    icon: 'pi pi-exclamation-triangle',
    rejectProps: { label: 'Hủy', severity: 'secondary', outlined: true },
    acceptProps: { label: 'Xóa', severity: 'danger' },
    accept: async () => {
      if (!employeeId.value) return
      try {
        await employeeService.deleteBankAccount(employeeId.value, acc.id)
        const resp = await employeeService.getBankAccounts(employeeId.value)
        bankAccounts.value = resp.data
        toast.add({ severity: 'success', summary: 'Đã xóa', detail: 'Tài khoản ngân hàng đã được xóa', life: 3000 })
      } catch (e) {
        toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 })
      }
    },
  })
}

onMounted(async () => {
  await loadCatalogs()
  if (!isNew.value) await loadEmployee()
})

watch(() => route.params.id, () => {
  if (!isNew.value) loadEmployee()
})
</script>
