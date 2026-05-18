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
        <label>Mức lương đóng BH (VNĐ)</label>
        <InputNumber
          v-model="form.insurance_salary_n"
          class="w-full"
          :use-grouping="true"
          :min="0"
          :max="999999999"
          placeholder="Tùy chọn"
        />
      </div>
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

import contractService, { type ContractRead } from '@/services/contractService'
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

// ── Form state ────────────────────────────────────────────────────────────────
const form = ref({
  contract_category_id: null as number | null,
  parent_contract_id:   null as number | null,
  contract_number:      '',
  signed_date_d:        null as Date | null,
  effective_from_d:     null as Date | null,
  effective_to_d:       null as Date | null,
  insurance_salary_n:   null as number | null,
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

// Reset form when dialog opens
watch(visible, (v) => {
  if (!v) return
  errors.value = {}
  if (props.contract) {
    const c = props.contract
    form.value = {
      contract_category_id: c.contract_category_id,
      parent_contract_id:   c.parent_contract_id,
      contract_number:      c.contract_number,
      signed_date_d:        fromIso(c.signed_date),
      effective_from_d:     fromIso(c.effective_from),
      effective_to_d:       fromIso(c.effective_to),
      insurance_salary_n:   c.insurance_salary ? parseFloat(c.insurance_salary) : null,
      notes:                c.notes ?? '',
    }
  } else {
    form.value = {
      contract_category_id: null,
      parent_contract_id:   null,
      contract_number:      '',
      signed_date_d:        null,
      effective_from_d:     null,
      effective_to_d:       null,
      insurance_salary_n:   null,
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
        insurance_salary: form.value.insurance_salary_n != null
          ? String(form.value.insurance_salary_n) : null,
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
        insurance_salary:     form.value.insurance_salary_n != null
          ? String(form.value.insurance_salary_n) : null,
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
</script>
