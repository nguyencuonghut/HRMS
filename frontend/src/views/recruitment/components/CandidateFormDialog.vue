<template>
  <Dialog
    v-model:visible="visible"
    :header="editing ? 'Sửa ứng viên' : 'Thêm ứng viên'"
    modal
    :style="{ width: '760px' }"
    @hide="resetForm"
  >
    <div class="rc-form">
      <div class="rc-field">
        <label class="rc-label">Họ và tên <span class="req">*</span></label>
        <InputText v-model="form.full_name" placeholder="Nguyễn Văn A" />
        <small v-if="errors.full_name" class="rc-error">{{ errors.full_name }}</small>
      </div>

      <div class="rc-row">
        <div class="rc-field">
          <label class="rc-label">Họ</label>
          <InputText v-model="form.last_name" placeholder="Nguyễn Văn" />
        </div>
        <div class="rc-field">
          <label class="rc-label">Tên</label>
          <InputText v-model="form.first_name" placeholder="A" />
        </div>
      </div>

      <div class="rc-row">
        <div class="rc-field">
          <label class="rc-label">Email cá nhân</label>
          <InputText v-model="form.personal_email" placeholder="email@example.com" />
        </div>
        <div class="rc-field">
          <label class="rc-label">Điện thoại</label>
          <InputText v-model="form.phone_number" placeholder="0901234567" />
        </div>
      </div>
      <small v-if="errors.identity_anchor" class="rc-error">{{ errors.identity_anchor }}</small>
      <small class="rc-muted">Khi tạo mới cần ít nhất một thông tin định danh: email, SĐT, CCCD/CMND hoặc hộ chiếu.</small>

      <div v-if="checkingDuplicates" class="rc-dup-panel rc-dup-panel--loading">
        <i class="pi pi-spin pi-spinner" />
        <span>Đang kiểm tra hồ sơ trùng...</span>
      </div>

      <div v-else-if="hasDuplicateWarnings" class="rc-dup-panel">
        <div class="rc-dup-header">
          <i class="pi pi-exclamation-triangle" />
          <span>Đã tìm thấy hồ sơ ứng viên có thể trùng</span>
        </div>

        <div v-if="duplicateCheckResult.exact_matches.length" class="rc-dup-section">
          <div class="rc-dup-section-title">Trùng mạnh</div>
          <div
            v-for="match in duplicateCheckResult.exact_matches"
            :key="`exact-${match.candidate_id}`"
            class="rc-dup-item rc-dup-item--exact"
          >
            <div class="rc-dup-item-top">
              <div>
                <strong>{{ match.full_name }}</strong>
                <span v-if="match.date_of_birth" class="rc-muted"> · {{ formatDate(match.date_of_birth) }}</span>
                <span v-if="match.current_company" class="rc-muted"> · {{ match.current_company }}</span>
              </div>
              <Button
                type="button"
                label="Mở hồ sơ"
                icon="pi pi-external-link"
                size="small"
                text
                @click="openCandidateDetail(match.candidate_id)"
              />
            </div>
            <div class="rc-dup-item-meta">
              <span v-if="match.personal_email">{{ match.personal_email }}</span>
              <span v-if="match.personal_email && match.phone_number"> · </span>
              <span v-if="match.phone_number">{{ match.phone_number }}</span>
              <span v-if="!match.personal_email && !match.phone_number">Không có email/SĐT</span>
            </div>
            <div class="rc-dup-reasons">
              <Tag
                v-for="reason in match.reason_labels"
                :key="`${match.candidate_id}-${reason}`"
                :value="reason"
                severity="danger"
              />
            </div>
          </div>
        </div>

        <div v-if="duplicateCheckResult.possible_matches.length" class="rc-dup-section">
          <div class="rc-dup-section-title">Có thể trùng</div>
          <div
            v-for="match in duplicateCheckResult.possible_matches"
            :key="`possible-${match.candidate_id}`"
            class="rc-dup-item"
          >
            <div class="rc-dup-item-top">
              <div>
                <strong>{{ match.full_name }}</strong>
                <span v-if="match.date_of_birth" class="rc-muted"> · {{ formatDate(match.date_of_birth) }}</span>
                <span v-if="match.current_company" class="rc-muted"> · {{ match.current_company }}</span>
              </div>
              <Button
                type="button"
                label="Mở hồ sơ"
                icon="pi pi-external-link"
                size="small"
                text
                @click="openCandidateDetail(match.candidate_id)"
              />
            </div>
            <div class="rc-dup-item-meta">
              <span v-if="match.personal_email">{{ match.personal_email }}</span>
              <span v-if="match.personal_email && match.phone_number"> · </span>
              <span v-if="match.phone_number">{{ match.phone_number }}</span>
              <span v-if="!match.personal_email && !match.phone_number">Không có email/SĐT</span>
            </div>
            <div class="rc-dup-reasons">
              <Tag
                v-for="reason in match.reason_labels"
                :key="`${match.candidate_id}-${reason}`"
                :value="reason"
                severity="warn"
              />
            </div>
          </div>
        </div>
      </div>

      <div class="rc-row">
        <div class="rc-field">
          <label class="rc-label">Ngày sinh</label>
          <DatePicker v-model="dateOfBirth" date-format="dd/mm/yy" show-button-bar placeholder="dd/mm/yyyy" />
        </div>
        <div class="rc-field">
          <label class="rc-label">Giới tính</label>
          <Select
            v-model="form.gender"
            :options="genderOptions"
            option-label="label"
            option-value="value"
            placeholder="Chọn"
            show-clear
          />
        </div>
      </div>

      <div class="rc-row">
        <div class="rc-field">
          <label class="rc-label">Quốc tịch</label>
          <NationalitySelect v-model="form.nationality_id" />
        </div>
        <div class="rc-field">
          <label class="rc-label">Quốc tịch thô <span class="rc-optional">(dùng khi import/map chưa chuẩn)</span></label>
          <InputText v-model="form.raw_nationality_text" placeholder="Việt Nam" />
        </div>
      </div>

      <div class="rc-row">
        <div class="rc-field">
          <label class="rc-label">Dân tộc</label>
          <EthnicitySelect v-model="form.ethnicity_id" />
        </div>
        <div class="rc-field">
          <label class="rc-label">Tôn giáo</label>
          <ReligionSelect v-model="form.religion_id" />
        </div>
      </div>

      <div class="rc-row">
        <div class="rc-field">
          <label class="rc-label">Số CCCD / Hộ chiếu</label>
          <InputText v-model="form.id_number" />
        </div>
        <div class="rc-field">
          <label class="rc-label">Ngày cấp</label>
          <DatePicker v-model="idIssuedOn" date-format="dd/mm/yy" show-button-bar />
        </div>
      </div>

      <div class="rc-row">
        <div class="rc-field">
          <label class="rc-label">Nơi cấp</label>
          <InputText v-model="form.id_issued_by" />
        </div>
        <div class="rc-field">
          <label class="rc-label">Ngày hết hạn giấy tờ</label>
          <DatePicker v-model="idExpiresOn" date-format="dd/mm/yy" show-button-bar />
        </div>
      </div>

      <div class="rc-row">
        <div class="rc-field">
          <label class="rc-label">Mã số thuế cá nhân</label>
          <InputText v-model="form.personal_tax_code" />
        </div>
        <div class="rc-field">
          <label class="rc-label">Mã số BHXH</label>
          <InputText v-model="form.bhxh_code" />
        </div>
      </div>

      <div class="rc-row">
        <div class="rc-field">
          <label class="rc-label">Số hộ chiếu</label>
          <InputText v-model="form.passport_number" />
        </div>
        <div class="rc-field">
          <label class="rc-label">Ngày cấp hộ chiếu</label>
          <DatePicker v-model="passportIssuedOn" date-format="dd/mm/yy" show-button-bar />
        </div>
      </div>

      <div class="rc-row">
        <div class="rc-field">
          <label class="rc-label">Ngày hết hạn hộ chiếu</label>
          <DatePicker v-model="passportExpiresOn" date-format="dd/mm/yy" show-button-bar />
        </div>
        <div class="rc-field">
          <label class="rc-label">Số giấy phép lao động</label>
          <InputText v-model="form.work_permit_number" />
        </div>
      </div>

      <div class="rc-row">
        <div class="rc-field">
          <label class="rc-label">Ngày cấp GPLĐ</label>
          <DatePicker v-model="workPermitIssuedOn" date-format="dd/mm/yy" show-button-bar />
        </div>
        <div class="rc-field">
          <label class="rc-label">Ngày hết hạn GPLĐ</label>
          <DatePicker v-model="workPermitExpiresOn" date-format="dd/mm/yy" show-button-bar />
        </div>
      </div>

      <div class="rc-field">
        <label class="rc-label">Địa chỉ</label>
        <InputText v-model="form.address" />
      </div>

      <div class="rc-row">
        <div class="rc-field">
          <label class="rc-label">Công ty hiện tại</label>
          <InputText v-model="form.current_company" />
        </div>
        <div class="rc-field">
          <label class="rc-label">Vị trí hiện tại</label>
          <InputText v-model="form.current_position" />
        </div>
      </div>

      <div class="rc-row">
        <div class="rc-field">
          <label class="rc-label">Lương kỳ vọng (VNĐ)</label>
          <InputNumber v-model="form.expected_salary" :min="0" locale="vi-VN" />
        </div>
        <div class="rc-field">
          <label class="rc-label">Kênh nguồn</label>
          <Select
            v-model="form.source_channel_id"
            :options="channels"
            option-label="name"
            option-value="id"
            placeholder="Chọn kênh"
            show-clear
          />
        </div>
      </div>

      <div class="rc-field">
        <label class="rc-label">Ghi chú nguồn</label>
        <InputText v-model="form.source_note" />
      </div>

      <div class="rc-field">
        <label class="rc-label">Tags <span class="rc-optional">(Enter để thêm)</span></label>
        <InputChips v-model="form.tags" />
      </div>

      <div class="rc-field">
        <label class="rc-label">Ghi chú nội bộ</label>
        <Textarea v-model="form.internal_note" rows="3" auto-resize />
      </div>

      <p v-if="apiError" class="rc-api-error"><i class="pi pi-exclamation-circle" />{{ apiError }}</p>
    </div>

    <template #footer>
      <Button label="Hủy" severity="secondary" text @click="visible = false" />
      <Button :label="editing ? 'Lưu' : 'Tạo'" :loading="saving" @click="submit" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import Button from 'primevue/button'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import InputChips from 'primevue/inputchips'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import { useToast } from 'primevue/usetoast'
import { useRouter } from 'vue-router'

import EthnicitySelect from '@/components/catalog/EthnicitySelect.vue'
import NationalitySelect from '@/components/catalog/NationalitySelect.vue'
import ReligionSelect from '@/components/catalog/ReligionSelect.vue'
import recruitmentService, {
  type CandidateDuplicateCheck,
  type CandidateDuplicateCheckResult,
  type CandidateRead,
  type RecruitmentChannelRead,
} from '@/services/recruitmentService'

const props = defineProps<{ editing: CandidateRead | null }>()
const emit = defineEmits<{ (e: 'saved'): void }>()
const visible = defineModel<boolean>('visible')

const toast = useToast()
const router = useRouter()
const saving = ref(false)
const apiError = ref('')
const channels = ref<RecruitmentChannelRead[]>([])
const checkingDuplicates = ref(false)
const duplicateCheckResult = ref<CandidateDuplicateCheckResult>({
  exact_matches: [],
  possible_matches: [],
})
const hasDuplicateWarnings = computed(
  () =>
    duplicateCheckResult.value.exact_matches.length > 0 ||
    duplicateCheckResult.value.possible_matches.length > 0,
)

const genderOptions = [
  { label: 'Nam', value: 'male' },
  { label: 'Nữ', value: 'female' },
  { label: 'Khác', value: 'other' },
]

const defaultForm = () => ({
  full_name: '',
  last_name: '',
  first_name: '',
  gender: null as string | null,
  nationality_id: null as number | null,
  raw_nationality_text: '',
  ethnicity_id: null as number | null,
  religion_id: null as number | null,
  id_number: '',
  id_issued_by: '',
  passport_number: '',
  work_permit_number: '',
  phone_number: '',
  personal_email: '',
  personal_tax_code: '',
  bhxh_code: '',
  address: '',
  current_company: '',
  current_position: '',
  expected_salary: null as number | null,
  source_channel_id: null as number | null,
  source_note: '',
  internal_note: '',
  tags: [] as string[],
})

const form = ref(defaultForm())
const errors = ref<Record<string, string>>({})

const dateOfBirth = ref<Date | null>(null)
const idIssuedOn = ref<Date | null>(null)
const idExpiresOn = ref<Date | null>(null)
const passportIssuedOn = ref<Date | null>(null)
const passportExpiresOn = ref<Date | null>(null)
const workPermitIssuedOn = ref<Date | null>(null)
const workPermitExpiresOn = ref<Date | null>(null)
let duplicateCheckTimer: ReturnType<typeof setTimeout> | null = null
let duplicateCheckSequence = 0

function toDate(value: string | null | undefined): Date | null {
  return value ? new Date(value) : null
}

function toIso(value: Date | null): string | null {
  return value ? value.toISOString().slice(0, 10) : null
}

function formatDate(value: string | null): string {
  if (!value) return 'Không rõ ngày sinh'
  const [year, month, day] = value.split('-')
  if (!year || !month || !day) return value
  return `${day}/${month}/${year}`
}

function resetDuplicateWarnings() {
  duplicateCheckResult.value = { exact_matches: [], possible_matches: [] }
  checkingDuplicates.value = false
  duplicateCheckSequence += 1
  if (duplicateCheckTimer) {
    clearTimeout(duplicateCheckTimer)
    duplicateCheckTimer = null
  }
}

function resetForm() {
  form.value = defaultForm()
  errors.value = {}
  apiError.value = ''
  resetDuplicateWarnings()
  dateOfBirth.value = null
  idIssuedOn.value = null
  idExpiresOn.value = null
  passportIssuedOn.value = null
  passportExpiresOn.value = null
  workPermitIssuedOn.value = null
  workPermitExpiresOn.value = null
}

watch(visible, (isVisible) => {
  if (!isVisible) return
  if (!props.editing) {
    resetForm()
    return
  }

  const candidate = props.editing
  form.value = {
    full_name: candidate.full_name,
    last_name: candidate.last_name ?? '',
    first_name: candidate.first_name ?? '',
    gender: candidate.gender ?? null,
    nationality_id: candidate.nationality_id ?? null,
    raw_nationality_text: candidate.raw_nationality_text ?? '',
    ethnicity_id: candidate.ethnicity_id ?? null,
    religion_id: candidate.religion_id ?? null,
    id_number: candidate.id_number ?? '',
    id_issued_by: candidate.id_issued_by ?? '',
    passport_number: candidate.passport_number ?? '',
    work_permit_number: candidate.work_permit_number ?? '',
    phone_number: candidate.phone_number ?? '',
    personal_email: candidate.personal_email ?? '',
    personal_tax_code: candidate.personal_tax_code ?? '',
    bhxh_code: candidate.bhxh_code ?? '',
    address: candidate.address ?? '',
    current_company: candidate.current_company ?? '',
    current_position: candidate.current_position ?? '',
    expected_salary: candidate.expected_salary ?? null,
    source_channel_id: candidate.source_channel_id ?? null,
    source_note: candidate.source_note ?? '',
    internal_note: candidate.internal_note ?? '',
    tags: [...(candidate.tags ?? [])],
  }
  dateOfBirth.value = toDate(candidate.date_of_birth)
  idIssuedOn.value = toDate(candidate.id_issued_on)
  idExpiresOn.value = toDate(candidate.id_expires_on)
  passportIssuedOn.value = toDate(candidate.passport_issued_on)
  passportExpiresOn.value = toDate(candidate.passport_expires_on)
  workPermitIssuedOn.value = toDate(candidate.work_permit_issued_on)
  workPermitExpiresOn.value = toDate(candidate.work_permit_expires_on)
})

function buildDuplicateCheckPayload(): CandidateDuplicateCheck | null {
  const payload: CandidateDuplicateCheck = {
    full_name: form.value.full_name.trim() || null,
    date_of_birth: toIso(dateOfBirth.value),
    id_number: form.value.id_number.trim() || null,
    passport_number: form.value.passport_number.trim() || null,
    phone_number: form.value.phone_number.trim() || null,
    personal_email: form.value.personal_email.trim() || null,
    exclude_candidate_id: props.editing?.id ?? null,
  }

  const hasStrongIdentity =
    !!payload.id_number ||
    !!payload.passport_number ||
    !!payload.phone_number ||
    !!payload.personal_email

  if (!payload.full_name && !hasStrongIdentity) return null
  if (payload.full_name && payload.full_name.length < 2 && !hasStrongIdentity) return null
  return payload
}

async function runDuplicateCheck(payload: CandidateDuplicateCheck) {
  const requestId = ++duplicateCheckSequence
  checkingDuplicates.value = true
  try {
    const response = await recruitmentService.checkCandidateDuplicates(payload)
    if (requestId !== duplicateCheckSequence) return
    duplicateCheckResult.value = response.data
  } catch {
    if (requestId !== duplicateCheckSequence) return
    duplicateCheckResult.value = { exact_matches: [], possible_matches: [] }
  } finally {
    if (requestId === duplicateCheckSequence) checkingDuplicates.value = false
  }
}

function scheduleDuplicateCheck() {
  if (!visible.value) return
  const payload = buildDuplicateCheckPayload()
  if (!payload) {
    resetDuplicateWarnings()
    return
  }

  if (duplicateCheckTimer) clearTimeout(duplicateCheckTimer)
  duplicateCheckTimer = setTimeout(() => {
    duplicateCheckTimer = null
    void runDuplicateCheck(payload)
  }, 350)
}

function openCandidateDetail(candidateId: number) {
  const resolved = router.resolve({ name: 'candidate-detail', params: { id: candidateId } })
  window.open(resolved.href, '_blank', 'noopener')
}

watch(
  () => [
    visible.value,
    props.editing?.id ?? null,
    form.value.full_name,
    form.value.id_number,
    form.value.passport_number,
    form.value.phone_number,
    form.value.personal_email,
    toIso(dateOfBirth.value),
  ],
  ([isVisible]) => {
    if (!isVisible) {
      resetDuplicateWarnings()
      return
    }
    scheduleDuplicateCheck()
  },
)

function validate() {
  errors.value = {}
  if (!form.value.full_name.trim()) {
    errors.value.full_name = 'Họ và tên không được để trống'
  }
  if (
    !props.editing &&
    !form.value.personal_email.trim() &&
    !form.value.phone_number.trim() &&
    !form.value.id_number.trim() &&
    !form.value.passport_number.trim()
  ) {
    errors.value.identity_anchor = 'Cần nhập ít nhất một thông tin định danh để kiểm tra trùng'
  }
  return Object.keys(errors.value).length === 0
}

async function submit() {
  if (!validate()) return

  saving.value = true
  apiError.value = ''
  try {
    const payload = {
      ...form.value,
      last_name: form.value.last_name || null,
      first_name: form.value.first_name || null,
      raw_nationality_text: form.value.raw_nationality_text || null,
      id_number: form.value.id_number || null,
      id_issued_by: form.value.id_issued_by || null,
      passport_number: form.value.passport_number || null,
      work_permit_number: form.value.work_permit_number || null,
      phone_number: form.value.phone_number || null,
      personal_email: form.value.personal_email || null,
      personal_tax_code: form.value.personal_tax_code || null,
      bhxh_code: form.value.bhxh_code || null,
      address: form.value.address || null,
      current_company: form.value.current_company || null,
      current_position: form.value.current_position || null,
      source_note: form.value.source_note || null,
      internal_note: form.value.internal_note || null,
      date_of_birth: toIso(dateOfBirth.value),
      id_issued_on: toIso(idIssuedOn.value),
      id_expires_on: toIso(idExpiresOn.value),
      passport_issued_on: toIso(passportIssuedOn.value),
      passport_expires_on: toIso(passportExpiresOn.value),
      work_permit_issued_on: toIso(workPermitIssuedOn.value),
      work_permit_expires_on: toIso(workPermitExpiresOn.value),
    }

    if (props.editing) {
      await recruitmentService.updateCandidate(props.editing.id, payload)
      toast.add({ severity: 'success', summary: 'Đã cập nhật ứng viên', life: 3000 })
    } else {
      await recruitmentService.createCandidate(payload)
      toast.add({ severity: 'success', summary: 'Đã thêm ứng viên', life: 3000 })
    }

    visible.value = false
    emit('saved')
  } catch (error: unknown) {
    const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
    if (typeof detail === 'string') {
      apiError.value = detail
    } else if (Array.isArray(detail) && detail.length) {
      const first = detail[0] as { msg?: string }
      apiError.value = typeof first?.msg === 'string' ? first.msg : 'Lỗi lưu ứng viên'
    } else {
      apiError.value = 'Lỗi lưu ứng viên'
    }
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    const response = await recruitmentService.listChannels()
    channels.value = (response.data as RecruitmentChannelRead[]).filter((item) => item.is_active)
  } catch {}
})

onBeforeUnmount(() => {
  resetDuplicateWarnings()
})
</script>
