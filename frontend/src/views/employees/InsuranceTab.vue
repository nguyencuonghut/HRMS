<template>
  <div class="insurance-tab">
    <!-- Loading -->
    <div v-if="loading" class="ins-tab-loading">
      <i class="pi pi-spin pi-spinner" />
      <span>Đang tải hồ sơ bảo hiểm...</span>
    </div>

    <template v-else-if="profile">
      <!-- Summary header -->
      <div class="ins-tab-header">
        <div class="ins-tab-meta">
          <Tag
            :value="statusLabel(profile.participation_status)"
            :severity="statusSeverity(profile.participation_status)"
          />
          <span v-if="profile.policy_version_name" class="ins-tab-policy">
            Policy: <strong>{{ profile.policy_version_name }}</strong>
          </span>
        </div>
        <div class="ins-tab-actions">
          <Button
            v-can:edit="'insurance'"
            v-if="!editing"
            label="Chỉnh sửa"
            icon="pi pi-pencil"
            severity="secondary"
            @click="startEdit"
          />
          <template v-else>
            <Button label="Hủy" severity="secondary" text :disabled="saving" @click="cancelEdit" />
            <Button v-can:edit="'insurance'" label="Lưu" icon="pi pi-save" :loading="saving" @click="save" />
          </template>
        </div>
      </div>

      <!-- Read mode -->
      <template v-if="!editing">
        <div class="ins-tab-info-grid">
          <div class="info-row">
            <span class="info-label">Mã số BHXH</span>
            <span class="info-value">{{ profile.bhxh_code || '—' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Mã BH chăm sóc sức khỏe</span>
            <span class="info-value">{{ profile.health_care_insurance_code || '—' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Người thân tham gia CSSK</span>
            <span class="info-value">
              <template v-if="profile.health_care_insurance_code">
                {{ profile.health_care_family_participation ? 'Có' : 'Không' }}
              </template>
              <span v-else class="text-muted">—</span>
            </span>
          </div>
          <div class="info-row">
            <span class="info-label">Mã BH tai nạn</span>
            <span class="info-value">{{ profile.accident_insurance_code || '—' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Nơi KCB ban đầu</span>
            <span class="info-value">{{ profile.bhyt_initial_clinic_name || '—' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Ngày tham gia tại công ty</span>
            <span class="info-value">{{ formatDate(profile.company_bhxh_joined_date) }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Nền tính BHXH</span>
            <span class="info-value">
              <template v-if="profile.insurance_basis_amount">
                {{ formatCurrency(profile.insurance_basis_amount) }}
                <small class="ins-basis-source">({{ basisSourceLabel(profile.insurance_basis_source) }})</small>
              </template>
              <span v-else class="text-muted">Chưa xác định</span>
            </span>
          </div>
          <div v-if="profile.contract_number" class="info-row">
            <span class="info-label">Hợp đồng hiện hành</span>
            <span class="info-value">{{ profile.contract_number }}</span>
          </div>
          <div v-if="profile.status_note" class="info-row">
            <span class="info-label">Ghi chú trạng thái</span>
            <span class="info-value">{{ profile.status_note }}</span>
          </div>
        </div>

        <!-- Contributions snapshot -->
        <div v-if="profile.contributions.length > 0" class="ins-tab-contribs">
          <h4 class="ins-tab-section-title">Mức đóng theo policy</h4>
          <div class="ins-tab-contrib-table">
            <div class="ins-contrib-head">
              <span>Khoản đóng</span>
              <span>NLĐ</span>
              <span>NSDLĐ</span>
              <span>Cách tính</span>
            </div>
            <div
              v-for="c in profile.contributions"
              :key="c.component_code"
              class="ins-contrib-row"
            >
              <span class="ins-contrib-name">{{ c.component_name }}</span>
              <span>{{ formatContribAmount(c.employee_amount, c.employee_rate_percent) }}</span>
              <span>{{ formatContribAmount(c.employer_amount, c.employer_rate_percent) }}</span>
              <span>
                <Tag
                  v-if="c.calc_mode === 'fixed_amount'"
                  value="Cố định"
                  severity="warn"
                  class="ins-calc-tag"
                />
                <span v-else class="text-muted" style="font-size: 0.82rem">Theo policy</span>
                <Tag
                  v-if="c.employer_advances_employee_part"
                  value="Nộp hộ"
                  severity="info"
                  class="ins-calc-tag"
                />
              </span>
            </div>
          </div>
        </div>
      </template>

      <!-- Edit mode -->
      <template v-else>
        <div class="field-row">
          <div class="field">
            <label>Mã số BHXH</label>
            <InputText v-model="form.bhxh_code" class="w-full" placeholder="Nhập mã BHXH..." />
          </div>
          <div class="field">
            <label>Mã BH tai nạn</label>
            <InputText v-model="form.accident_insurance_code" class="w-full" placeholder="Nhập mã BH tai nạn..." />
          </div>
        </div>

        <div class="field-row">
          <div class="field">
            <label>Mã BH chăm sóc sức khỏe</label>
            <InputText v-model="form.health_care_insurance_code" class="w-full" placeholder="Nhập mã BH CSSK..." />
          </div>
          <div class="field">
            <label>Tham gia CSSK cho người thân</label>
            <div class="ins-checkbox-panel" :class="{ 'is-disabled': !form.health_care_insurance_code }">
              <div class="ins-checkbox-row">
                <label class="ins-toggle-label">
                  <Checkbox
                    v-model="form.health_care_family_participation"
                    :binary="true"
                    :disabled="!form.health_care_insurance_code"
                  />
                  Người thân tham gia cùng
                </label>
                <small class="text-muted">
                  {{
                    form.health_care_insurance_code
                      ? 'Bật khi hợp đồng CSSK có đăng ký thêm người thân.'
                      : 'Nhập mã BH CSSK trước khi chọn.'
                  }}
                </small>
              </div>
            </div>
          </div>
        </div>

        <div class="field-row">
          <div class="field">
            <label>Nơi KCB ban đầu</label>
            <BhytClinicSelect v-model="form.bhyt_initial_clinic" />
          </div>
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
            <InputText v-model="form.status_note" class="w-full" placeholder="Lý do dừng..." />
          </div>
        </div>

        <div class="field-sep" />

        <div class="field-row">
          <div class="field">
            <label>Nguồn nền tính BHXH</label>
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
            <label v-if="form.insurance_basis_source === 'manual_fixed'">
              Mức lương cố định <span class="req">*</span>
            </label>
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
              <span v-if="profile.insurance_basis_amount">
                {{ formatCurrency(profile.insurance_basis_amount) }}
              </span>
              <span v-else class="text-muted">Chưa có mức BHXH trong hợp đồng hiện hành</span>
            </div>
          </div>
        </div>
      </template>
    </template>

    <!-- No profile -->
    <div v-else class="ins-tab-empty">
      <i class="pi pi-shield" style="font-size: 2rem; color: var(--p-text-muted-color)" />
      <p>Chưa có hồ sơ bảo hiểm</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import DatePicker from 'primevue/datepicker'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import BhytClinicSelect from '@/components/catalog/BhytClinicSelect.vue'
import { type BhytClinicRead } from '@/services/bhytClinicService'
import insuranceService, { type EmployeeInsuranceProfileRead } from '@/services/insuranceService'

const props = defineProps<{ employeeId: number }>()
const emit  = defineEmits<{ refresh: [] }>()

// ── State ──────────────────────────────────────────────────────────────────────

const loading = ref(false)
const saving  = ref(false)
const editing = ref(false)
const profile = ref<EmployeeInsuranceProfileRead | null>(null)

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
})

// ── Options ────────────────────────────────────────────────────────────────────

const statusOptions = [
  { label: 'Đang đóng', value: 'active'  },
  { label: 'Tạm dừng',  value: 'paused'  },
  { label: 'Đã nghỉ',   value: 'stopped' },
]

const basisSourceOptions = [
  { label: 'Từ hợp đồng', value: 'contract'     },
  { label: 'Mức cố định', value: 'manual_fixed'  },
]

// ── Formatters ─────────────────────────────────────────────────────────────────

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

function formatCurrency(val: string | number | null): string {
  if (val == null) return '—'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(Number(val))
}

function formatContribAmount(amount: string | null, rate: string | null): string {
  if (amount != null) return formatCurrency(amount)
  if (rate != null) return `${parseFloat(rate)}%`
  return '—'
}

function statusLabel(s: string): string {
  return { active: 'Đang đóng', paused: 'Tạm dừng', stopped: 'Đã nghỉ' }[s] ?? s
}

function statusSeverity(s: string): string {
  return { active: 'success', paused: 'warn', stopped: 'secondary' }[s] ?? 'secondary'
}

function basisSourceLabel(s: string): string {
  return { contract: 'Từ HĐ', manual_fixed: 'Cố định', computed: 'Tính tự động' }[s] ?? s
}

function fromIsoDate(iso: string | null | undefined): Date | null {
  if (!iso) return null
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d)
}

function toIsoDate(d: Date | null | undefined): string | null {
  if (!d) return null
  const y  = d.getFullYear()
  const m  = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${dd}`
}

// ── Load ───────────────────────────────────────────────────────────────────────

async function load() {
  loading.value = true
  try {
    const res = await insuranceService.getEmployeeProfile(props.employeeId)
    profile.value = res.data
  } catch {
    profile.value = null
  } finally {
    loading.value = false
  }
}

onMounted(load)

// ── Edit ───────────────────────────────────────────────────────────────────────

function startEdit() {
  if (!profile.value) return
  const p = profile.value
  form.value = {
    bhxh_code:                    p.bhxh_code,
    health_care_insurance_code:   p.health_care_insurance_code,
    health_care_family_participation: p.health_care_family_participation ?? false,
    accident_insurance_code:      p.accident_insurance_code,
    bhyt_initial_clinic:          p.bhyt_initial_clinic_code
      ? { id: 0, code: p.bhyt_initial_clinic_code, name: p.bhyt_initial_clinic_name ?? '', province_code: null, province_name: null }
      : null,
    company_bhxh_joined_date_obj: fromIsoDate(p.company_bhxh_joined_date),
    status_effective_from_obj:    fromIsoDate(p.status_effective_from),
    participation_status:         p.participation_status as 'active' | 'paused' | 'stopped',
    status_note:                  p.status_note,
    insurance_basis_source:       p.insurance_basis_source as 'contract' | 'computed' | 'manual_fixed',
    insurance_basis_amount:       p.insurance_basis_amount != null ? Number(p.insurance_basis_amount) : null,
  }
  editing.value = true
}

function cancelEdit() {
  editing.value = false
}

async function save() {
  saving.value = true
  try {
    await insuranceService.updateEmployeeProfile(props.employeeId, {
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
      component_overrides: [],
    })
    editing.value = false
    await load()
    emit('refresh')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.ins-checkbox-panel {
  display: flex;
  justify-content: center;
  min-height: 42px;
  padding: 0.65rem 1rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-md);
  background: color-mix(in srgb, var(--p-content-background) 92%, var(--p-primary-color) 8%);
}

.ins-checkbox-panel.is-disabled {
  background: color-mix(in srgb, var(--p-content-background) 96%, var(--p-surface-500) 4%);
}

.ins-checkbox-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  width: 100%;
}

.ins-toggle-label {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  font-weight: 500;
  color: var(--p-text-color);
  flex: 0 1 auto;
}

.ins-checkbox-panel small {
  line-height: 1.4;
  flex: 1 1 auto;
  margin-left: auto;
  text-align: right;
}

@media (max-width: 960px) {
  .ins-checkbox-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .ins-checkbox-panel {
    min-height: unset;
  }

  .ins-checkbox-panel small {
    margin-left: 0;
    text-align: left;
  }
}
</style>
