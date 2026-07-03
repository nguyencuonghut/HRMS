<template>
  <div class="insurance-view">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h2>Bảo hiểm BHXH</h2>
        <span class="subtitle">Hồ sơ BHXH nhân viên, nền lương đóng và cấu hình chính sách</span>
      </div>
      <div class="insurance-header-actions">
        <Button
          label="Cấu hình BHXH dùng chung"
          icon="pi pi-sliders-h"
          severity="secondary"
          outlined
          @click="router.push('/catalog/insurance')"
        />
      </div>
    </div>

    <!-- Top tabs -->
    <Tabs v-model:value="activeTopTab" class="ins-top-tabs">
      <TabList>
        <Tab value="profiles">Hồ sơ BHXH</Tab>
        <Tab value="changes">Biến động</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="profiles">

    <!-- Summary cards -->
    <div class="insurance-summary-grid">
      <div class="card insurance-summary-card">
        <div class="insurance-card-label">Đang tham gia BHXH</div>
        <div class="insurance-card-main">{{ activeCount }}</div>
        <div class="insurance-card-sub">nhân viên</div>
      </div>
      <div class="card insurance-summary-card">
        <div class="insurance-card-label">Policy đang active</div>
        <div class="insurance-card-main">{{ activePolicy?.code ?? '—' }}</div>
        <div class="insurance-card-sub">{{ activePolicy?.name ?? 'Chưa có policy active' }}</div>
      </div>
    </div>

    <!-- Filter toolbar -->
    <div class="toolbar">
      <IconField class="toolbar-search">
        <InputIcon class="pi pi-search" />
        <InputText
          v-model="filters.keyword"
          placeholder="Tìm mã NV, họ tên, mã BHXH..."
          class="w-full"
          @keyup.enter="applyFilter"
        />
      </IconField>
      <Select
        v-model="filters.department_id"
        :options="departments"
        option-label="name"
        option-value="id"
        placeholder="Phòng ban"
        filter
        show-clear
        class="toolbar-filter"
      />
      <Select
        v-model="filters.participation_status"
        :options="statusOptions"
        option-label="label"
        option-value="value"
        placeholder="Trạng thái"
        filter
        show-clear
        class="toolbar-filter-sm"
      />
      <Select
        v-model="filters.has_bhxh_code"
        :options="bhxhCodeOptions"
        option-label="label"
        option-value="value"
        placeholder="Có mã BHXH"
        show-clear
        class="toolbar-filter-sm"
      />
      <Button label="Lọc" icon="pi pi-filter" @click="applyFilter" />
      <Button
        icon="pi pi-refresh"
        severity="secondary"
        text
        rounded
        :loading="loading"
        @click="reset"
      />
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
        <Column field="employee_code" header="Mã NV" style="min-width: 100px">
          <template #body="{ data }">
            <span class="emp-code">{{ data.employee_code }}</span>
          </template>
        </Column>
        <Column field="employee_name" header="Họ tên" style="min-width: 160px" />
        <Column field="department_name" header="Phòng ban" style="min-width: 140px">
          <template #body="{ data }">{{ data.department_name ?? '—' }}</template>
        </Column>
        <Column field="bhxh_code" header="Mã BHXH" style="min-width: 120px">
          <template #body="{ data }">
            <span v-if="data.bhxh_code" class="ins-code">{{ data.bhxh_code }}</span>
            <span v-else class="text-muted">—</span>
          </template>
        </Column>
        <Column field="health_care_insurance_code" header="Mã BH CSSK" style="min-width: 130px">
          <template #body="{ data }">
            <span v-if="data.health_care_insurance_code" class="ins-code">{{ data.health_care_insurance_code }}</span>
            <span v-else class="text-muted">—</span>
          </template>
        </Column>
        <Column field="health_care_family_participation" header="Người thân CSSK" style="min-width: 120px">
          <template #body="{ data }">
            <span v-if="data.health_care_insurance_code">
              {{ data.health_care_family_participation ? 'Có' : 'Không' }}
            </span>
            <span v-else class="text-muted">—</span>
          </template>
        </Column>
        <Column field="accident_insurance_code" header="Mã BH tai nạn" style="min-width: 130px">
          <template #body="{ data }">
            <span v-if="data.accident_insurance_code" class="ins-code">{{ data.accident_insurance_code }}</span>
            <span v-else class="text-muted">—</span>
          </template>
        </Column>
        <Column field="bhyt_initial_clinic_name" header="Nơi KCB ban đầu" style="min-width: 160px">
          <template #body="{ data }">{{ data.bhyt_initial_clinic_name ?? '—' }}</template>
        </Column>
        <Column field="company_bhxh_joined_date" header="Ngày tham gia" style="min-width: 120px">
          <template #body="{ data }">{{ formatDate(data.company_bhxh_joined_date) }}</template>
        </Column>
        <Column field="participation_status" header="Trạng thái" style="min-width: 120px">
          <template #body="{ data }">
            <Tag
              :value="statusLabel(data.participation_status)"
              :severity="statusSeverity(data.participation_status)"
            />
          </template>
        </Column>
        <Column header="Nền tính BHXH" style="min-width: 150px">
          <template #body="{ data }">
            <span v-if="data.insurance_basis_amount" class="ins-basis">
              {{ formatCurrency(data.insurance_basis_amount) }}
              <small class="ins-basis-source">{{ basisSourceLabel(data.insurance_basis_source) }}</small>
            </span>
            <span v-else class="text-muted">Chưa xác định</span>
          </template>
        </Column>
        <Column header="" style="width: 60px; text-align: right">
          <template #body="{ data }">
            <Button
              v-can:edit="'insurance'"
              icon="pi pi-pencil"
              text
              rounded
              severity="secondary"
              @click="openEdit(data)"
            />
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Edit Dialog -->
    <Dialog
      v-model:visible="showDialog"
      :header="`Hồ sơ BHXH — ${editingItem?.employee_name ?? ''}`"
      modal
      :style="{ width: '660px' }"
      :closable="!saving"
    >
      <div v-if="detail" class="ins-dialog-body">
        <Tabs v-model:value="activeDialogTab">
          <TabList>
            <Tab value="basic">Thông tin cơ bản</Tab>
            <Tab value="overrides">Override đóng góp ({{ detail.contributions.length }})</Tab>
          </TabList>

          <!-- Tab 1: Basic info -->
          <TabPanels>
            <TabPanel value="basic">
              <div class="field-row">
                <div class="field">
                  <label>Mã số BHXH</label>
                  <InputText v-model="form.bhxh_code" placeholder="Nhập mã BHXH..." class="w-full" />
                </div>
                <div class="field">
                  <label>Mã BH chăm sóc sức khỏe</label>
                  <InputText v-model="form.health_care_insurance_code" placeholder="Nhập mã BH CSSK..." class="w-full" />
                </div>
              </div>

              <div class="field-row">
                <div class="field">
                  <label class="ins-toggle-label">
                    <Checkbox
                      v-model="form.health_care_family_participation"
                      :binary="true"
                      :disabled="!form.health_care_insurance_code"
                    />
                    Người thân tham gia cùng
                  </label>
                  <small v-if="!form.health_care_insurance_code" class="text-muted">
                    Nhập mã BH CSSK trước khi chọn.
                  </small>
                </div>
                <div class="field">
                  <label>Mã BH tai nạn</label>
                  <InputText v-model="form.accident_insurance_code" placeholder="Nhập mã BH tai nạn..." class="w-full" />
                </div>
              </div>

              <div class="field-row">
                <div class="field">
                  <label>Nơi KCB ban đầu</label>
                  <BhytClinicSelect v-model="form.bhyt_initial_clinic" />
                </div>
                <div class="field" />
              </div>

              <div class="field-row">
                <div class="field">
                  <label>Ngày tham gia tại công ty</label>
                  <DatePicker
                    v-model="form.company_bhxh_joined_date_obj"
                    date-format="dd/mm/yy"
                    show-button-bar
                    class="w-full"
                  />
                </div>
                <div class="field">
                  <label>Trạng thái tham gia <span class="req">*</span></label>
                  <Select
                    v-model="form.participation_status"
                    :options="statusOptions"
                    option-label="label"
                    option-value="value"
                    filter
                    class="w-full"
                  />
                </div>
              </div>

              <div v-if="form.participation_status === 'stopped'" class="field-row">
                <div class="field">
                  <label>Ngày dừng hiệu lực <span class="req">*</span></label>
                  <DatePicker
                    v-model="form.status_effective_from_obj"
                    date-format="dd/mm/yy"
                    show-button-bar
                    class="w-full"
                  />
                </div>
                <div class="field">
                  <label>Ghi chú trạng thái</label>
                  <InputText v-model="form.status_note" placeholder="Lý do dừng..." class="w-full" />
                </div>
              </div>

              <div class="field-sep" />

              <div class="field-row">
                <div class="field">
                  <label>Nguồn nền tính BHXH <span class="req">*</span></label>
                  <Select
                    v-model="form.insurance_basis_source"
                    :options="basisSourceOptions"
                    option-label="label"
                    option-value="value"
                    filter
                    class="w-full"
                  />
                </div>
                <div class="field">
                  <label v-if="form.insurance_basis_source === 'manual_fixed'">Mức lương cố định <span class="req">*</span></label>
                  <label v-else>Nền BHXH từ hợp đồng</label>
                  <InputNumber
                    v-if="form.insurance_basis_source === 'manual_fixed'"
                    v-model="form.insurance_basis_amount"
                    :min="0"
                    :max-fraction-digits="0"
                    suffix=" ₫"
                    class="w-full"
                  />
                  <div v-else class="ins-basis-resolved">
                    <span v-if="detail.insurance_basis_amount">
                      {{ formatCurrency(detail.insurance_basis_amount) }}
                    </span>
                    <span v-else class="text-muted">Chưa xác định (hợp đồng chưa có mức BHXH)</span>
                  </div>
                </div>
              </div>

              <div v-if="detail.contract_number" class="ins-contract-ref">
                Hợp đồng hiện hành: <strong>{{ detail.contract_number }}</strong>
              </div>
            </TabPanel>

            <!-- Tab 2: Component overrides -->
            <TabPanel value="overrides">
              <p class="ins-override-hint">
                Mặc định nhân viên đóng theo tỷ lệ của policy đang active.
                Bật override để nhập mức cố định cho từng khoản.
              </p>
              <div class="ins-overrides-table">
                <div
                  v-for="contrib in detail.contributions"
                  :key="contrib.component_code"
                  class="ins-override-row"
                >
                  <div class="ins-override-info">
                    <strong>{{ contrib.component_name }}</strong>
                    <small class="text-muted">{{ contrib.component_code }}</small>
                  </div>
                  <div class="ins-override-policy">
                    <span v-if="contrib.calc_mode === 'company_policy'" class="text-muted">
                      NLĐ {{ formatPercent(contrib.employee_rate_percent) }} /
                      NSDLĐ {{ formatPercent(contrib.employer_rate_percent) }}
                    </span>
                    <span v-else class="ins-fixed-badge">Cố định</span>
                  </div>
                  <div class="ins-override-toggle">
                    <label class="ins-toggle-label">
                      <Checkbox
                        :model-value="!getOverride(contrib.component_code)?.use_company_default"
                        :binary="true"
                        @update:model-value="toggleOverride(contrib.component_code, !$event)"
                      />
                      Override
                    </label>
                  </div>
                  <div
                    v-if="getOverride(contrib.component_code) && !getOverride(contrib.component_code)!.use_company_default"
                    class="ins-override-inputs"
                  >
                    <div class="field">
                      <label>NLĐ đóng (₫)</label>
                      <InputNumber
                        :model-value="getOverride(contrib.component_code)!.fixed_employee_amount ?? undefined"
                        :min="0"
                        :max-fraction-digits="0"
                        class="w-full"
                        @update:model-value="setOverrideField(contrib.component_code, 'fixed_employee_amount', $event)"
                      />
                    </div>
                    <div class="field">
                      <label>NSDLĐ đóng (₫)</label>
                      <InputNumber
                        :model-value="getOverride(contrib.component_code)!.fixed_employer_amount ?? undefined"
                        :min="0"
                        :max-fraction-digits="0"
                        class="w-full"
                        @update:model-value="setOverrideField(contrib.component_code, 'fixed_employer_amount', $event)"
                      />
                    </div>
                    <div class="field">
                      <label class="ins-toggle-label">
                        <Checkbox
                          :model-value="getOverride(contrib.component_code)!.employer_advances_employee_part ?? false"
                          :binary="true"
                          @update:model-value="setOverrideField(contrib.component_code, 'employer_advances_employee_part', $event)"
                        />
                        Công ty nộp hộ phần NLĐ
                      </label>
                    </div>
                  </div>
                </div>
              </div>
            </TabPanel>
          </TabPanels>
        </Tabs>
      </div>

      <div v-else class="ins-dialog-loading">
        <i class="pi pi-spin pi-spinner" style="font-size: 1.5rem" />
      </div>

      <template #footer>
        <Button label="Hủy" severity="secondary" text :disabled="saving" @click="closeDialog" />
        <Button v-can:edit="'insurance'" label="Lưu" icon="pi pi-save" :loading="saving" @click="submitForm" />
      </template>
    </Dialog>

        </TabPanel>

        <TabPanel value="changes">
          <InsuranceChangesTab />
        </TabPanel>
      </TabPanels>
    </Tabs>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
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
import { usePermissionGate } from '@/composables/usePermissionGate'
import departmentService from '@/services/departmentService'
import BhytClinicSelect from '@/components/catalog/BhytClinicSelect.vue'
import InsuranceChangesTab from './InsuranceChangesTab.vue'
import { type BhytClinicRead } from '@/services/bhytClinicService'
import insuranceService, {
  type EmployeeInsuranceComponentOverrideInput,
  type EmployeeInsuranceListItem,
  type EmployeeInsuranceProfileRead,
  type InsurancePolicyVersionRead,
} from '@/services/insuranceService'

const router = useRouter()
const permissionGate = usePermissionGate()
const canLoadDepartments = computed(() => permissionGate.canAccessRoute('/org/departments'))

const activeTopTab = ref('profiles')

// ── State ─────────────────────────────────────────────────────────────────────

const loading  = ref(false)
const saving   = ref(false)
const items    = ref<EmployeeInsuranceListItem[]>([])
const total    = ref(0)
const page     = ref(1)
const pageSize = ref(20)

const departments  = ref<{ id: number; name: string }[]>([])
const activePolicy = ref<InsurancePolicyVersionRead | null>(null)
const activeCount  = ref(0)

const filters = ref({
  keyword:               '' as string | null,
  department_id:         null as number | null,
  participation_status:  null as string | null,
  has_bhxh_code:         null as boolean | null,
})

// ── Options ───────────────────────────────────────────────────────────────────

const statusOptions = [
  { label: 'Đang đóng', value: 'active' },
  { label: 'Tạm dừng',  value: 'paused' },
  { label: 'Đã nghỉ',   value: 'stopped' },
]

const bhxhCodeOptions = [
  { label: 'Có mã BHXH',   value: true },
  { label: 'Chưa có mã',   value: false },
]

const basisSourceOptions = [
  { label: 'Từ hợp đồng',     value: 'contract' },
  { label: 'Mức cố định',     value: 'manual_fixed' },
]

// ── Formatters ────────────────────────────────────────────────────────────────

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

function formatCurrency(val: string | number | null): string {
  if (val == null) return '—'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(Number(val))
}

function formatPercent(val: string | null): string {
  if (val == null) return '—'
  const n = parseFloat(val)
  return n % 1 === 0 ? `${n}%` : `${n.toFixed(2)}%`
}

function toIsoDate(d: Date | null | undefined): string | null {
  if (!d) return null
  const y  = d.getFullYear()
  const m  = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${dd}`
}

function fromIsoDate(iso: string | null | undefined): Date | null {
  if (!iso) return null
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d)
}

function statusLabel(s: string): string {
  return { active: 'Đang đóng', paused: 'Tạm dừng', stopped: 'Đã nghỉ' }[s] ?? s
}

function statusSeverity(s: string): string {
  return { active: 'success', paused: 'warn', stopped: 'secondary' }[s] ?? 'secondary'
}

function basisSourceLabel(s: string): string {
  return { contract: 'HĐ', manual_fixed: 'Cố định', computed: 'Tính tự động' }[s] ?? s
}

// ── Load data ─────────────────────────────────────────────────────────────────

async function loadPolicyInfo() {
  try {
    const res = await insuranceService.getPolicyVersions()
    const active = res.data.find((p: InsurancePolicyVersionRead) => p.is_active) ?? null
    activePolicy.value = active
  } catch { /* non-blocking */ }
}

async function loadDepartments() {
  if (!canLoadDepartments.value) {
    departments.value = []
    return
  }
  try {
    const res = await departmentService.getList(true)
    departments.value = res.data as { id: number; name: string }[]
  } catch { /* non-blocking */ }
}

async function load() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: page.value, page_size: pageSize.value }
    if (filters.value.keyword)              params.keyword              = filters.value.keyword
    if (filters.value.department_id != null) params.department_id       = filters.value.department_id
    if (filters.value.participation_status) params.participation_status = filters.value.participation_status
    if (filters.value.has_bhxh_code != null) params.has_bhxh_code       = filters.value.has_bhxh_code

    const res = await insuranceService.listEmployeeProfiles(params)
    items.value = res.data.items
    total.value = res.data.total

    if (page.value === 1 && !Object.values(filters.value).some(v => v != null && v !== '')) {
      activeCount.value = res.data.total
    }
  } finally {
    loading.value = false
  }
}

function applyFilter() {
  page.value = 1
  load()
}

function reset() {
  filters.value = { keyword: null, department_id: null, participation_status: null, has_bhxh_code: null }
  page.value = 1
  load()
}

function onPage(e: { page: number; rows: number }) {
  page.value = e.page + 1
  pageSize.value = e.rows
  load()
}

onMounted(async () => {
  await Promise.all([loadPolicyInfo(), loadDepartments(), load()])
})

// ── Edit dialog ───────────────────────────────────────────────────────────────

const showDialog    = ref(false)
const activeDialogTab = ref('basic')
const editingItem   = ref<EmployeeInsuranceListItem | null>(null)
const detail        = ref<EmployeeInsuranceProfileRead | null>(null)

interface FormState {
  bhxh_code: string | null
  health_care_insurance_code: string | null
  health_care_family_participation: boolean
  accident_insurance_code: string | null
  bhyt_initial_clinic: BhytClinicRead | null
  company_bhxh_joined_date_obj: Date | null
  status_effective_from_obj: Date | null
  participation_status: 'active' | 'paused' | 'stopped'
  status_note: string | null
  insurance_basis_source: 'contract' | 'computed' | 'manual_fixed'
  insurance_basis_amount: number | null
  overrides: Record<string, EmployeeInsuranceComponentOverrideInput>
}

const form = ref<FormState>({
  bhxh_code: null,
  health_care_insurance_code: null,
  health_care_family_participation: false,
  accident_insurance_code: null,
  bhyt_initial_clinic: null,
  company_bhxh_joined_date_obj: null,
  status_effective_from_obj: null,
  participation_status: 'active',
  status_note: null,
  insurance_basis_source: 'contract',
  insurance_basis_amount: null,
  overrides: {},
})

async function openEdit(item: EmployeeInsuranceListItem) {
  editingItem.value = item
  showDialog.value = true
  activeDialogTab.value = 'basic'
  detail.value = null
  form.value.overrides = {}

  try {
    const res = await insuranceService.getEmployeeProfile(item.employee_id)
    detail.value = res.data
    const d = res.data
    form.value = {
      bhxh_code:               d.bhxh_code,
      health_care_insurance_code: d.health_care_insurance_code,
      health_care_family_participation: d.health_care_family_participation ?? false,
      accident_insurance_code: d.accident_insurance_code,
      bhyt_initial_clinic:     d.bhyt_initial_clinic_code
        ? { id: 0, code: d.bhyt_initial_clinic_code, name: d.bhyt_initial_clinic_name ?? '', province_code: null, province_name: null }
        : null,
      company_bhxh_joined_date_obj: fromIsoDate(d.company_bhxh_joined_date),
      status_effective_from_obj:    fromIsoDate(d.status_effective_from),
      participation_status:         d.participation_status as 'active' | 'paused' | 'stopped',
      status_note:                  d.status_note,
      insurance_basis_source:       d.insurance_basis_source as 'contract' | 'computed' | 'manual_fixed',
      insurance_basis_amount:       d.insurance_basis_amount != null ? Number(d.insurance_basis_amount) : null,
      overrides: {},
    }
    // Pre-populate existing overrides
    for (const c of d.contributions) {
      if (c.calc_mode === 'fixed_amount') {
        form.value.overrides[c.component_code] = {
          component_code:                c.component_code,
          use_company_default:           false,
          fixed_employee_amount:         c.fixed_employee_amount != null ? Number(c.fixed_employee_amount) : null,
          fixed_employer_amount:         c.fixed_employer_amount != null ? Number(c.fixed_employer_amount) : null,
          employer_advances_employee_part: c.employer_advances_employee_part,
        }
      }
    }
  } catch { /* show loading state */ }
}

function closeDialog() {
  showDialog.value = false
  editingItem.value = null
  detail.value = null
}

// Override helpers
function getOverride(code: string): EmployeeInsuranceComponentOverrideInput | undefined {
  return form.value.overrides[code]
}

function toggleOverride(code: string, wantOverride: boolean) {
  if (wantOverride) {
    form.value.overrides[code] = {
      component_code:                  code,
      use_company_default:             false,
      fixed_employee_amount:           null,
      fixed_employer_amount:           null,
      employer_advances_employee_part: false,
    }
  } else {
    delete form.value.overrides[code]
  }
}

function setOverrideField(code: string, field: keyof EmployeeInsuranceComponentOverrideInput, value: unknown) {
  if (form.value.overrides[code]) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(form.value.overrides[code] as any)[field] = value
  }
}

async function submitForm() {
  if (!editingItem.value) return
  saving.value = true
  try {
    const payload = {
      bhxh_code:                form.value.bhxh_code || null,
      health_care_insurance_code: form.value.health_care_insurance_code || null,
      health_care_family_participation: form.value.health_care_insurance_code
        ? form.value.health_care_family_participation
        : null,
      accident_insurance_code: form.value.accident_insurance_code || null,
      bhyt_initial_clinic_name: form.value.bhyt_initial_clinic?.name || null,
      bhyt_initial_clinic_code: form.value.bhyt_initial_clinic?.code || null,
      company_bhxh_joined_date: toIsoDate(form.value.company_bhxh_joined_date_obj),
      participation_status:     form.value.participation_status,
      status_effective_from:    toIsoDate(form.value.status_effective_from_obj),
      status_note:              form.value.status_note || null,
      insurance_basis_source:   form.value.insurance_basis_source,
      insurance_basis_amount:
        form.value.insurance_basis_source === 'manual_fixed'
          ? form.value.insurance_basis_amount
          : null,
      component_overrides: Object.values(form.value.overrides) as EmployeeInsuranceComponentOverrideInput[],
    }
    await insuranceService.updateEmployeeProfile(editingItem.value.employee_id, payload)
    closeDialog()
    load()
  } finally {
    saving.value = false
  }
}
</script>
