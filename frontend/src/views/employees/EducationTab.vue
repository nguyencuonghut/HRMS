<template>
  <div class="section-stack">

    <!-- ══ 1. Học vấn ══════════════════════════════════════════════════════ -->
    <div class="section-card">
      <div class="section-header">
        <span class="section-title">Quá trình học vấn</span>
        <Button v-can:edit="'employees'" label="Thêm" icon="pi pi-plus" size="small" @click="openEduCreate" />
      </div>

      <div v-if="loading.edu" class="loading-state">
        <i class="pi pi-spin pi-spinner" /><span>Đang tải...</span>
      </div>
      <div v-else-if="!educations.length" class="empty-state">
        <i class="pi pi-book" /><span>Chưa có thông tin học vấn</span>
      </div>
      <DataTable v-else :value="educations" size="small" row-hover>
        <Column header="Trường / Cơ sở đào tạo">
          <template #body="{ data }">
            <span class="info-value">{{ data.institution_name || eduInstitutionName(data) }}</span>
            <Tag v-if="data.is_main_education" value="Bằng chính" severity="success" class="ml-2" style="font-size:0.7rem" />
          </template>
        </Column>
        <Column header="Chuyên ngành">
          <template #body="{ data }">{{ data.major_name || '—' }}</template>
        </Column>
        <Column header="Trình độ" style="width:110px">
          <template #body="{ data }">{{ data.education_level_name }}</template>
        </Column>
        <Column header="Năm TN" style="width:80px">
          <template #body="{ data }">{{ data.graduation_year ?? '—' }}</template>
        </Column>
        <Column header="Loại bằng" style="width:130px">
          <template #body="{ data }">{{ data.diploma_type ?? '—' }}</template>
        </Column>
        <Column header="" style="width:80px">
          <template #body="{ data }">
            <div class="action-cell">
              <Button v-can:edit="'employees'" icon="pi pi-pencil" severity="secondary" text rounded size="small" v-tooltip.top="'Sửa'" @click="openEduEdit(data)" />
              <Button v-can:edit="'employees'" icon="pi pi-trash" severity="danger" text rounded size="small" v-tooltip.top="'Xóa'" @click="confirmDeleteEdu(data)" />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- ══ 2. Kinh nghiệm làm việc ════════════════════════════════════════ -->
    <div class="section-card">
      <div class="section-header">
        <span class="section-title">Kinh nghiệm làm việc</span>
        <Button v-can:edit="'employees'" label="Thêm" icon="pi pi-plus" size="small" @click="openExpCreate" />
      </div>

      <div v-if="loading.exp" class="loading-state">
        <i class="pi pi-spin pi-spinner" /><span>Đang tải...</span>
      </div>
      <div v-else-if="!experiences.length" class="empty-state">
        <i class="pi pi-briefcase" /><span>Chưa có kinh nghiệm làm việc</span>
      </div>
      <DataTable v-else :value="experiences" size="small" row-hover>
        <Column header="Công ty">
          <template #body="{ data }">
            <span class="info-value">{{ data.company_name }}</span>
          </template>
        </Column>
        <Column header="Vị trí">
          <template #body="{ data }">{{ data.position_name ?? '—' }}</template>
        </Column>
        <Column header="Từ" style="width:110px">
          <template #body="{ data }">{{ formatDate(data.start_date) }}</template>
        </Column>
        <Column header="Đến" style="width:110px">
          <template #body="{ data }">{{ data.end_date ? formatDate(data.end_date) : 'Hiện tại' }}</template>
        </Column>
        <Column header="" style="width:80px">
          <template #body="{ data }">
            <div class="action-cell">
              <Button v-can:edit="'employees'" icon="pi pi-pencil" severity="secondary" text rounded size="small" v-tooltip.top="'Sửa'" @click="openExpEdit(data)" />
              <Button v-can:edit="'employees'" icon="pi pi-trash" severity="danger" text rounded size="small" v-tooltip.top="'Xóa'" @click="confirmDeleteExp(data)" />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- ══ 3. Kỹ năng ════════════════════════════════════════════════════ -->
    <div class="section-card">
      <div class="section-header">
        <span class="section-title">Kỹ năng</span>
        <Button v-can:edit="'employees'" label="Thêm" icon="pi pi-plus" size="small" @click="openSkillCreate" />
      </div>

      <div v-if="loading.skill" class="loading-state">
        <i class="pi pi-spin pi-spinner" /><span>Đang tải...</span>
      </div>
      <div v-else-if="!skills.length" class="empty-state">
        <i class="pi pi-star" /><span>Chưa có kỹ năng</span>
      </div>
      <div v-else class="chip-list">
        <div v-for="sk in skills" :key="sk.id" class="chip-item">
          <span class="chip-label">{{ sk.skill_name }}</span>
          <span class="chip-level">[{{ skillLevelLabel(sk.proficiency_level) }}]</span>
          <div class="chip-actions">
            <Button v-can:edit="'employees'" icon="pi pi-pencil" severity="secondary" text rounded size="small" v-tooltip.top="'Sửa'" @click="openSkillEdit(sk)" />
            <Button v-can:edit="'employees'" icon="pi pi-times" severity="danger" text rounded size="small" v-tooltip.top="'Xóa'" @click="confirmDeleteSkill(sk)" />
          </div>
        </div>
      </div>
    </div>

    <!-- ══ 4. Chứng chỉ ══════════════════════════════════════════════════ -->
    <div class="section-card">
      <div class="section-header">
        <span class="section-title">Chứng chỉ</span>
        <Button v-can:edit="'employees'" label="Thêm" icon="pi pi-plus" size="small" @click="openCertCreate" />
      </div>

      <div v-if="loading.cert" class="loading-state">
        <i class="pi pi-spin pi-spinner" /><span>Đang tải...</span>
      </div>
      <div v-else-if="!certificates.length" class="empty-state">
        <i class="pi pi-verified" /><span>Chưa có chứng chỉ</span>
      </div>
      <DataTable v-else :value="certificates" size="small" row-hover>
        <Column header="Chứng chỉ">
          <template #body="{ data }">
            <span class="info-value">{{ data.certificate_name }}</span>
          </template>
        </Column>
        <Column header="Số văn bằng" style="width:140px">
          <template #body="{ data }">{{ data.certificate_number ?? '—' }}</template>
        </Column>
        <Column header="Ngày cấp" style="width:110px">
          <template #body="{ data }">{{ data.issued_date ? formatDate(data.issued_date) : '—' }}</template>
        </Column>
        <Column header="Hết hạn" style="width:110px">
          <template #body="{ data }">
            <span :class="isCertExpired(data.expires_on) ? 'cert-expired' : ''">
              {{ data.expires_on ? formatDate(data.expires_on) : 'Không hạn' }}
            </span>
          </template>
        </Column>
        <Column header="" style="width:80px">
          <template #body="{ data }">
            <div class="action-cell">
              <Button v-can:edit="'employees'" icon="pi pi-pencil" severity="secondary" text rounded size="small" v-tooltip.top="'Sửa'" @click="openCertEdit(data)" />
              <Button v-can:edit="'employees'" icon="pi pi-trash" severity="danger" text rounded size="small" v-tooltip.top="'Xóa'" @click="confirmDeleteCert(data)" />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- ══ 5. Ngoại ngữ ══════════════════════════════════════════════════ -->
    <div class="section-card">
      <div class="section-header">
        <span class="section-title">Ngoại ngữ</span>
        <Button v-can:edit="'employees'" label="Thêm" icon="pi pi-plus" size="small" @click="openLangCreate" />
      </div>

      <div v-if="loading.lang" class="loading-state">
        <i class="pi pi-spin pi-spinner" /><span>Đang tải...</span>
      </div>
      <div v-else-if="!languages.length" class="empty-state">
        <i class="pi pi-globe" /><span>Chưa có ngoại ngữ</span>
      </div>
      <div v-else class="chip-list">
        <div v-for="lang in languages" :key="lang.id" class="chip-item">
          <span class="chip-label">{{ lang.language_name }}</span>
          <span class="chip-level">[{{ langLevelLabel(lang.proficiency_level) }}]</span>
          <div class="chip-actions">
            <Button v-can:edit="'employees'" icon="pi pi-pencil" severity="secondary" text rounded size="small" v-tooltip.top="'Sửa'" @click="openLangEdit(lang)" />
            <Button v-can:edit="'employees'" icon="pi pi-times" severity="danger" text rounded size="small" v-tooltip.top="'Xóa'" @click="confirmDeleteLang(lang)" />
          </div>
        </div>
      </div>
    </div>

    <!-- ══ Dialog: Học vấn ══════════════════════════════════════════════ -->
    <Dialog v-model:visible="eduDialog.visible"
      :header="eduDialog.id ? 'Cập nhật học vấn' : 'Thêm học vấn'"
      :style="{ width: '520px' }" modal :closable="!submitting">
      <div class="form-grid no-top-pad">
        <div class="field col-full">
          <label>Trường / Cơ sở đào tạo <span class="req">*</span></label>
          <AutoComplete
            v-model="selectedInstitution"
            :suggestions="institutionSuggestions"
            option-label="name"
            dropdown
            force-selection
            placeholder="Tìm kiếm trường học..."
            class="w-full"
            :invalid="!!eduErrors.institution"
            @complete="searchInstitutions"
          >
            <template #option="{ option }">
              <div>
                <div>{{ option.name }}</div>
                <small class="muted-text">{{ option.short_name || option.code || '' }}</small>
              </div>
            </template>
          </AutoComplete>
          <small v-if="eduErrors.institution" class="error-msg">{{ eduErrors.institution }}</small>
        </div>
        <div class="field col-full">
          <label>Chuyên ngành</label>
          <AutoComplete
            v-model="selectedMajor"
            :suggestions="majorSuggestions"
            option-label="name"
            dropdown
            force-selection
            placeholder="Tìm kiếm chuyên ngành..."
            class="w-full"
            @complete="searchMajors"
          >
            <template #option="{ option }">
              <div>
                <div>{{ option.name }}</div>
                <small class="muted-text">{{ option.major_group || option.code || '' }}</small>
              </div>
            </template>
          </AutoComplete>
        </div>
        <div class="field">
          <label>Trình độ <span class="req">*</span></label>
          <Select v-model="eduForm.education_level_id"
            :options="educationLevelOptions" option-label="label" option-value="value"
            class="w-full" :invalid="!!eduErrors.education_level_id" />
          <small v-if="eduErrors.education_level_id" class="error-msg">{{ eduErrors.education_level_id }}</small>
        </div>
        <div class="field">
          <label>Năm tốt nghiệp</label>
          <InputNumber v-model="eduForm.graduation_year" class="w-full" :use-grouping="false" placeholder="VD: 2015" />
        </div>
        <div class="field col-full">
          <label>Loại bằng</label>
          <Select v-model="eduForm.diploma_type"
            :options="diplomaTypeOptions" class="w-full"
            :show-clear="true" placeholder="Chọn loại bằng" />
        </div>
        <div class="field col-full">
          <div class="switch-row">
            <ToggleSwitch v-model="eduForm.is_main_education" />
            <label>Đây là bằng cấp chính (dùng cho hồ sơ)</label>
          </div>
        </div>
        <div class="field col-full">
          <label>Ghi chú</label>
          <Textarea v-model="eduForm.note" class="w-full" rows="2" auto-resize />
        </div>
      </div>
      <template #footer>
        <Button label="Hủy" severity="secondary" outlined :disabled="submitting" @click="eduDialog.visible = false" />
        <Button v-can:edit="'employees'" :label="eduDialog.id ? 'Lưu thay đổi' : 'Thêm'" icon="pi pi-check" :loading="submitting" @click="submitEdu" />
      </template>
    </Dialog>

    <!-- ══ Dialog: Kinh nghiệm ══════════════════════════════════════════ -->
    <Dialog v-model:visible="expDialog.visible"
      :header="expDialog.id ? 'Cập nhật kinh nghiệm' : 'Thêm kinh nghiệm'"
      :style="{ width: '480px' }" modal :closable="!submitting">
      <div class="form-grid no-top-pad">
        <div class="field col-full">
          <label>Tên công ty <span class="req">*</span></label>
          <InputText v-model="expForm.company_name" class="w-full" :invalid="!!expErrors.company_name" />
          <small v-if="expErrors.company_name" class="error-msg">{{ expErrors.company_name }}</small>
        </div>
        <div class="field col-full">
          <label>Chức vụ / Vị trí</label>
          <InputText v-model="expForm.position_name" class="w-full" />
        </div>
        <div class="field">
          <label>Từ ngày <span class="req">*</span></label>
          <DatePicker v-model="expForm.start_date_d" class="w-full" dateFormat="dd/mm/yy" :invalid="!!expErrors.start_date" />
          <small v-if="expErrors.start_date" class="error-msg">{{ expErrors.start_date }}</small>
        </div>
        <div class="field">
          <label>Đến ngày <span class="muted-text">(để trống = hiện tại)</span></label>
          <DatePicker v-model="expForm.end_date_d" class="w-full" dateFormat="dd/mm/yy" :show-clear="true" />
        </div>
        <div class="field col-full">
          <label>Mô tả công việc</label>
          <Textarea v-model="expForm.description" class="w-full" rows="3" auto-resize />
        </div>
      </div>
      <template #footer>
        <Button label="Hủy" severity="secondary" outlined :disabled="submitting" @click="expDialog.visible = false" />
        <Button v-can:edit="'employees'" :label="expDialog.id ? 'Lưu thay đổi' : 'Thêm'" icon="pi pi-check" :loading="submitting" @click="submitExp" />
      </template>
    </Dialog>

    <!-- ══ Dialog: Kỹ năng ══════════════════════════════════════════════ -->
    <Dialog v-model:visible="skillDialog.visible"
      :header="skillDialog.id ? 'Cập nhật kỹ năng' : 'Thêm kỹ năng'"
      :style="{ width: '400px' }" modal :closable="!submitting">
      <div class="form-grid no-top-pad">
        <div v-if="!skillDialog.id" class="field col-full">
          <label>Kỹ năng <span class="req">*</span></label>
          <Select v-model="skillForm.skill_id"
            :options="skillOptions" option-label="label" option-value="value"
            class="w-full" filter :invalid="!!skillErrors.skill_id" placeholder="Chọn kỹ năng" />
          <small v-if="skillErrors.skill_id" class="error-msg">{{ skillErrors.skill_id }}</small>
        </div>
        <div class="field col-full">
          <label>Mức độ thành thạo <span class="req">*</span></label>
          <Select v-model="skillForm.proficiency_level"
            :options="skillProficiencyOptions" option-label="label" option-value="value"
            class="w-full" :invalid="!!skillErrors.proficiency_level" />
          <small v-if="skillErrors.proficiency_level" class="error-msg">{{ skillErrors.proficiency_level }}</small>
        </div>
        <div class="field col-full">
          <label>Ghi chú</label>
          <Textarea v-model="skillForm.note" class="w-full" rows="2" auto-resize />
        </div>
      </div>
      <template #footer>
        <Button label="Hủy" severity="secondary" outlined :disabled="submitting" @click="skillDialog.visible = false" />
        <Button v-can:edit="'employees'" :label="skillDialog.id ? 'Lưu thay đổi' : 'Thêm'" icon="pi pi-check" :loading="submitting" @click="submitSkill" />
      </template>
    </Dialog>

    <!-- ══ Dialog: Chứng chỉ ════════════════════════════════════════════ -->
    <Dialog v-model:visible="certDialog.visible"
      :header="certDialog.id ? 'Cập nhật chứng chỉ' : 'Thêm chứng chỉ'"
      :style="{ width: '480px' }" modal :closable="!submitting">
      <div class="form-grid no-top-pad">
        <div v-if="!certDialog.id" class="field col-full">
          <label>Chứng chỉ <span class="req">*</span></label>
          <Select v-model="certForm.certificate_id"
            :options="certOptions" option-label="label" option-value="value"
            class="w-full" filter :invalid="!!certErrors.certificate_id" placeholder="Chọn chứng chỉ" />
          <small v-if="certErrors.certificate_id" class="error-msg">{{ certErrors.certificate_id }}</small>
        </div>
        <div class="field col-full">
          <label>Số văn bằng / Mã chứng chỉ</label>
          <InputText v-model="certForm.certificate_number" class="w-full" />
        </div>
        <div class="field">
          <label>Ngày cấp</label>
          <DatePicker v-model="certForm.issued_date_d" class="w-full" dateFormat="dd/mm/yy" :show-clear="true" />
        </div>
        <div class="field">
          <label>Ngày hết hạn</label>
          <DatePicker v-model="certForm.expires_on_d" class="w-full" dateFormat="dd/mm/yy" :show-clear="true" />
        </div>
        <div class="field col-full">
          <label>Nơi cấp</label>
          <InputText v-model="certForm.issued_by" class="w-full" />
        </div>
        <div class="field col-full">
          <label>Ghi chú</label>
          <Textarea v-model="certForm.note" class="w-full" rows="2" auto-resize />
        </div>
      </div>
      <template #footer>
        <Button label="Hủy" severity="secondary" outlined :disabled="submitting" @click="certDialog.visible = false" />
        <Button v-can:edit="'employees'" :label="certDialog.id ? 'Lưu thay đổi' : 'Thêm'" icon="pi pi-check" :loading="submitting" @click="submitCert" />
      </template>
    </Dialog>

    <!-- ══ Dialog: Ngoại ngữ ════════════════════════════════════════════ -->
    <Dialog v-model:visible="langDialog.visible"
      :header="langDialog.id ? 'Cập nhật ngoại ngữ' : 'Thêm ngoại ngữ'"
      :style="{ width: '400px' }" modal :closable="!submitting">
      <div class="form-grid no-top-pad">
        <div class="field col-full">
          <label>Ngoại ngữ <span class="req">*</span></label>
          <InputText v-model="langForm.language_name" class="w-full"
            placeholder="VD: Tiếng Anh, Tiếng Trung..."
            :invalid="!!langErrors.language_name" :disabled="!!langDialog.id" />
          <small v-if="langErrors.language_name" class="error-msg">{{ langErrors.language_name }}</small>
        </div>
        <div class="field col-full">
          <label>Mức độ thành thạo <span class="req">*</span></label>
          <Select v-model="langForm.proficiency_level"
            :options="langProficiencyOptions" option-label="label" option-value="value"
            class="w-full" :invalid="!!langErrors.proficiency_level" />
          <small v-if="langErrors.proficiency_level" class="error-msg">{{ langErrors.proficiency_level }}</small>
        </div>
        <div class="field col-full">
          <label>Ghi chú</label>
          <Textarea v-model="langForm.note" class="w-full" rows="2" auto-resize />
        </div>
      </div>
      <template #footer>
        <Button label="Hủy" severity="secondary" outlined :disabled="submitting" @click="langDialog.visible = false" />
        <Button v-can:edit="'employees'" :label="langDialog.id ? 'Lưu thay đổi' : 'Thêm'" icon="pi pi-check" :loading="submitting" @click="submitLang" />
      </template>
    </Dialog>

  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import AutoComplete from 'primevue/autocomplete'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import ToggleSwitch from 'primevue/toggleswitch'

import educationCatalogService, {
  type EducationalInstitutionRead,
  type EducationMajorRead,
} from '@/services/educationCatalogService'
import otherBusinessCatalogService from '@/services/otherBusinessCatalogService'
import employeeService, {
  type EducationHistoryRead,
  type EducationHistoryCreate,
  type WorkExperienceRead,
  type EmployeeSkillRead,
  type EmployeeCertificateRead,
  type EmployeeLanguageRead,
  type SkillProficiencyLevel,
  type LanguageProficiencyLevel,
  SKILL_PROFICIENCY_LABELS,
  LANGUAGE_PROFICIENCY_LABELS,
  DIPLOMA_TYPE_OPTIONS,
} from '@/services/employeeService'

const props = defineProps<{ employeeId: number }>()
const emit  = defineEmits<{ (e: 'refresh'): void }>()

const toast   = useToast()
const confirm = useConfirm()

// ── State ──────────────────────────────────────────────────────────────────────
const loading = reactive({ edu: false, exp: false, skill: false, cert: false, lang: false })
const submitting = ref(false)

const educations   = ref<EducationHistoryRead[]>([])
const experiences  = ref<WorkExperienceRead[]>([])
const skills       = ref<EmployeeSkillRead[]>([])
const certificates = ref<EmployeeCertificateRead[]>([])
const languages    = ref<EmployeeLanguageRead[]>([])

// ── Catalog options ────────────────────────────────────────────────────────────
const educationLevelOptions = ref<{ value: number; label: string }[]>([])
const skillOptions  = ref<{ value: number; label: string }[]>([])
const certOptions   = ref<{ value: number; label: string }[]>([])
const diplomaTypeOptions = DIPLOMA_TYPE_OPTIONS

const skillProficiencyOptions = Object.entries(SKILL_PROFICIENCY_LABELS).map(([value, label]) => ({ value, label }))
const langProficiencyOptions  = Object.entries(LANGUAGE_PROFICIENCY_LABELS).map(([value, label]) => ({ value, label }))

// ── Helpers ────────────────────────────────────────────────────────────────────
function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('vi-VN')
}

function toIso(d: Date | null | undefined): string | null {
  if (!d) return null
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function fromIso(iso: string | null | undefined): Date | null {
  return iso ? new Date(iso) : null
}

function isCertExpired(expires_on: string | null): boolean {
  if (!expires_on) return false
  return new Date(expires_on) < new Date()
}

function skillLevelLabel(level: SkillProficiencyLevel): string {
  return SKILL_PROFICIENCY_LABELS[level] ?? level
}

function langLevelLabel(level: LanguageProficiencyLevel): string {
  return LANGUAGE_PROFICIENCY_LABELS[level] ?? level
}

function eduInstitutionName(data: EducationHistoryRead): string {
  return data.institution_name ?? '—'
}

function apiError(e: unknown): string {
  const err = e as { response?: { data?: { detail?: unknown } } }
  const detail = err.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((d: { msg: string }) => d.msg).join('; ')
  return typeof detail === 'string' ? detail : 'Đã xảy ra lỗi'
}

// ── Load all sections ──────────────────────────────────────────────────────────
async function loadAll() {
  await Promise.all([loadEdu(), loadExp(), loadSkills(), loadCerts(), loadLangs()])
}

async function loadEdu() {
  loading.edu = true
  try { educations.value = (await employeeService.getEducationHistories(props.employeeId)).data }
  catch (e) { toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 }) }
  finally { loading.edu = false }
}

async function loadExp() {
  loading.exp = true
  try { experiences.value = (await employeeService.getWorkExperiences(props.employeeId)).data }
  catch (e) { toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 }) }
  finally { loading.exp = false }
}

async function loadSkills() {
  loading.skill = true
  try { skills.value = (await employeeService.getEmployeeSkills(props.employeeId)).data }
  catch (e) { toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 }) }
  finally { loading.skill = false }
}

async function loadCerts() {
  loading.cert = true
  try { certificates.value = (await employeeService.getEmployeeCertificates(props.employeeId)).data }
  catch (e) { toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 }) }
  finally { loading.cert = false }
}

async function loadLangs() {
  loading.lang = true
  try { languages.value = (await employeeService.getEmployeeLanguages(props.employeeId)).data }
  catch (e) { toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 }) }
  finally { loading.lang = false }
}

async function loadCatalogs() {
  try {
    const [levelsResp, skillsResp, certsResp] = await Promise.all([
      educationCatalogService.lookupEducationLevels({ limit: 100 }),
      otherBusinessCatalogService.lookupSkills(),
      otherBusinessCatalogService.lookupCertificates(),
    ])
    educationLevelOptions.value = levelsResp.data.map((l: { id: number; name: string; rank_no: number }) => ({
      value: l.id,
      label: `${l.rank_no}. ${l.name}`,
    }))
    skillOptions.value  = skillsResp.data.map((s: { id: number; name: string }) => ({ value: s.id, label: s.name }))
    certOptions.value   = certsResp.data.map((c: { id: number; name: string }) => ({ value: c.id, label: c.name }))
  } catch { /* silently ignore catalog load error */ }
}

onMounted(() => { loadAll(); loadCatalogs() })
watch(() => props.employeeId, loadAll)

// ── Education dialog ───────────────────────────────────────────────────────────
const eduDialog = reactive({ visible: false, id: null as number | null })
const eduErrors = ref<Record<string, string>>({})
const eduForm = ref({
  education_level_id: null as number | null,
  graduation_year: null as number | null,
  diploma_type: null as string | null,
  is_main_education: false,
  note: '',
})

const selectedInstitution = ref<EducationalInstitutionRead | null>(null)
const selectedMajor = ref<EducationMajorRead | null>(null)
const institutionSuggestions = ref<EducationalInstitutionRead[]>([])
const majorSuggestions = ref<EducationMajorRead[]>([])

async function searchInstitutions(event: { query: string }) {
  const res = await educationCatalogService.lookupEducationalInstitutions({ keyword: event.query || null, limit: 20 })
  institutionSuggestions.value = res.data
}

async function searchMajors(event: { query: string }) {
  const res = await educationCatalogService.lookupEducationMajors({ keyword: event.query || null, limit: 20 })
  majorSuggestions.value = res.data
}

function resetEduForm() {
  eduForm.value = {
    education_level_id: null,
    graduation_year: null,
    diploma_type: null, is_main_education: false, note: '',
  }
  selectedInstitution.value = null
  selectedMajor.value = null
  eduErrors.value = {}
}

function openEduCreate() {
  eduDialog.id = null
  resetEduForm()
  eduDialog.visible = true
}

function openEduEdit(edu: EducationHistoryRead) {
  eduDialog.id = edu.id
  eduErrors.value = {}
  eduForm.value = {
    education_level_id: edu.education_level_id,
    graduation_year: edu.graduation_year,
    diploma_type: edu.diploma_type,
    is_main_education: edu.is_main_education,
    note: edu.note ?? '',
  }
  selectedInstitution.value = edu.institution_id
    ? { id: edu.institution_id, name: edu.institution_name ?? '' } as EducationalInstitutionRead
    : null
  selectedMajor.value = edu.major_id
    ? { id: edu.major_id, name: edu.major_name ?? '' } as EducationMajorRead
    : null
  eduDialog.visible = true
}

function validateEdu(): boolean {
  eduErrors.value = {}
  if (!selectedInstitution.value) eduErrors.value.institution = 'Chọn trường từ danh mục'
  if (!eduForm.value.education_level_id) eduErrors.value.education_level_id = 'Chọn trình độ'
  return Object.keys(eduErrors.value).length === 0
}

async function submitEdu() {
  if (!validateEdu()) return
  submitting.value = true
  try {
    const payload: EducationHistoryCreate = {
      institution_id: selectedInstitution.value!.id,
      major_id: selectedMajor.value?.id ?? null,
      education_level_id: eduForm.value.education_level_id!,
      graduation_year: eduForm.value.graduation_year,
      diploma_type: eduForm.value.diploma_type,
      is_main_education: eduForm.value.is_main_education,
      note: eduForm.value.note?.trim() || null,
    }
    if (eduDialog.id) {
      await employeeService.updateEducationHistory(props.employeeId, eduDialog.id, payload)
      toast.add({ severity: 'success', summary: 'Đã lưu', detail: 'Cập nhật học vấn thành công', life: 3000 })
    } else {
      await employeeService.createEducationHistory(props.employeeId, payload)
      toast.add({ severity: 'success', summary: 'Đã thêm', detail: 'Thêm học vấn thành công', life: 3000 })
    }
    eduDialog.visible = false
    await loadEdu()
    emit('refresh')
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
  } finally { submitting.value = false }
}

function confirmDeleteEdu(edu: EducationHistoryRead) {
  confirm.require({
    message: `Xóa học vấn "${edu.institution_name || edu.education_level_name}"?`,
    header: 'Xác nhận xóa', icon: 'pi pi-exclamation-triangle',
    rejectLabel: 'Hủy', acceptLabel: 'Xóa',
    accept: async () => {
      try {
        await employeeService.deleteEducationHistory(props.employeeId, edu.id)
        toast.add({ severity: 'success', summary: 'Đã xóa', life: 3000 })
        await loadEdu(); emit('refresh')
      } catch (e) { toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 }) }
    },
  })
}

// ── Work experience dialog ─────────────────────────────────────────────────────
const expDialog = reactive({ visible: false, id: null as number | null })
const expErrors = ref<Record<string, string>>({})
const expForm = ref({
  company_name: '',
  position_name: '',
  start_date_d: null as Date | null,
  end_date_d: null as Date | null,
  description: '',
})

function resetExpForm() {
  expForm.value = { company_name: '', position_name: '', start_date_d: null, end_date_d: null, description: '' }
  expErrors.value = {}
}

function openExpCreate() { expDialog.id = null; resetExpForm(); expDialog.visible = true }

function openExpEdit(exp: WorkExperienceRead) {
  expDialog.id = exp.id
  expErrors.value = {}
  expForm.value = {
    company_name: exp.company_name,
    position_name: exp.position_name ?? '',
    start_date_d: fromIso(exp.start_date),
    end_date_d: fromIso(exp.end_date),
    description: exp.description ?? '',
  }
  expDialog.visible = true
}

function validateExp(): boolean {
  expErrors.value = {}
  if (!expForm.value.company_name?.trim()) expErrors.value.company_name = 'Nhập tên công ty'
  if (!expForm.value.start_date_d) expErrors.value.start_date = 'Chọn ngày bắt đầu'
  return Object.keys(expErrors.value).length === 0
}

async function submitExp() {
  if (!validateExp()) return
  submitting.value = true
  try {
    const payload = {
      company_name: expForm.value.company_name.trim(),
      position_name: expForm.value.position_name?.trim() || null,
      start_date: toIso(expForm.value.start_date_d)!,
      end_date: toIso(expForm.value.end_date_d),
      description: expForm.value.description?.trim() || null,
    }
    if (expDialog.id) {
      await employeeService.updateWorkExperience(props.employeeId, expDialog.id, payload)
      toast.add({ severity: 'success', summary: 'Đã lưu', detail: 'Cập nhật kinh nghiệm thành công', life: 3000 })
    } else {
      await employeeService.createWorkExperience(props.employeeId, payload)
      toast.add({ severity: 'success', summary: 'Đã thêm', detail: 'Thêm kinh nghiệm thành công', life: 3000 })
    }
    expDialog.visible = false
    await loadExp(); emit('refresh')
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
  } finally { submitting.value = false }
}

function confirmDeleteExp(exp: WorkExperienceRead) {
  confirm.require({
    message: `Xóa kinh nghiệm tại "${exp.company_name}"?`,
    header: 'Xác nhận xóa', icon: 'pi pi-exclamation-triangle',
    rejectLabel: 'Hủy', acceptLabel: 'Xóa',
    accept: async () => {
      try {
        await employeeService.deleteWorkExperience(props.employeeId, exp.id)
        toast.add({ severity: 'success', summary: 'Đã xóa', life: 3000 })
        await loadExp(); emit('refresh')
      } catch (e) { toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 }) }
    },
  })
}

// ── Skill dialog ───────────────────────────────────────────────────────────────
const skillDialog = reactive({ visible: false, id: null as number | null })
const skillErrors = ref<Record<string, string>>({})
const skillForm = ref({
  skill_id: null as number | null,
  proficiency_level: null as SkillProficiencyLevel | null,
  note: '',
})

function openSkillCreate() {
  skillDialog.id = null
  skillForm.value = { skill_id: null, proficiency_level: null, note: '' }
  skillErrors.value = {}
  skillDialog.visible = true
}

function openSkillEdit(sk: EmployeeSkillRead) {
  skillDialog.id = sk.id
  skillErrors.value = {}
  skillForm.value = { skill_id: sk.skill_id, proficiency_level: sk.proficiency_level, note: sk.note ?? '' }
  skillDialog.visible = true
}

function validateSkill(): boolean {
  skillErrors.value = {}
  if (!skillDialog.id && !skillForm.value.skill_id) skillErrors.value.skill_id = 'Chọn kỹ năng'
  if (!skillForm.value.proficiency_level) skillErrors.value.proficiency_level = 'Chọn mức độ thành thạo'
  return Object.keys(skillErrors.value).length === 0
}

async function submitSkill() {
  if (!validateSkill()) return
  submitting.value = true
  try {
    if (skillDialog.id) {
      await employeeService.updateEmployeeSkill(props.employeeId, skillDialog.id, {
        proficiency_level: skillForm.value.proficiency_level!,
        note: skillForm.value.note?.trim() || null,
      })
      toast.add({ severity: 'success', summary: 'Đã lưu', detail: 'Cập nhật kỹ năng thành công', life: 3000 })
    } else {
      await employeeService.createEmployeeSkill(props.employeeId, {
        skill_id: skillForm.value.skill_id!,
        proficiency_level: skillForm.value.proficiency_level!,
        note: skillForm.value.note?.trim() || null,
      })
      toast.add({ severity: 'success', summary: 'Đã thêm', detail: 'Thêm kỹ năng thành công', life: 3000 })
    }
    skillDialog.visible = false
    await loadSkills(); emit('refresh')
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
  } finally { submitting.value = false }
}

function confirmDeleteSkill(sk: EmployeeSkillRead) {
  confirm.require({
    message: `Xóa kỹ năng "${sk.skill_name}"?`,
    header: 'Xác nhận xóa', icon: 'pi pi-exclamation-triangle',
    rejectLabel: 'Hủy', acceptLabel: 'Xóa',
    accept: async () => {
      try {
        await employeeService.deleteEmployeeSkill(props.employeeId, sk.id)
        toast.add({ severity: 'success', summary: 'Đã xóa', life: 3000 })
        await loadSkills(); emit('refresh')
      } catch (e) { toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 }) }
    },
  })
}

// ── Certificate dialog ─────────────────────────────────────────────────────────
const certDialog = reactive({ visible: false, id: null as number | null })
const certErrors = ref<Record<string, string>>({})
const certForm = ref({
  certificate_id: null as number | null,
  certificate_number: '',
  issued_date_d: null as Date | null,
  expires_on_d: null as Date | null,
  issued_by: '',
  note: '',
})

function openCertCreate() {
  certDialog.id = null
  certForm.value = { certificate_id: null, certificate_number: '', issued_date_d: null, expires_on_d: null, issued_by: '', note: '' }
  certErrors.value = {}
  certDialog.visible = true
}

function openCertEdit(cert: EmployeeCertificateRead) {
  certDialog.id = cert.id
  certErrors.value = {}
  certForm.value = {
    certificate_id: cert.certificate_id,
    certificate_number: cert.certificate_number ?? '',
    issued_date_d: fromIso(cert.issued_date),
    expires_on_d: fromIso(cert.expires_on),
    issued_by: cert.issued_by ?? '',
    note: cert.note ?? '',
  }
  certDialog.visible = true
}

function validateCert(): boolean {
  certErrors.value = {}
  if (!certDialog.id && !certForm.value.certificate_id) certErrors.value.certificate_id = 'Chọn chứng chỉ'
  return Object.keys(certErrors.value).length === 0
}

async function submitCert() {
  if (!validateCert()) return
  submitting.value = true
  try {
    if (certDialog.id) {
      await employeeService.updateEmployeeCertificate(props.employeeId, certDialog.id, {
        certificate_number: certForm.value.certificate_number?.trim() || null,
        issued_date: toIso(certForm.value.issued_date_d),
        expires_on: toIso(certForm.value.expires_on_d),
        issued_by: certForm.value.issued_by?.trim() || null,
        note: certForm.value.note?.trim() || null,
      })
      toast.add({ severity: 'success', summary: 'Đã lưu', detail: 'Cập nhật chứng chỉ thành công', life: 3000 })
    } else {
      await employeeService.createEmployeeCertificate(props.employeeId, {
        certificate_id: certForm.value.certificate_id!,
        certificate_number: certForm.value.certificate_number?.trim() || null,
        issued_date: toIso(certForm.value.issued_date_d),
        expires_on: toIso(certForm.value.expires_on_d),
        issued_by: certForm.value.issued_by?.trim() || null,
        note: certForm.value.note?.trim() || null,
      })
      toast.add({ severity: 'success', summary: 'Đã thêm', detail: 'Thêm chứng chỉ thành công', life: 3000 })
    }
    certDialog.visible = false
    await loadCerts(); emit('refresh')
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
  } finally { submitting.value = false }
}

function confirmDeleteCert(cert: EmployeeCertificateRead) {
  confirm.require({
    message: `Xóa chứng chỉ "${cert.certificate_name}"?`,
    header: 'Xác nhận xóa', icon: 'pi pi-exclamation-triangle',
    rejectLabel: 'Hủy', acceptLabel: 'Xóa',
    accept: async () => {
      try {
        await employeeService.deleteEmployeeCertificate(props.employeeId, cert.id)
        toast.add({ severity: 'success', summary: 'Đã xóa', life: 3000 })
        await loadCerts(); emit('refresh')
      } catch (e) { toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 }) }
    },
  })
}

// ── Language dialog ────────────────────────────────────────────────────────────
const langDialog = reactive({ visible: false, id: null as number | null })
const langErrors = ref<Record<string, string>>({})
const langForm = ref({
  language_name: '',
  proficiency_level: null as LanguageProficiencyLevel | null,
  note: '',
})

function openLangCreate() {
  langDialog.id = null
  langForm.value = { language_name: '', proficiency_level: null, note: '' }
  langErrors.value = {}
  langDialog.visible = true
}

function openLangEdit(lang: EmployeeLanguageRead) {
  langDialog.id = lang.id
  langErrors.value = {}
  langForm.value = { language_name: lang.language_name, proficiency_level: lang.proficiency_level, note: lang.note ?? '' }
  langDialog.visible = true
}

function validateLang(): boolean {
  langErrors.value = {}
  if (!langForm.value.language_name?.trim()) langErrors.value.language_name = 'Nhập tên ngoại ngữ'
  if (!langForm.value.proficiency_level) langErrors.value.proficiency_level = 'Chọn mức độ'
  return Object.keys(langErrors.value).length === 0
}

async function submitLang() {
  if (!validateLang()) return
  submitting.value = true
  try {
    if (langDialog.id) {
      await employeeService.updateEmployeeLanguage(props.employeeId, langDialog.id, {
        proficiency_level: langForm.value.proficiency_level!,
        note: langForm.value.note?.trim() || null,
      })
      toast.add({ severity: 'success', summary: 'Đã lưu', detail: 'Cập nhật ngoại ngữ thành công', life: 3000 })
    } else {
      await employeeService.createEmployeeLanguage(props.employeeId, {
        language_name: langForm.value.language_name.trim(),
        proficiency_level: langForm.value.proficiency_level!,
        note: langForm.value.note?.trim() || null,
      })
      toast.add({ severity: 'success', summary: 'Đã thêm', detail: 'Thêm ngoại ngữ thành công', life: 3000 })
    }
    langDialog.visible = false
    await loadLangs(); emit('refresh')
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
  } finally { submitting.value = false }
}

function confirmDeleteLang(lang: EmployeeLanguageRead) {
  confirm.require({
    message: `Xóa ngoại ngữ "${lang.language_name}"?`,
    header: 'Xác nhận xóa', icon: 'pi pi-exclamation-triangle',
    rejectLabel: 'Hủy', acceptLabel: 'Xóa',
    accept: async () => {
      try {
        await employeeService.deleteEmployeeLanguage(props.employeeId, lang.id)
        toast.add({ severity: 'success', summary: 'Đã xóa', life: 3000 })
        await loadLangs(); emit('refresh')
      } catch (e) { toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 }) }
    },
  })
}
</script>
