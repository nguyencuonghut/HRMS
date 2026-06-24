<template>
  <div class="card insurance-region-history-card">
    <div class="section-heading">
      <h3>Policy tuổi nghỉ hưu</h3>
      <Button
        v-can:create="'insurance'"
        label="Thêm policy tuổi nghỉ hưu"
        icon="pi pi-plus"
        size="small"
        @click="openCreateDialog"
      />
    </div>

    <div v-if="policies.current" class="retirement-policy-current">
      <div>
        <div class="insurance-card-label">Policy hiện hành</div>
        <div class="retirement-policy-name">{{ policies.current.name }}</div>
        <div class="retirement-policy-meta">
          Hiệu lực từ {{ formatDate(policies.current.effective_from) }}
          <template v-if="policies.current.effective_to">
            đến {{ formatDate(policies.current.effective_to) }}
          </template>
        </div>
        <div class="retirement-policy-note">
          {{ policies.current.legal_basis_summary || 'Chưa khai báo căn cứ pháp lý' }}
        </div>
      </div>
      <div class="retirement-policy-actions">
        <Tag
          v-for="item in currentThresholdTags"
          :key="item.gender"
          :value="item.label"
          :severity="item.gender === 'male' ? 'contrast' : 'info'"
        />
        <Button
          v-if="canManagePolicies"
          label="Sửa policy hiện hành"
          icon="pi pi-pencil"
          severity="secondary"
          outlined
          size="small"
          @click="openEditDialog(policies.current)"
        />
      </div>
    </div>

    <DataTable
      v-if="policies.current"
      :value="policies.current.thresholds"
      stripedRows
      responsive-layout="scroll"
      class="retirement-policy-threshold-table"
    >
      <Column field="gender" header="Giới tính" style="width: 140px">
        <template #body="{ data }">{{ genderLabel(data.gender) }}</template>
      </Column>
      <Column field="applicable_year" header="Năm áp dụng" style="width: 140px" />
      <Column header="Tuổi nghỉ hưu" style="width: 180px">
        <template #body="{ data }">
          {{ formatRetirementAge(data.age_years, data.age_months) }}
        </template>
      </Column>
    </DataTable>

    <div class="section-heading retirement-policy-history-heading">
      <h3>Lịch sử policy</h3>
    </div>

    <DataTable :value="policies.history" :loading="loading" stripedRows responsive-layout="scroll">
      <template #empty>
        <div class="empty-state">Chưa có policy tuổi nghỉ hưu nào.</div>
      </template>
      <Column field="name" header="Policy" style="min-width: 240px" />
      <Column header="Hiệu lực từ" style="width: 140px">
        <template #body="{ data }">{{ formatDate(data.effective_from) }}</template>
      </Column>
      <Column header="Hiệu lực đến" style="width: 140px">
        <template #body="{ data }">{{ formatDate(data.effective_to) }}</template>
      </Column>
      <Column field="legal_basis_summary" header="Căn cứ pháp lý" style="min-width: 280px">
        <template #body="{ data }">{{ data.legal_basis_summary || '—' }}</template>
      </Column>
      <Column v-if="canManagePolicies || canDeletePolicies" header="" style="width: 180px">
        <template #body="{ data }">
          <div class="action-cell">
            <Button
              v-if="canManagePolicies"
              icon="pi pi-pencil"
              severity="secondary"
              text
              rounded
              size="small"
              @click="openEditDialog(data)"
            />
            <Button
              v-if="canDeletePolicies"
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

    <Dialog
      v-model:visible="policyDialogVisible"
      modal
      :style="{ width: 'min(1100px, 96vw)' }"
      :header="editingPolicyId ? 'Cập nhật policy tuổi nghỉ hưu' : 'Tạo policy tuổi nghỉ hưu mới'"
    >
      <div class="retirement-policy-form">
        <div class="retirement-policy-grid">
          <div class="retirement-policy-field">
            <label>Tên policy</label>
            <InputText v-model="policyForm.name" class="retirement-policy-input" />
          </div>
          <div v-if="!editingPolicyId" class="retirement-policy-field">
            <label>Ngày hiệu lực</label>
            <DatePicker
              v-model="policyEffectiveFrom"
              date-format="dd/mm/yy"
              show-icon
              class="retirement-policy-input"
            />
          </div>
          <div class="retirement-policy-field retirement-policy-form-span-2">
            <label>Căn cứ pháp lý</label>
            <Textarea
              v-model="policyForm.legal_basis_summary"
              rows="2"
              auto-resize
              class="retirement-policy-input"
            />
          </div>
          <div class="retirement-policy-field retirement-policy-form-span-2">
            <label>Ghi chú</label>
            <Textarea
              v-model="policyForm.note"
              rows="2"
              auto-resize
              class="retirement-policy-input"
            />
          </div>
        </div>

        <div class="retirement-policy-threshold-editor">
          <div class="retirement-policy-threshold-block">
            <div class="retirement-policy-threshold-title">
              <h4>Ngưỡng tuổi nghỉ hưu - Nam</h4>
              <Button icon="pi pi-plus" label="Thêm dòng" size="small" text @click="addThresholdRow('male')" />
            </div>
            <div
              v-for="(row, index) in maleThresholds"
              :key="`male-${index}`"
              class="retirement-policy-threshold-row"
            >
              <InputNumber
                v-model="row.applicable_year"
                :min="1900"
                placeholder="Năm"
                class="retirement-policy-input"
              />
              <InputNumber
                v-model="row.age_years"
                :min="0"
                placeholder="Tuổi"
                class="retirement-policy-input"
              />
              <InputNumber
                v-model="row.age_months"
                :min="0"
                :max="11"
                placeholder="Tháng"
                class="retirement-policy-input"
              />
              <Button icon="pi pi-trash" severity="danger" text @click="removeThresholdRow('male', index)" />
            </div>
          </div>

          <div class="retirement-policy-threshold-block">
            <div class="retirement-policy-threshold-title">
              <h4>Ngưỡng tuổi nghỉ hưu - Nữ</h4>
              <Button icon="pi pi-plus" label="Thêm dòng" size="small" text @click="addThresholdRow('female')" />
            </div>
            <div
              v-for="(row, index) in femaleThresholds"
              :key="`female-${index}`"
              class="retirement-policy-threshold-row"
            >
              <InputNumber
                v-model="row.applicable_year"
                :min="1900"
                placeholder="Năm"
                class="retirement-policy-input"
              />
              <InputNumber
                v-model="row.age_years"
                :min="0"
                placeholder="Tuổi"
                class="retirement-policy-input"
              />
              <InputNumber
                v-model="row.age_months"
                :min="0"
                :max="11"
                placeholder="Tháng"
                class="retirement-policy-input"
              />
              <Button icon="pi pi-trash" severity="danger" text @click="removeThresholdRow('female', index)" />
            </div>
          </div>
        </div>

        <div class="retirement-policy-dialog-actions">
          <Button label="Hủy" severity="secondary" text @click="policyDialogVisible = false" />
          <Button
            :label="editingPolicyId ? 'Lưu cập nhật' : 'Tạo policy'"
            icon="pi pi-check"
            :loading="savingPolicy"
            @click="submitPolicy"
          />
        </div>
      </div>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { usePermissionGate } from '@/composables/usePermissionGate'
import insuranceService from '@/services/insuranceService'
import type {
  HrRetirementAgePoliciesRead,
  HrRetirementAgePolicyRead,
  HrRetirementAgeThresholdInput,
} from '@/types/hr_report.types'

const toast = useToast()
const confirm = useConfirm()
const { canEdit, canDelete } = usePermissionGate()
const now = new Date()

const loading = ref(false)
const savingPolicy = ref(false)
const policies = ref<HrRetirementAgePoliciesRead>({ current: null, history: [] })

const policyDialogVisible = ref(false)
const editingPolicyId = ref<number | null>(null)
const policyEffectiveFrom = ref<Date | null>(new Date(now.getFullYear(), 0, 1))
const policyForm = reactive({
  name: '',
  legal_basis_summary: '',
  note: '',
  thresholds: [] as HrRetirementAgeThresholdInput[],
})

const canManagePolicies = computed(() => canEdit('insurance'))
const canDeletePolicies = computed(() => canDelete('insurance'))

const maleThresholds = computed(() => policyForm.thresholds.filter((item) => item.gender === 'male'))
const femaleThresholds = computed(() => policyForm.thresholds.filter((item) => item.gender === 'female'))
const currentThresholdTags = computed(() =>
  (policies.value.current?.thresholds ?? []).map((item) => ({
    gender: item.gender,
    label: `${genderLabel(item.gender)}: ${formatRetirementAge(item.age_years, item.age_months)} · ${item.applicable_year}`,
  })),
)

function formatDate(value?: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('vi-VN').format(date)
}

function genderLabel(value: string) {
  if (value === 'male') return 'Nam'
  if (value === 'female') return 'Nữ'
  return value
}

function formatRetirementAge(years: number, months: number) {
  return `${years} tuổi ${months} tháng`
}

function cloneThresholds(policy?: HrRetirementAgePolicyRead | null): HrRetirementAgeThresholdInput[] {
  return (policy?.thresholds ?? []).map((item) => ({
    gender: item.gender as 'male' | 'female',
    applicable_year: item.applicable_year,
    age_years: item.age_years,
    age_months: item.age_months,
  }))
}

function resetPolicyForm(policy?: HrRetirementAgePolicyRead | null) {
  editingPolicyId.value = policy?.id ?? null
  policyForm.name = policy?.name ?? ''
  policyForm.legal_basis_summary = policy?.legal_basis_summary ?? ''
  policyForm.note = policy?.note ?? ''
  policyForm.thresholds = cloneThresholds(policy)
  policyEffectiveFrom.value = policy?.effective_from ? new Date(policy.effective_from) : new Date(now.getFullYear(), 0, 1)
}

function openCreateDialog() {
  resetPolicyForm(policies.value.current)
  editingPolicyId.value = null
  policyDialogVisible.value = true
}

function openEditDialog(policy: HrRetirementAgePolicyRead) {
  resetPolicyForm(policy)
  policyDialogVisible.value = true
}

function addThresholdRow(targetGender: 'male' | 'female') {
  policyForm.thresholds.push({
    gender: targetGender,
    applicable_year: now.getFullYear(),
    age_years: 0,
    age_months: 0,
  })
}

function removeThresholdRow(targetGender: 'male' | 'female', index: number) {
  const rows = policyForm.thresholds
    .map((item, originalIndex) => ({ item, originalIndex }))
    .filter(({ item }) => item.gender === targetGender)
  const target = rows[index]
  if (!target) return
  policyForm.thresholds.splice(target.originalIndex, 1)
}

function errorDetail(error: any, fallback: string) {
  return error?.response?.data?.detail || error?.message || fallback
}

async function loadPolicies() {
  loading.value = true
  try {
    const res = await insuranceService.getRetirementAgePolicies()
    policies.value = res.data
  } catch {
    policies.value = { current: null, history: [] }
  } finally {
    loading.value = false
  }
}

async function submitPolicy() {
  savingPolicy.value = true
  try {
    const thresholds = [...policyForm.thresholds].sort((a, b) =>
      a.gender === b.gender
        ? a.applicable_year - b.applicable_year
        : a.gender.localeCompare(b.gender),
    )
    if (editingPolicyId.value) {
      const res = await insuranceService.updateRetirementAgePolicy(editingPolicyId.value, {
        name: policyForm.name,
        legal_basis_summary: policyForm.legal_basis_summary || null,
        note: policyForm.note || null,
        thresholds,
      })
      policies.value = res.data
    } else {
      const effectiveFrom = policyEffectiveFrom.value
        ? policyEffectiveFrom.value.toISOString().slice(0, 10)
        : null
      if (!effectiveFrom) {
        throw new Error('Ngày hiệu lực là bắt buộc')
      }
      const res = await insuranceService.createRetirementAgePolicy({
        name: policyForm.name,
        legal_basis_summary: policyForm.legal_basis_summary || null,
        effective_from: effectiveFrom,
        note: policyForm.note || null,
        thresholds,
      })
      policies.value = res.data
    }
    policyDialogVisible.value = false
    toast.add({
      severity: 'success',
      summary: 'Đã lưu policy',
      detail: 'Cấu hình tuổi nghỉ hưu đã được cập nhật.',
      life: 3000,
    })
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Không lưu được policy',
      detail: errorDetail(error, 'Vui lòng thử lại.'),
      life: 4000,
    })
  } finally {
    savingPolicy.value = false
  }
}

function confirmDeletePolicy(policy: HrRetirementAgePolicyRead) {
  confirm.require({
    message: `Xóa policy "${policy.name}"?`,
    header: 'Xác nhận xóa policy',
    icon: 'pi pi-exclamation-triangle',
    rejectProps: {
      label: 'Hủy',
      severity: 'secondary',
      outlined: true,
    },
    acceptProps: {
      label: 'Xóa',
      severity: 'danger',
    },
    accept: async () => {
      try {
        const res = await insuranceService.deleteRetirementAgePolicy(policy.id)
        policies.value = res.data
        toast.add({
          severity: 'success',
          summary: 'Đã xóa policy',
          detail: 'Policy tuổi nghỉ hưu đã được xóa.',
          life: 3000,
        })
      } catch (error: any) {
        toast.add({
          severity: 'error',
          summary: 'Không xóa được policy',
          detail: errorDetail(error, 'Vui lòng thử lại.'),
          life: 4000,
        })
      }
    },
  })
}

onMounted(loadPolicies)
</script>

<style scoped>
.retirement-policy-current {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}

.retirement-policy-name {
  font-size: 1rem;
  font-weight: 700;
  color: var(--l-text);
}

.retirement-policy-meta,
.retirement-policy-note {
  margin-top: 0.35rem;
  color: var(--l-text-muted);
}

.retirement-policy-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: flex-start;
}

.retirement-policy-threshold-table {
  margin-bottom: 1.25rem;
}

.retirement-policy-history-heading {
  margin-top: 0.5rem;
}

.retirement-policy-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.retirement-policy-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.retirement-policy-field {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  min-width: 0;
}

.retirement-policy-field label {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--l-text-muted);
}

.retirement-policy-form-span-2 {
  grid-column: span 2;
}

.retirement-policy-input {
  width: 100%;
}

.retirement-policy-field :deep(.p-inputtext),
.retirement-policy-field :deep(.p-datepicker),
.retirement-policy-field :deep(.p-inputnumber),
.retirement-policy-field :deep(textarea) {
  width: 100%;
}

.retirement-policy-threshold-editor {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.retirement-policy-threshold-block {
  padding: 1rem;
  border: 1px solid var(--l-border);
  border-radius: 0.9rem;
  background: color-mix(in srgb, var(--l-surface) 92%, transparent);
  min-width: 0;
}

.retirement-policy-threshold-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.retirement-policy-threshold-title h4 {
  margin: 0;
  font-size: 0.95rem;
}

.retirement-policy-threshold-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr)) auto;
  gap: 0.75rem;
  align-items: center;
  margin-bottom: 0.75rem;
  min-width: 0;
}

.retirement-policy-threshold-row :deep(.p-inputnumber),
.retirement-policy-threshold-row :deep(.p-inputtext) {
  width: 100%;
}

.retirement-policy-dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

@media (max-width: 1023px) {
  .retirement-policy-grid {
    grid-template-columns: 1fr;
  }

  .retirement-policy-threshold-editor {
    grid-template-columns: 1fr;
  }

  .retirement-policy-form-span-2 {
    grid-column: auto;
  }
}

@media (max-width: 767px) {
  .retirement-policy-threshold-row {
    grid-template-columns: 1fr;
  }
}
</style>
