<template>
  <div class="insurance-foundation-view">
    <div class="page-header insurance-header">
      <div>
        <h2>Cấu hình BHXH dùng chung</h2>
        <span class="subtitle">Foundation cho policy, tỷ lệ đóng mặc định và vùng BHXH công ty</span>
      </div>
      <div class="insurance-header-actions">
        <Button label="Cập nhật vùng công ty" icon="pi pi-map-marker" severity="secondary" @click="openRegionDialog" />
        <Button label="Tạo policy mới" icon="pi pi-plus" @click="openCreatePolicyDialog" />
        <Button
          v-if="activePolicy"
          label="Tạo nháp từ policy hiện hành"
          icon="pi pi-copy"
          severity="secondary"
          @click="openCloneDialog"
        />
        <Button
          label="Về tổng quan danh mục"
          icon="pi pi-th-large"
          severity="secondary"
          outlined
          @click="router.push('/catalog')"
        />
        <Button
          label="Mở module BHXH nhân viên"
          icon="pi pi-users"
          severity="secondary"
          @click="router.push('/insurance')"
        />
      </div>
    </div>

    <div class="insurance-note">
      <strong>Lưu ý quan trọng:</strong>
      <ul>
        <li>Thay đổi policy chỉ áp dụng cho cấu hình mới sau khi activate.</li>
        <li>Vùng BHXH của công ty hiện đang được seed mặc định là Vùng III.</li>
        <li>Seeder tỷ lệ là mặc định vận hành; trước khi thay đổi production cần đối chiếu lại văn bản pháp lý hiện hành.</li>
      </ul>
    </div>

    <div class="insurance-summary-grid">
      <div class="card insurance-summary-card">
        <div class="insurance-card-label">Policy đang active</div>
        <div v-if="activePolicy" class="insurance-card-main">{{ activePolicy.name }}</div>
        <div v-if="activePolicy" class="insurance-card-sub">
          {{ activePolicy.code }} · Hiệu lực từ {{ formatDate(activePolicy.effective_from) }}
        </div>
        <div v-else class="insurance-card-empty">Chưa có policy đang active</div>
      </div>

      <div class="card insurance-summary-card">
        <div class="insurance-card-label">Vùng BHXH công ty</div>
        <div v-if="companyRegion.current" class="insurance-card-main">{{ regionLabel(companyRegion.current.region) }}</div>
        <div v-if="companyRegion.current" class="insurance-card-sub">
          Hiệu lực từ {{ formatDate(companyRegion.current.effective_from) }}
        </div>
        <div v-else class="insurance-card-empty">Chưa có vùng hiệu lực</div>
      </div>
    </div>

    <div class="insurance-section-grid">
      <div class="card insurance-policy-list-card">
        <div class="section-heading">
          <h3>Danh sách policy version</h3>
          <Button icon="pi pi-refresh" severity="secondary" text rounded :loading="loading" @click="loadAll" />
        </div>

        <DataTable :value="policyVersions" :loading="loading" stripedRows responsive-layout="scroll">
          <Column field="code" header="Mã" style="min-width: 160px" />
          <Column field="name" header="Tên" style="min-width: 240px" />
          <Column header="Hiệu lực" style="width: 190px">
            <template #body="{ data }">
              <div class="range-cell">
                <span>{{ formatDate(data.effective_from) }}</span>
                <span>{{ data.effective_to ? `→ ${formatDate(data.effective_to)}` : '→ hiện tại' }}</span>
              </div>
            </template>
          </Column>
          <Column header="Vùng" style="width: 110px">
            <template #body="{ data }">{{ regionLabel(data.company_region) }}</template>
          </Column>
          <Column header="Trạng thái" style="width: 110px">
            <template #body="{ data }">
              <Tag
                :value="data.is_active ? 'Đang dùng' : (data.effective_to ? 'Lịch sử' : 'Nháp')"
                :severity="data.is_active ? 'success' : (data.effective_to ? 'contrast' : 'secondary')"
              />
            </template>
          </Column>
          <Column header="" style="width: 156px">
            <template #body="{ data }">
              <div class="action-cell">
                <Button
                  v-if="!data.is_active && !data.effective_to"
                  icon="pi pi-pencil"
                  severity="secondary"
                  text
                  rounded
                  size="small"
                  @click="openEditPolicyDialog(data)"
                />
                <Button
                  v-if="!data.is_active && !data.effective_to"
                  icon="pi pi-check"
                  severity="success"
                  text
                  rounded
                  size="small"
                  :loading="activatingPolicyId === data.id"
                  @click="activatePolicy(data)"
                />
                <Button
                  v-if="!data.is_active && !data.effective_to"
                  icon="pi pi-trash"
                  severity="danger"
                  text
                  rounded
                  size="small"
                  @click="confirmDeletePolicy(data)"
                />
              </div>
            </template>
          </Column>
        </DataTable>
      </div>

      <div class="card insurance-active-rates-card">
        <div class="section-heading">
          <h3>Tỷ lệ đóng mặc định đang áp dụng</h3>
          <span v-if="activePolicy" class="section-hint">{{ activePolicy.code }}</span>
        </div>

        <div v-if="!activePolicy" class="empty-state">Chưa có policy active</div>
        <div v-else class="ins-rates-table">
          <div class="ins-rates-head">
            <span>Thành phần</span>
            <span>NLĐ %</span>
            <span>NSDLĐ %</span>
            <span>Tổng %</span>
            <span>Nộp hộ</span>
          </div>
          <template v-for="group in groupedRates" :key="group.kind">
            <div class="ins-rates-group-header">{{ group.label }}</div>
            <div v-for="item in group.items" :key="item.component_code" class="ins-rates-row">
              <span>{{ item.component_name }}</span>
              <span>{{ formatPercent(item.employee_rate_percent) }}</span>
              <span>{{ formatPercent(item.employer_rate_percent) }}</span>
              <span>{{ formatPercent(totalRate(item)) }}</span>
              <Tag :value="item.employer_advances_employee_part ? 'Có' : 'Không'" :severity="item.employer_advances_employee_part ? 'warn' : 'contrast'" size="small" />
            </div>
            <div class="ins-rates-subtotal">
              <span>Tổng {{ group.label.split('—')[0].trim() }}</span>
              <span>{{ formatPercent(group.empTotal) }}</span>
              <span>{{ formatPercent(group.erTotal) }}</span>
              <span>{{ formatPercent(group.empTotal + group.erTotal) }}</span>
              <span></span>
            </div>
          </template>
          <div class="ins-rates-total">
            <span>Tổng tất cả</span>
            <span>{{ formatPercent(grandTotals.emp) }}</span>
            <span>{{ formatPercent(grandTotals.er) }}</span>
            <span>{{ formatPercent(grandTotals.emp + grandTotals.er) }}</span>
            <span></span>
          </div>
        </div>
      </div>
    </div>

    <div class="card insurance-region-history-card">
      <div class="section-heading">
        <h3>Lịch sử vùng BHXH công ty</h3>
      </div>

      <DataTable :value="companyRegion.history" stripedRows responsive-layout="scroll">
        <Column header="Vùng" style="width: 140px">
          <template #body="{ data }">{{ regionLabel(data.region) }}</template>
        </Column>
        <Column header="Hiệu lực từ" style="width: 140px">
          <template #body="{ data }">{{ formatDate(data.effective_from) }}</template>
        </Column>
        <Column header="Hiệu lực đến" style="width: 140px">
          <template #body="{ data }">{{ data.effective_to ? formatDate(data.effective_to) : 'Hiện tại' }}</template>
        </Column>
        <Column field="note" header="Ghi chú" style="min-width: 240px" />
      </DataTable>
    </div>

    <div class="card ins-date-checker">
      <div class="section-heading">
        <h3>Kiểm tra cấu hình theo ngày</h3>
      </div>
      <div class="field-row-2">
        <div class="field">
          <label>Ngày kiểm tra</label>
          <input v-model="checkDate" class="p-inputtext p-component w-full" type="date" />
        </div>
        <div class="field ins-check-action">
          <Button label="Kiểm tra" icon="pi pi-search" :loading="checkingDate" :disabled="!checkDate" @click="checkEffectiveConfig" />
        </div>
      </div>
      <div v-if="checkResult" class="ins-check-result">
        <div>Policy: <strong>{{ checkResult.policy_version.code }} — {{ checkResult.policy_version.name }}</strong></div>
        <div>Vùng công ty: <strong>{{ regionLabel(checkResult.company_region.region) }}</strong> (từ {{ formatDate(checkResult.company_region.effective_from) }})</div>
      </div>
      <div v-if="checkError" class="ins-check-error">{{ checkError }}</div>
    </div>

    <Dialog
      v-model:visible="policyDialogVisible"
      :header="editingPolicy ? 'Cập nhật policy version' : 'Tạo policy version mới'"
      :style="{ width: '960px' }"
      modal
      :close-on-escape="!submitting"
      :closable="!submitting"
    >
      <form class="insurance-policy-form" @submit.prevent="submitPolicy">
        <div class="field-row-3">
          <div class="field">
            <label>Mã policy <span class="req">*</span></label>
            <InputText v-model="policyForm.code" class="w-full" :disabled="!!editingPolicy" />
          </div>
          <div class="field">
            <label>Ngày hiệu lực <span class="req">*</span></label>
            <input v-model="policyForm.effective_from" class="p-inputtext p-component w-full" type="date" />
          </div>
          <div class="field">
            <label>Vùng công ty snapshot <span class="req">*</span></label>
            <Select
              v-model="policyForm.company_region"
              :options="regionOptions"
              option-label="label"
              option-value="value"
              filter
              class="w-full"
            />
          </div>
        </div>

        <div class="field">
          <label>Tên policy <span class="req">*</span></label>
          <InputText v-model="policyForm.name" class="w-full" />
        </div>

        <div class="field">
          <label>Căn cứ pháp lý</label>
          <Textarea v-model="policyForm.legal_basis_summary" class="w-full" rows="3" auto-resize />
        </div>

        <div class="field">
          <label>Ghi chú</label>
          <Textarea v-model="policyForm.note" class="w-full" rows="2" auto-resize />
        </div>

        <div class="policy-components-editor">
          <div class="section-heading">
            <h3>Component rates</h3>
            <span class="section-hint">Đủ 5 component active mới được activate policy</span>
          </div>

          <DataTable :value="policyForm.components" responsive-layout="scroll" stripedRows>
            <Column field="component_code" header="Mã" style="width: 180px" />
            <Column field="component_name" header="Tên" style="min-width: 260px" />
            <Column header="NLĐ %" style="width: 130px">
              <template #body="{ data }">
                <InputNumber v-model="data.employee_rate_percent_n" :min="0" :min-fraction-digits="0" :max-fraction-digits="4" class="w-full" />
              </template>
            </Column>
            <Column header="NSDLĐ %" style="width: 130px">
              <template #body="{ data }">
                <InputNumber v-model="data.employer_rate_percent_n" :min="0" :min-fraction-digits="0" :max-fraction-digits="4" class="w-full" />
              </template>
            </Column>
            <Column header="Công ty nộp hộ" style="width: 160px">
              <template #body="{ data }">
                <Checkbox v-model="data.employer_advances_employee_part" binary />
              </template>
            </Column>
          </DataTable>
        </div>

        <div class="dialog-actions">
          <Button type="button" label="Hủy" severity="secondary" text :disabled="submitting" @click="policyDialogVisible = false" />
          <Button type="submit" :label="editingPolicy ? 'Lưu thay đổi' : 'Tạo policy'" icon="pi pi-check" :loading="submitting" />
        </div>
      </form>
    </Dialog>

    <Dialog
      v-model:visible="regionDialogVisible"
      header="Cập nhật vùng BHXH công ty"
      :style="{ width: '520px' }"
      modal
      :close-on-escape="!submittingRegion"
      :closable="!submittingRegion"
    >
      <form class="insurance-region-form" @submit.prevent="submitRegion">
        <div class="field">
          <label>Vùng mới <span class="req">*</span></label>
          <Select v-model="regionForm.region" :options="regionOptions" option-label="label" option-value="value" filter class="w-full" />
        </div>
        <div class="field">
          <label>Ngày hiệu lực <span class="req">*</span></label>
          <input v-model="regionForm.effective_from" class="p-inputtext p-component w-full" type="date" />
        </div>
        <div class="field">
          <label>Ghi chú</label>
          <Textarea v-model="regionForm.note" class="w-full" rows="3" auto-resize />
        </div>

        <div class="dialog-actions">
          <Button type="button" label="Hủy" severity="secondary" text :disabled="submittingRegion" @click="regionDialogVisible = false" />
          <Button type="submit" label="Lưu vùng công ty" icon="pi pi-check" :loading="submittingRegion" />
        </div>
      </form>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import { useToast } from 'primevue/usetoast'
import insuranceService, {
  type CompanyRegionRead,
  type InsuranceContributionComponentRead,
  type InsuranceEffectiveContributionConfigRead,
  type InsurancePolicyVersionCreate,
  type InsurancePolicyVersionRead,
  type InsurancePolicyVersionUpdate,
} from '@/services/insuranceService'

type PolicyFormComponent = {
  component_code: string
  component_name: string
  employee_rate_percent_n: number
  employer_rate_percent_n: number
  employer_advances_employee_part: boolean
}

const router = useRouter()
const confirm = useConfirm()
const toast = useToast()

const loading = ref(false)
const submitting = ref(false)
const submittingRegion = ref(false)
const activatingPolicyId = ref<number | null>(null)

const policyVersions = ref<InsurancePolicyVersionRead[]>([])
const components = ref<InsuranceContributionComponentRead[]>([])
const companyRegion = ref<CompanyRegionRead>({ current: null, history: [] })

const policyDialogVisible = ref(false)
const regionDialogVisible = ref(false)
const editingPolicy = ref<InsurancePolicyVersionRead | null>(null)

const policyForm = ref({
  code: '',
  name: '',
  legal_basis_summary: '',
  effective_from: '',
  company_region: 3,
  note: '',
  components: [] as PolicyFormComponent[],
})

const regionForm = ref({
  region: 3,
  effective_from: '',
  note: '',
})

const regionOptions = [
  { label: 'Vùng I', value: 1 },
  { label: 'Vùng II', value: 2 },
  { label: 'Vùng III', value: 3 },
  { label: 'Vùng IV', value: 4 },
]

const checkDate = ref('')
const checkResult = ref<InsuranceEffectiveContributionConfigRead | null>(null)
const checkError = ref('')
const checkingDate = ref(false)

const activePolicy = computed(() => policyVersions.value.find((item) => item.is_active) ?? null)

const _kindOrder = ['bhxh', 'bhyt', 'bhtn']
const _kindLabels: Record<string, string> = {
  bhxh: 'BHXH — Bảo hiểm xã hội',
  bhyt: 'BHYT — Bảo hiểm y tế',
  bhtn: 'BHTN — Bảo hiểm thất nghiệp',
}

const groupedRates = computed(() => {
  if (!activePolicy.value) return []
  const sorted = [...activePolicy.value.components].sort((a, b) => a.sort_order - b.sort_order)
  return _kindOrder
    .map((kind) => {
      const items = sorted.filter((c) => c.insurance_kind.toLowerCase() === kind)
      const empTotal = items.reduce((s: number, c) => s + Number(c.employee_rate_percent), 0)
      const erTotal = items.reduce((s: number, c) => s + Number(c.employer_rate_percent), 0)
      return { kind, label: _kindLabels[kind] ?? kind.toUpperCase(), items, empTotal, erTotal }
    })
    .filter((g) => g.items.length > 0)
})

const grandTotals = computed(() => {
  if (!activePolicy.value) return { emp: 0, er: 0 }
  const comps = activePolicy.value.components
  return {
    emp: comps.reduce((s, c) => s + Number(c.employee_rate_percent), 0),
    er: comps.reduce((s, c) => s + Number(c.employer_rate_percent), 0),
  }
})

function regionLabel(region: number) {
  return regionOptions.find((item) => item.value === region)?.label ?? `Vùng ${region}`
}

function formatDate(value: string | null) {
  if (!value) return '—'
  const [year, month, day] = value.slice(0, 10).split('-')
  return `${day}/${month}/${year}`
}

function formatPercent(value: string | number) {
  const n = Number(value)
  return `${n.toFixed(n % 1 === 0 ? 0 : 2)}%`
}

function totalRate(item: { employee_rate_percent: string; employer_rate_percent: string }) {
  return Number(item.employee_rate_percent) + Number(item.employer_rate_percent)
}

function apiError(error: unknown): string {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof detail === 'string') return detail
  return 'Đã xảy ra lỗi không xác định'
}

function buildDefaultComponentFormRows() {
  return components.value
    .filter((item) => item.is_active)
    .sort((a, b) => a.sort_order - b.sort_order)
    .map((item) => ({
      component_code: item.code,
      component_name: item.name_vi,
      employee_rate_percent_n: 0,
      employer_rate_percent_n: 0,
      employer_advances_employee_part: false,
    }))
}

async function loadAll() {
  loading.value = true
  try {
    const [componentsResp, policyResp, regionResp] = await Promise.all([
      insuranceService.getComponents(),
      insuranceService.getPolicyVersions(),
      insuranceService.getCompanyRegion(),
    ])
    components.value = componentsResp.data
    policyVersions.value = policyResp.data
    companyRegion.value = regionResp.data
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(error), life: 5000 })
  } finally {
    loading.value = false
  }
}

function resetPolicyForm() {
  policyForm.value = {
    code: '',
    name: '',
    legal_basis_summary: '',
    effective_from: '',
    company_region: companyRegion.value.current?.region ?? 3,
    note: '',
    components: buildDefaultComponentFormRows(),
  }
}

function openCreatePolicyDialog() {
  editingPolicy.value = null
  resetPolicyForm()
  policyDialogVisible.value = true
}

function openCloneDialog() {
  if (!activePolicy.value) return
  editingPolicy.value = null
  policyForm.value = {
    code: '',
    name: `[NHÁP] ${activePolicy.value.name}`,
    legal_basis_summary: activePolicy.value.legal_basis_summary ?? '',
    effective_from: '',
    company_region: activePolicy.value.company_region,
    note: activePolicy.value.note ?? '',
    components: activePolicy.value.components
      .slice()
      .sort((a: { sort_order: number }, b: { sort_order: number }) => a.sort_order - b.sort_order)
      .map((item: typeof activePolicy.value.components[number]) => ({
        component_code: item.component_code,
        component_name: item.component_name,
        employee_rate_percent_n: Number(item.employee_rate_percent),
        employer_rate_percent_n: Number(item.employer_rate_percent),
        employer_advances_employee_part: item.employer_advances_employee_part,
      })),
  }
  policyDialogVisible.value = true
}

function openEditPolicyDialog(policy: InsurancePolicyVersionRead) {
  editingPolicy.value = policy
  policyForm.value = {
    code: policy.code,
    name: policy.name,
    legal_basis_summary: policy.legal_basis_summary ?? '',
    effective_from: policy.effective_from,
    company_region: policy.company_region,
    note: policy.note ?? '',
    components: policy.components
      .slice()
      .sort((a, b) => a.sort_order - b.sort_order)
      .map((item) => ({
        component_code: item.component_code,
        component_name: item.component_name,
        employee_rate_percent_n: Number(item.employee_rate_percent),
        employer_rate_percent_n: Number(item.employer_rate_percent),
        employer_advances_employee_part: item.employer_advances_employee_part,
      })),
  }
  policyDialogVisible.value = true
}

function openRegionDialog() {
  regionForm.value = {
    region: companyRegion.value.current?.region ?? 3,
    effective_from: '',
    note: '',
  }
  regionDialogVisible.value = true
}

async function submitPolicy() {
  submitting.value = true
  try {
    const componentsPayload = policyForm.value.components.map((item) => ({
      component_code: item.component_code,
      employee_rate_percent: String(item.employee_rate_percent_n ?? 0),
      employer_rate_percent: String(item.employer_rate_percent_n ?? 0),
      employer_advances_employee_part: item.employer_advances_employee_part,
    }))

    if (editingPolicy.value) {
      const payload: InsurancePolicyVersionUpdate = {
        name: policyForm.value.name,
        legal_basis_summary: policyForm.value.legal_basis_summary || null,
        effective_from: policyForm.value.effective_from,
        company_region: policyForm.value.company_region,
        note: policyForm.value.note || null,
        components: componentsPayload,
      }
      await insuranceService.updatePolicyVersion(editingPolicy.value.id, payload)
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã cập nhật policy version', life: 3000 })
    } else {
      const payload: InsurancePolicyVersionCreate = {
        code: policyForm.value.code,
        name: policyForm.value.name,
        legal_basis_summary: policyForm.value.legal_basis_summary || null,
        effective_from: policyForm.value.effective_from,
        company_region: policyForm.value.company_region,
        note: policyForm.value.note || null,
        components: componentsPayload,
      }
      await insuranceService.createPolicyVersion(payload)
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã tạo policy version mới', life: 3000 })
    }

    policyDialogVisible.value = false
    await loadAll()
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(error), life: 5000 })
  } finally {
    submitting.value = false
  }
}

async function activatePolicy(policy: InsurancePolicyVersionRead) {
  activatingPolicyId.value = policy.id
  try {
    await insuranceService.activatePolicyVersion(policy.id)
    toast.add({ severity: 'success', summary: 'Thành công', detail: `Đã activate ${policy.code}`, life: 3000 })
    await loadAll()
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(error), life: 5000 })
  } finally {
    activatingPolicyId.value = null
  }
}

function confirmDeletePolicy(policy: InsurancePolicyVersionRead) {
  confirm.require({
    message: `Hủy nháp policy ${policy.code}? Thao tác này sẽ xóa toàn bộ component rates của bản nháp này.`,
    header: 'Xác nhận hủy nháp',
    icon: 'pi pi-exclamation-triangle',
    rejectProps: {
      label: 'Không',
      severity: 'secondary',
      outlined: true,
    },
    acceptProps: {
      label: 'Hủy nháp',
      severity: 'danger',
    },
    accept: async () => {
      try {
        await insuranceService.deletePolicyVersion(policy.id)
        toast.add({ severity: 'success', summary: 'Thành công', detail: `Đã hủy nháp ${policy.code}`, life: 3000 })
        await loadAll()
      } catch (error) {
        toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(error), life: 5000 })
      }
    },
  })
}

async function checkEffectiveConfig() {
  if (!checkDate.value) return
  checkingDate.value = true
  checkResult.value = null
  checkError.value = ''
  try {
    const resp = await insuranceService.getEffectiveConfig(checkDate.value)
    checkResult.value = resp.data
  } catch (error) {
    const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
    checkError.value = typeof detail === 'string' ? detail : 'Không tìm thấy cấu hình cho ngày này'
  } finally {
    checkingDate.value = false
  }
}

async function submitRegion() {
  submittingRegion.value = true
  try {
    await insuranceService.updateCompanyRegion({
      region: regionForm.value.region,
      effective_from: regionForm.value.effective_from,
      note: regionForm.value.note || null,
    })
    toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã cập nhật vùng BHXH công ty', life: 3000 })
    regionDialogVisible.value = false
    await loadAll()
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(error), life: 5000 })
  } finally {
    submittingRegion.value = false
  }
}

onMounted(async () => {
  await loadAll()
})
</script>
