<template>
  <Dialog
    v-model:visible="visible"
    :header="isEdit ? 'Cập nhật hợp đồng' : 'Thêm hợp đồng'"
    :style="{ width: '560px' }"
    modal
    :closable="!submitting"
  >
    <div class="field-row">
      <div class="field">
        <label>Loại hợp đồng <span class="req">*</span></label>
        <Select
          v-model="form.contract_category_id"
          :options="categoryOptions"
          option-label="label"
          option-value="value"
          filter
          placeholder="Chọn loại"
          class="w-full"
          :invalid="!!errors.contract_category_id"
        />
        <small v-if="errors.contract_category_id" class="error-msg">{{ errors.contract_category_id }}</small>
      </div>

      <div class="field">
        <label>Số hợp đồng <span class="req">*</span></label>
        <InputText
          v-model="form.contract_number"
          class="w-full"
          placeholder="VD: HĐ-2024-001"
          :invalid="!!errors.contract_number"
        />
        <small v-if="errors.contract_number" class="error-msg">{{ errors.contract_number }}</small>
      </div>
    </div>

    <div class="field" v-if="parentOptions.length > 0">
      <label>Phụ lục của hợp đồng</label>
      <Select
        v-model="form.parent_contract_id"
        :options="parentOptions"
        option-label="label"
        option-value="value"
        filter
        show-clear
        placeholder="Chọn HĐ gốc (nếu là phụ lục)"
        class="w-full"
      />
    </div>

    <div class="field-row">
      <div class="field">
        <label>Ngày ký <span class="req">*</span></label>
        <DatePicker
          v-model="form.signed_date_d"
          class="w-full"
          date-format="dd/mm/yy"
          :invalid="!!errors.signed_date"
        />
        <small v-if="errors.signed_date" class="error-msg">{{ errors.signed_date }}</small>
      </div>

      <div class="field">
        <label>Mode lương đóng BH <span class="req">*</span></label>
        <Select
          v-model="form.insurance_salary_mode"
          :options="insuranceSalaryModeOptions"
          option-label="label"
          option-value="value"
          class="w-full"
          :invalid="!!errors.insurance_salary_mode"
        />
        <small v-if="errors.insurance_salary_mode" class="error-msg">{{ errors.insurance_salary_mode }}</small>
      </div>
    </div>

    <div v-if="form.insurance_salary_mode === 'computed_by_position_group'" class="field-row">
      <div class="field">
        <label>Nhóm vị trí BHXH <span class="req">*</span></label>
        <Select
          v-model="form.bhxh_position_group_id"
          :options="positionGroupOptions"
          option-label="label"
          option-value="value"
          filter
          class="w-full"
          :loading="loadingInsuranceConfig"
          :invalid="!!errors.bhxh_position_group_id"
        />
        <small v-if="errors.bhxh_position_group_id" class="error-msg">{{ errors.bhxh_position_group_id }}</small>
      </div>

      <div class="field">
        <label>Bậc hệ số <span class="req">*</span></label>
        <Select
          v-model="form.insurance_salary_grade_no"
          :options="gradeOptions"
          option-label="label"
          option-value="value"
          class="w-full"
          :invalid="!!errors.insurance_salary_grade_no"
        />
        <small v-if="errors.insurance_salary_grade_no" class="error-msg">{{ errors.insurance_salary_grade_no }}</small>
      </div>
    </div>

    <div v-else class="field">
      <label>Mức lương đóng BH cố định (VNĐ) <span class="req">*</span></label>
      <InputNumber
        v-model="form.insurance_salary_fixed_amount_n"
        class="w-full"
        :use-grouping="true"
        :min="0"
        :max="999999999"
        placeholder="Nhập mức cố định"
        :invalid="!!errors.insurance_salary_fixed_amount"
      />
      <small v-if="errors.insurance_salary_fixed_amount" class="error-msg">{{ errors.insurance_salary_fixed_amount }}</small>
    </div>

    <div class="field-row">
      <div class="field">
        <label>Hiệu lực từ <span class="req">*</span></label>
        <DatePicker
          v-model="form.effective_from_d"
          class="w-full"
          date-format="dd/mm/yy"
          :invalid="!!errors.effective_from"
        />
        <small v-if="errors.effective_from" class="error-msg">{{ errors.effective_from }}</small>
      </div>

      <div class="field">
        <label>Hiệu lực đến</label>
        <DatePicker
          v-model="form.effective_to_d"
          class="w-full"
          date-format="dd/mm/yy"
          show-button-bar
          placeholder="Để trống = vô thời hạn"
        />
      </div>
    </div>

    <div class="field">
      <label>Mức lương đóng BH (VNĐ)</label>
      <div class="contract-insurance-preview-box">
        <template v-if="previewLoading">
          Đang tính preview...
        </template>
        <template v-else-if="previewError">
          <span class="error-msg">{{ previewError }}</span>
        </template>
        <template v-else-if="resolvedInsuranceSalaryLabel">
          <div class="preview-amount">{{ resolvedInsuranceSalaryLabel }}</div>
          <small v-if="previewMetaLine">{{ previewMetaLine }}</small>
        </template>
        <template v-else>
          Chưa đủ dữ liệu để tính preview.
        </template>
      </div>
    </div>

    <div class="field">
      <label>Ghi chú</label>
      <Textarea
        v-model="form.notes"
        class="w-full"
        rows="2"
        placeholder="Tùy chọn"
        auto-resize
      />
    </div>

    <template #footer>
      <Button label="Hủy" severity="secondary" outlined :disabled="submitting" @click="visible = false" />
      <Button
        :label="isEdit ? 'Lưu thay đổi' : 'Tạo hợp đồng'"
        icon="pi pi-check"
        :loading="submitting"
        @click="submit"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'

import contractService, {
  type ContractInsuranceSalaryPreviewRead,
  type ContractRead,
  type InsuranceSalaryMode,
} from '@/services/contractService'
import employeeService from '@/services/employeeService'
import insuranceService, { type BhxhPositionGroupRead } from '@/services/insuranceService'
import otherBusinessCatalogService, { type ContractCategoryRead } from '@/services/otherBusinessCatalogService'

interface Props {
  employeeId: number
  contract?: ContractRead | null
  existingContracts?: ContractRead[]
}

const props   = withDefaults(defineProps<Props>(), { contract: null, existingContracts: () => [] })
const emit    = defineEmits<{ saved: [] }>()
const toast   = useToast()
const visible = defineModel<boolean>({ default: false })

const isEdit    = computed(() => !!props.contract)
const submitting = ref(false)
const errors     = ref<Record<string, string>>({})

const categories = ref<ContractCategoryRead[]>([])
const positionGroups = ref<BhxhPositionGroupRead[]>([])
const employeeCurrentJobPositionId = ref<number | null>(null)
const loadingInsuranceConfig = ref(false)
const preview = ref<ContractInsuranceSalaryPreviewRead | null>(null)
const previewLoading = ref(false)
const previewError = ref('')
let previewRequestSeq = 0

const categoryOptions = computed(() =>
  categories.value
    .filter(c => c.is_active)
    .map(c => ({ label: `${c.name} (${c.document_kind === 'labor_contract' ? 'HĐ' : 'PL'})`, value: c.id }))
)

const parentOptions = computed(() =>
  props.existingContracts
    .filter(c => c.document_kind === 'labor_contract')
    .map(c => ({ label: c.contract_number, value: c.id }))
)

const insuranceSalaryModeOptions = [
  { label: 'Theo nhóm vị trí + bậc', value: 'computed_by_position_group' },
  { label: 'Cố định theo thỏa thuận', value: 'fixed_manual' },
] satisfies Array<{ label: string; value: InsuranceSalaryMode }>

const gradeOptions = Array.from({ length: 7 }, (_, idx) => ({
  label: `Bậc ${idx + 1}`,
  value: idx + 1,
}))

const positionGroupOptions = computed(() =>
  positionGroups.value
    .filter((group) => group.is_active)
    .map((group) => ({
      label: `${group.name} (${group.code})`,
      value: group.id,
    })),
)

const resolvedInsuranceSalaryLabel = computed(() => {
  if (preview.value?.insurance_salary) {
    return formatCurrency(preview.value.insurance_salary)
  }
  if (
    form.value.insurance_salary_mode === 'fixed_manual' &&
    form.value.insurance_salary_fixed_amount_n != null
  ) {
    return formatCurrency(String(form.value.insurance_salary_fixed_amount_n))
  }
  return null
})

const previewMetaLine = computed(() => {
  if (!preview.value) return null
  if (preview.value.insurance_salary_mode === 'fixed_manual') {
    return 'Mode cố định theo thỏa thuận'
  }
  const baseGrade = preview.value.insurance_salary_grade_no != null
    ? `Bậc gốc ${preview.value.insurance_salary_grade_no}`
    : null
  const resolvedGrade = preview.value.resolved_insurance_salary_grade_no != null
    ? `Bậc áp dụng ${preview.value.resolved_insurance_salary_grade_no}`
    : null
  const region = preview.value.company_region != null ? `Vùng ${preview.value.company_region}` : null
  const minimumWage = preview.value.regional_minimum_wage
    ? formatCurrency(preview.value.regional_minimum_wage)
    : null
  const coefficient = preview.value.coefficient ? `Hệ số ${preview.value.coefficient}` : null
  return [baseGrade, resolvedGrade, region, minimumWage, coefficient].filter(Boolean).join(' · ')
})

// ── Form state ────────────────────────────────────────────────────────────────
const form = ref({
  contract_category_id: null as number | null,
  parent_contract_id:   null as number | null,
  contract_number:      '',
  signed_date_d:        null as Date | null,
  effective_from_d:     null as Date | null,
  effective_to_d:       null as Date | null,
  insurance_salary_mode: 'computed_by_position_group' as InsuranceSalaryMode,
  bhxh_position_group_id: null as number | null,
  insurance_salary_grade_no: 1 as number | null,
  insurance_salary_fixed_amount_n: null as number | null,
  notes:                '',
})

function toIso(d: Date | null): string | null {
  if (!d) return null
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function fromIso(s: string | null | undefined): Date | null {
  return s ? new Date(s) : null
}

function formatCurrency(value: string | number | null): string {
  if (value == null || value === '') return '—'
  const parsed = typeof value === 'number' ? value : Number(value)
  if (Number.isNaN(parsed)) return '—'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(parsed)
}

function getDefaultComputedGroupId(): number | null {
  if (!employeeCurrentJobPositionId.value) return null
  const match = positionGroups.value.find((group) =>
    group.members.some((member) => member.job_position_id === employeeCurrentJobPositionId.value),
  )
  return match?.id ?? null
}

async function loadInsuranceConfig() {
  loadingInsuranceConfig.value = true
  try {
    const [groupRes, employeeRes] = await Promise.all([
      insuranceService.getPositionGroups(),
      employeeService.get(props.employeeId),
    ])
    positionGroups.value = groupRes.data.groups
    employeeCurrentJobPositionId.value = employeeRes.data.current_job?.job_position?.id ?? null
  } catch {
    positionGroups.value = []
    employeeCurrentJobPositionId.value = null
  } finally {
    loadingInsuranceConfig.value = false
  }
}

async function refreshPreview() {
  preview.value = null
  previewError.value = ''

  const effectiveFrom = toIso(form.value.effective_from_d)
  if (!effectiveFrom) return

  if (form.value.insurance_salary_mode === 'fixed_manual') {
    if (form.value.insurance_salary_fixed_amount_n == null) return
  } else {
    if (!form.value.bhxh_position_group_id || !form.value.insurance_salary_grade_no) return
  }

  previewLoading.value = true
  const requestId = ++previewRequestSeq
  try {
    const res = await contractService.previewInsuranceSalary(props.employeeId, {
      effective_from: effectiveFrom,
      insurance_salary_mode: form.value.insurance_salary_mode,
      bhxh_position_group_id: form.value.bhxh_position_group_id,
      insurance_salary_grade_no: form.value.insurance_salary_grade_no,
      insurance_salary_fixed_amount:
        form.value.insurance_salary_fixed_amount_n != null
          ? String(form.value.insurance_salary_fixed_amount_n)
          : null,
    })
    if (requestId !== previewRequestSeq) return
    preview.value = res.data
  } catch (e: unknown) {
    if (requestId !== previewRequestSeq) return
    const err = e as { response?: { data?: { detail?: unknown } } }
    const detail = err.response?.data?.detail
    previewError.value = typeof detail === 'string' ? detail : 'Không tính được preview lương BH'
  } finally {
    if (requestId === previewRequestSeq) {
      previewLoading.value = false
    }
  }
}

// Reset form when dialog opens
watch(visible, async (v) => {
  if (!v) return
  errors.value = {}
  preview.value = null
  previewError.value = ''
  await loadInsuranceConfig()
  if (props.contract) {
    const c = props.contract
    form.value = {
      contract_category_id: c.contract_category_id,
      parent_contract_id:   c.parent_contract_id,
      contract_number:      c.contract_number,
      signed_date_d:        fromIso(c.signed_date),
      effective_from_d:     fromIso(c.effective_from),
      effective_to_d:       fromIso(c.effective_to),
      insurance_salary_mode: c.insurance_salary_mode,
      bhxh_position_group_id: c.bhxh_position_group_id,
      insurance_salary_grade_no: c.insurance_salary_grade_no ?? 1,
      insurance_salary_fixed_amount_n: c.insurance_salary_fixed_amount ? parseFloat(c.insurance_salary_fixed_amount) : null,
      notes:                c.notes ?? '',
    }
    await refreshPreview()
  } else {
    const defaultGroupId = getDefaultComputedGroupId()
    form.value = {
      contract_category_id: null,
      parent_contract_id:   null,
      contract_number:      '',
      signed_date_d:        null,
      effective_from_d:     null,
      effective_to_d:       null,
      insurance_salary_mode: 'computed_by_position_group',
      bhxh_position_group_id: defaultGroupId,
      insurance_salary_grade_no: 1,
      insurance_salary_fixed_amount_n: null,
      notes:                '',
    }
  }
})

// Load categories on mount
async function loadCategories() {
  try {
    const res = await otherBusinessCatalogService.lookupContractCategories({ is_active: true })
    categories.value = res.data
  } catch {
    // ignore
  }
}
loadCategories()

// ── Validation ────────────────────────────────────────────────────────────────
function validate(): boolean {
  errors.value = {}
  if (!form.value.contract_category_id) errors.value.contract_category_id = 'Chọn loại hợp đồng'
  if (!form.value.contract_number.trim()) errors.value.contract_number = 'Số hợp đồng không được để trống'
  if (!form.value.signed_date_d) errors.value.signed_date = 'Chọn ngày ký'
  if (!form.value.effective_from_d) errors.value.effective_from = 'Chọn ngày hiệu lực'
  if (!form.value.insurance_salary_mode) errors.value.insurance_salary_mode = 'Chọn mode lương đóng BH'
  if (form.value.insurance_salary_mode === 'computed_by_position_group') {
    if (!form.value.bhxh_position_group_id) errors.value.bhxh_position_group_id = 'Chọn nhóm vị trí BHXH'
    if (!form.value.insurance_salary_grade_no) errors.value.insurance_salary_grade_no = 'Chọn bậc hệ số'
  } else if (form.value.insurance_salary_fixed_amount_n == null || form.value.insurance_salary_fixed_amount_n <= 0) {
    errors.value.insurance_salary_fixed_amount = 'Nhập mức lương đóng BH cố định > 0'
  }
  if (
    form.value.effective_to_d &&
    form.value.effective_from_d &&
    form.value.effective_to_d < form.value.effective_from_d
  ) {
    errors.value.effective_from = 'Ngày hết hạn phải >= ngày hiệu lực'
  }
  return Object.keys(errors.value).length === 0
}

// ── Submit ────────────────────────────────────────────────────────────────────
async function submit() {
  if (!validate()) return
  submitting.value = true
  try {
    if (isEdit.value && props.contract) {
      const payload = {
        contract_number:  form.value.contract_number.trim(),
        signed_date:      toIso(form.value.signed_date_d)!,
        effective_from:   toIso(form.value.effective_from_d)!,
        effective_to:     toIso(form.value.effective_to_d),
        insurance_salary_mode: form.value.insurance_salary_mode,
        bhxh_position_group_id: form.value.insurance_salary_mode === 'computed_by_position_group'
          ? form.value.bhxh_position_group_id
          : null,
        insurance_salary_grade_no: form.value.insurance_salary_mode === 'computed_by_position_group'
          ? form.value.insurance_salary_grade_no
          : null,
        insurance_salary_fixed_amount: form.value.insurance_salary_mode === 'fixed_manual' && form.value.insurance_salary_fixed_amount_n != null
          ? String(form.value.insurance_salary_fixed_amount_n) : null,
        insurance_salary: form.value.insurance_salary_mode === 'fixed_manual' && form.value.insurance_salary_fixed_amount_n != null
          ? String(form.value.insurance_salary_fixed_amount_n) : null,
        notes: form.value.notes.trim() || null,
      }
      await contractService.updateContract(props.employeeId, props.contract.id, payload)
      toast.add({ severity: 'success', summary: 'Đã cập nhật hợp đồng', life: 3000 })
    } else {
      const payload = {
        contract_category_id: form.value.contract_category_id!,
        contract_number:      form.value.contract_number.trim(),
        signed_date:          toIso(form.value.signed_date_d)!,
        effective_from:       toIso(form.value.effective_from_d)!,
        effective_to:         toIso(form.value.effective_to_d),
        insurance_salary_mode: form.value.insurance_salary_mode,
        bhxh_position_group_id: form.value.insurance_salary_mode === 'computed_by_position_group'
          ? form.value.bhxh_position_group_id
          : null,
        insurance_salary_grade_no: form.value.insurance_salary_mode === 'computed_by_position_group'
          ? form.value.insurance_salary_grade_no
          : null,
        insurance_salary_fixed_amount: form.value.insurance_salary_mode === 'fixed_manual' && form.value.insurance_salary_fixed_amount_n != null
          ? String(form.value.insurance_salary_fixed_amount_n) : null,
        insurance_salary: form.value.insurance_salary_mode === 'fixed_manual' && form.value.insurance_salary_fixed_amount_n != null
          ? String(form.value.insurance_salary_fixed_amount_n) : null,
        parent_contract_id:   form.value.parent_contract_id,
        notes:                form.value.notes.trim() || null,
      }
      await contractService.createContract(props.employeeId, payload)
      toast.add({ severity: 'success', summary: 'Đã tạo hợp đồng', life: 3000 })
    }
    visible.value = false
    emit('saved')
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: unknown } } }
    const detail = err.response?.data?.detail
    const msg = typeof detail === 'string' ? detail : 'Không lưu được hợp đồng'
    toast.add({ severity: 'error', summary: 'Lỗi', detail: msg, life: 5000 })
  } finally {
    submitting.value = false
  }
}

watch(
  () => [
    form.value.insurance_salary_mode,
    form.value.bhxh_position_group_id,
    form.value.insurance_salary_grade_no,
    form.value.insurance_salary_fixed_amount_n,
    form.value.effective_from_d?.toISOString() ?? null,
  ],
  async () => {
    if (!visible.value) return
    await refreshPreview()
  },
)
</script>
