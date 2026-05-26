import api from './api'

// ── Types ─────────────────────────────────────────────────────────────────────

export type GenderType = 'male' | 'female' | 'other'
export type StatusType = 'probation' | 'official' | 'long_leave' | 'resigned'
export type AddressType = 'permanent' | 'contact'

export interface EmployeeListItem {
  id: number
  employee_seq: number
  display_code: string
  full_name: string
  date_of_birth: string
  gender: GenderType
  nationality_id: number
  ethnicity_id: number | null
  id_number: string
  phone_number: string | null
  personal_email: string | null
  status: StatusType
  start_date: string
  resigned_date: string | null
  is_active: boolean
  created_at: string
  updated_at: string | null
  id_expires_on: string | null
  passport_expires_on: string | null
  work_permit_expires_on: string | null
}

export interface EmployeeListPage {
  items: EmployeeListItem[]
  total: number
  page: number
  page_size: number
}

export interface EmployeeAddressRead {
  id: number
  employee_id: number
  address_type: AddressType
  new_province_unit_id: number | null
  new_district_unit_id: number | null
  new_ward_unit_id: number | null
  new_address_line: string | null
  old_province_unit_id: number | null
  old_district_unit_id: number | null
  old_ward_unit_id: number | null
  old_address_line: string | null
  full_address_text: string | null
  created_at: string
  updated_at: string | null
  // Enriched unit names
  old_province_name: string | null
  old_district_name: string | null
  old_ward_name: string | null
  new_province_name: string | null
  new_ward_name: string | null
}

export interface EmployeeBankAccountRead {
  id: number
  employee_id: number
  bank_id: number
  account_number: string
  account_name: string
  branch_name: string | null
  is_primary: boolean
  is_active: boolean
  note: string | null
  created_at: string
  updated_at: string | null
}

// ── Job Records (3.2) ─────────────────────────────────────────────────────────

export interface DepartmentBrief {
  id: number
  code: string
  name: string
  display_prefix: string | null
}

export interface JobTitleBrief {
  id: number
  code: string
  name: string
}

export interface JobPositionBrief {
  id: number
  code: string
  name: string
}

export interface JobRecordRead {
  id: number
  employee_id: number
  department_id: number
  department: DepartmentBrief
  job_title_id: number | null
  job_title: JobTitleBrief | null
  job_position_id: number | null
  job_position: JobPositionBrief | null
  probation_start_date: string | null
  probation_end_date: string | null
  official_date: string | null
  effective_from: string
  effective_to: string | null
  is_current: boolean
  notes: string | null
  changed_by: number | null
  created_at: string
  updated_at: string | null
}

export interface JobRecordCreate {
  department_id: number
  job_title_id?: number | null
  job_position_id?: number | null
  probation_start_date?: string | null
  probation_end_date?: string | null
  official_date?: string | null
  effective_from: string
  notes?: string | null
}

export interface JobRecordUpdate {
  department_id?: number | null
  job_title_id?: number | null
  job_position_id?: number | null
  probation_start_date?: string | null
  probation_end_date?: string | null
  official_date?: string | null
  notes?: string | null
}

export interface JobRecordTransfer {
  department_id: number
  job_title_id?: number | null
  job_position_id?: number | null
  effective_from: string
  notes?: string | null
}

// ─────────────────────────────────────────────────────────────────────────────

// ── Relatives (3.3) ──────────────────────────────────────────────────────────

export type RelationshipType =
  'vo' | 'chong' | 'cha' | 'me' | 'con' | 'anh' | 'chi' | 'em' | 'khac'

export const RELATIONSHIP_LABELS: Record<RelationshipType, string> = {
  vo: 'Vợ', chong: 'Chồng', cha: 'Cha', me: 'Mẹ', con: 'Con',
  anh: 'Anh', chi: 'Chị', em: 'Em', khac: 'Khác',
}

export interface EmployeeRelativeRead {
  id: number
  employee_id: number
  full_name: string
  relationship_type: RelationshipType
  date_of_birth: string | null
  occupation: string | null
  phone_number: string | null
  is_emergency_contact: boolean
  note: string | null
  created_at: string
  updated_at: string | null
}

export interface RelativeCreate {
  full_name: string
  relationship_type: RelationshipType
  date_of_birth?: string | null
  occupation?: string | null
  phone_number?: string | null
  is_emergency_contact?: boolean
  note?: string | null
}

export interface RelativeUpdate {
  full_name?: string
  relationship_type?: RelationshipType
  date_of_birth?: string | null
  occupation?: string | null
  phone_number?: string | null
  is_emergency_contact?: boolean
  note?: string | null
}

// ─────────────────────────────────────────────────────────────────────────────

export interface EmployeeRead extends EmployeeListItem {
  last_name: string
  first_name: string
  religion_id: number | null
  id_issued_on: string
  id_issued_by: string
  id_expires_on: string | null
  passport_number: string | null
  passport_issued_on: string | null
  passport_expires_on: string | null
  work_permit_number: string | null
  work_permit_issued_on: string | null
  work_permit_expires_on: string | null
  personal_tax_code: string | null
  bhxh_code: string | null
  avatar_path: string | null
  user_id: number | null
  addresses: EmployeeAddressRead[]
  bank_accounts: EmployeeBankAccountRead[]
  current_job: JobRecordRead | null
  relatives: EmployeeRelativeRead[]
}

export interface EmployeeLookupItem {
  id: number
  employee_seq: number
  display_code: string
  full_name: string
  status: StatusType
}

export interface EmployeeCreate {
  employee_seq?: number | null
  employee_code_sequence_id?: number | null
  full_name: string
  last_name: string
  first_name: string
  date_of_birth: string
  gender: GenderType
  nationality_id: number
  ethnicity_id?: number | null
  religion_id?: number | null
  id_number: string
  id_issued_on: string
  id_issued_by: string
  id_expires_on?: string | null
  passport_number?: string | null
  passport_issued_on?: string | null
  passport_expires_on?: string | null
  work_permit_number?: string | null
  work_permit_issued_on?: string | null
  work_permit_expires_on?: string | null
  phone_number?: string | null
  personal_email?: string | null
  personal_tax_code?: string | null
  bhxh_code?: string | null
  status?: StatusType
  start_date: string
  resigned_date?: string | null
  initial_department_id?: number | null
  initial_job_title_id?: number | null
  initial_job_position_id?: number | null
  initial_job_effective_from?: string | null
  initial_probation_start_date?: string | null
  initial_probation_end_date?: string | null
  initial_official_date?: string | null
  initial_job_notes?: string | null
}

export interface EmployeeUpdate {
  full_name?: string
  last_name?: string
  first_name?: string
  date_of_birth?: string
  gender?: GenderType
  nationality_id?: number
  ethnicity_id?: number | null
  religion_id?: number | null
  id_number?: string
  id_issued_on?: string
  id_issued_by?: string
  id_expires_on?: string | null
  passport_number?: string | null
  passport_issued_on?: string | null
  passport_expires_on?: string | null
  work_permit_number?: string | null
  work_permit_issued_on?: string | null
  work_permit_expires_on?: string | null
  phone_number?: string | null
  personal_email?: string | null
  personal_tax_code?: string | null
  bhxh_code?: string | null
  status?: StatusType
  start_date?: string
  resigned_date?: string | null
  is_active?: boolean
}

export interface EmployeeAddressWrite {
  address_type: AddressType
  new_province_unit_id?: number | null
  new_district_unit_id?: number | null
  new_ward_unit_id?: number | null
  new_address_line?: string | null
  old_province_unit_id?: number | null
  old_district_unit_id?: number | null
  old_ward_unit_id?: number | null
  old_address_line?: string | null
  full_address_text?: string | null
}

export interface EmployeeBankAccountWrite {
  bank_id: number
  account_number: string
  account_name: string
  branch_name?: string | null
  is_primary?: boolean
  note?: string | null
}

// ── Education & Experience (3.4) ─────────────────────────────────────────────

export type SkillProficiencyLevel = 'beginner' | 'intermediate' | 'advanced' | 'expert'
export type LanguageProficiencyLevel = 'native' | 'A1' | 'A2' | 'B1' | 'B2' | 'C1' | 'C2'

export const SKILL_PROFICIENCY_LABELS: Record<SkillProficiencyLevel, string> = {
  beginner: 'Cơ bản',
  intermediate: 'Trung bình',
  advanced: 'Khá',
  expert: 'Thành thạo',
}

export const LANGUAGE_PROFICIENCY_LABELS: Record<LanguageProficiencyLevel, string> = {
  native: 'Bản ngữ',
  A1: 'A1 — Sơ cấp',
  A2: 'A2 — Sơ cấp',
  B1: 'B1 — Trung cấp',
  B2: 'B2 — Trung cấp',
  C1: 'C1 — Cao cấp',
  C2: 'C2 — Thành thạo',
}

export const DIPLOMA_TYPE_OPTIONS = [
  'Chính quy', 'Liên thông', 'Vừa học vừa làm', 'Từ xa', 'Văn bằng 2',
]

export interface EducationHistoryRead {
  id: number
  employee_id: number
  institution_id: number | null
  institution_name: string | null
  major_id: number | null
  major_name: string | null
  education_level_id: number
  education_level_name: string
  graduation_year: number | null
  diploma_type: string | null
  is_main_education: boolean
  note: string | null
  created_at: string
  updated_at: string | null
}

export interface EducationHistoryCreate {
  institution_id: number
  major_id?: number | null
  education_level_id: number
  graduation_year?: number | null
  diploma_type?: string | null
  is_main_education?: boolean
  note?: string | null
}

export interface EducationHistoryUpdate {
  institution_id?: number | null
  major_id?: number | null
  education_level_id?: number | null
  graduation_year?: number | null
  diploma_type?: string | null
  is_main_education?: boolean | null
  note?: string | null
}

export interface WorkExperienceRead {
  id: number
  employee_id: number
  company_name: string
  position_name: string | null
  start_date: string
  end_date: string | null
  description: string | null
  created_at: string
  updated_at: string | null
}

export interface WorkExperienceCreate {
  company_name: string
  position_name?: string | null
  start_date: string
  end_date?: string | null
  description?: string | null
}

export type WorkExperienceUpdate = Partial<WorkExperienceCreate>

export interface EmployeeSkillRead {
  id: number
  employee_id: number
  skill_id: number
  skill_name: string
  skill_group: string | null
  proficiency_level: SkillProficiencyLevel
  note: string | null
  created_at: string
  updated_at: string | null
}

export interface EmployeeSkillCreate {
  skill_id: number
  proficiency_level: SkillProficiencyLevel
  note?: string | null
}

export interface EmployeeSkillUpdate {
  proficiency_level?: SkillProficiencyLevel
  note?: string | null
}

export interface EmployeeCertificateRead {
  id: number
  employee_id: number
  certificate_id: number
  certificate_name: string
  certificate_number: string | null
  issued_date: string | null
  expires_on: string | null
  issued_by: string | null
  note: string | null
  created_at: string
  updated_at: string | null
}

export interface EmployeeCertificateCreate {
  certificate_id: number
  certificate_number?: string | null
  issued_date?: string | null
  expires_on?: string | null
  issued_by?: string | null
  note?: string | null
}

export type EmployeeCertificateUpdate = Partial<Omit<EmployeeCertificateCreate, 'certificate_id'>>

export interface EmployeeLanguageRead {
  id: number
  employee_id: number
  language_name: string
  proficiency_level: LanguageProficiencyLevel
  note: string | null
  created_at: string
  updated_at: string | null
}

export interface EmployeeLanguageCreate {
  language_name: string
  proficiency_level: LanguageProficiencyLevel
  note?: string | null
}

export interface EmployeeLanguageUpdate {
  proficiency_level?: LanguageProficiencyLevel
  note?: string | null
}

// ── Import / Export (3.7) ─────────────────────────────────────────────────────

export interface ImportRowError {
  row:     number
  column:  string
  message: string
}

export interface ImportResult {
  total:       number
  success:     number
  failed:      number
  errors:      ImportRowError[]
  created_ids: number[]
}

// ── Attachments (3.5) ─────────────────────────────────────────────────────────
export const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  avatar:        'Ảnh thẻ',
  id_card_front: 'CCCD / CMND — Mặt trước',
  id_card_back:  'CCCD / CMND — Mặt sau',
  passport:      'Hộ chiếu',
  work_permit:   'Giấy phép lao động',
  degree:        'Bằng cấp / Văn bằng',
  certificate:   'Chứng chỉ',
  resume:        'CV / Sơ yếu lý lịch',
  other:         'Khác',
}

export const DOCUMENT_TYPE_OPTIONS = Object.entries(DOCUMENT_TYPE_LABELS).map(
  ([value, label]) => ({ value, label })
)

export const DOCUMENT_TYPE_GROUPS: { label: string; types: string[] }[] = [
  { label: 'Ảnh thẻ',              types: ['avatar'] },
  { label: 'CCCD / CMND',          types: ['id_card_front', 'id_card_back'] },
  { label: 'Hộ chiếu',             types: ['passport'] },
  { label: 'Giấy phép lao động',   types: ['work_permit'] },
  { label: 'Bằng cấp / Văn bằng', types: ['degree'] },
  { label: 'Chứng chỉ',            types: ['certificate'] },
  { label: 'CV / Sơ yếu lý lịch', types: ['resume'] },
  { label: 'Khác',                 types: ['other'] },
]

export interface EmployeeAttachmentRead {
  id:                  number
  employee_id:         number
  document_type:       string
  document_type_label: string
  description:         string | null
  file_name:           string
  file_path:           string
  file_size:           number | null
  mime_type:           string | null
  uploaded_at:         string
  download_url:        string
}

// ── Document Checklist (13.6) ─────────────────────────────────────────────────

export interface ChecklistItemRead {
  id: number
  document_type_id: number
  document_type_name: string
  document_type_code: string
  is_required: boolean
  has_expiry: boolean
  status: string   // not_submitted | submitted | expired | waived
  submitted_at: string | null
  expires_at: string | null
  days_until_expiry: number | null
  is_expiring_soon: boolean
  waived_reason: string | null
  has_file: boolean
  file_name: string | null
  note: string | null
  updated_at: string
}

export interface ChecklistItemUpdate {
  status?: string
  submitted_at?: string | null
  expires_at?: string | null
  note?: string | null
}

// ── Service ───────────────────────────────────────────────────────────────────

const BASE = '/employees'

async function downloadBlob(url: string, filename: string, params?: Record<string, unknown>) {
  const res = await api.get(url, { responseType: 'blob', params })
  const href = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = href
  a.download = filename
  a.click()
  URL.revokeObjectURL(href)
}

export default {
  list: (params?: {
    keyword?: string
    status?: string
    is_active?: boolean
    page?: number
    page_size?: number
  }) => api.get<EmployeeListPage>(BASE, { params }),

  get: (id: number) => api.get<EmployeeRead>(`${BASE}/${id}`),

  create: (data: EmployeeCreate) => api.post<EmployeeRead>(BASE, data),

  update: (id: number, data: EmployeeUpdate) => api.put<EmployeeRead>(`${BASE}/${id}`, data),

  deactivate: (id: number) => api.delete(`${BASE}/${id}`),

  lookup: (params?: { keyword?: string; limit?: number }) =>
    api.get<EmployeeLookupItem[]>(`${BASE}/lookup`, { params }),

  // Addresses
  getAddresses: (id: number) => api.get<EmployeeAddressRead[]>(`${BASE}/${id}/addresses`),

  upsertAddress: (id: number, data: EmployeeAddressWrite) =>
    api.put<EmployeeAddressRead>(`${BASE}/${id}/addresses`, data),

  // Bank accounts
  getBankAccounts: (id: number) =>
    api.get<EmployeeBankAccountRead[]>(`${BASE}/${id}/bank-accounts`),

  createBankAccount: (id: number, data: EmployeeBankAccountWrite) =>
    api.post<EmployeeBankAccountRead>(`${BASE}/${id}/bank-accounts`, data),

  updateBankAccount: (id: number, accountId: number, data: EmployeeBankAccountWrite) =>
    api.put<EmployeeBankAccountRead>(`${BASE}/${id}/bank-accounts/${accountId}`, data),

  deleteBankAccount: (id: number, accountId: number) =>
    api.delete(`${BASE}/${id}/bank-accounts/${accountId}`),

  // Job records (3.2)
  getJobRecords: (id: number) =>
    api.get<JobRecordRead[]>(`${BASE}/${id}/job-records`),

  createJobRecord: (id: number, data: JobRecordCreate) =>
    api.post<JobRecordRead>(`${BASE}/${id}/job-records`, data),

  updateCurrentJobRecord: (id: number, data: JobRecordUpdate) =>
    api.put<JobRecordRead>(`${BASE}/${id}/job-records/current`, data),

  transferJobRecord: (id: number, data: JobRecordTransfer) =>
    api.post<JobRecordRead>(`${BASE}/${id}/job-records/transfer`, data),

  // Relatives (3.3)
  getRelatives: (id: number) =>
    api.get<EmployeeRelativeRead[]>(`${BASE}/${id}/relatives`),

  createRelative: (id: number, data: RelativeCreate) =>
    api.post<EmployeeRelativeRead>(`${BASE}/${id}/relatives`, data),

  updateRelative: (id: number, relId: number, data: RelativeUpdate) =>
    api.put<EmployeeRelativeRead>(`${BASE}/${id}/relatives/${relId}`, data),

  deleteRelative: (id: number, relId: number) =>
    api.delete(`${BASE}/${id}/relatives/${relId}`),

  // Education histories (3.4)
  getEducationHistories: (id: number) =>
    api.get<EducationHistoryRead[]>(`${BASE}/${id}/education-histories`),

  createEducationHistory: (id: number, data: EducationHistoryCreate) =>
    api.post<EducationHistoryRead>(`${BASE}/${id}/education-histories`, data),

  updateEducationHistory: (id: number, eduId: number, data: EducationHistoryUpdate) =>
    api.put<EducationHistoryRead>(`${BASE}/${id}/education-histories/${eduId}`, data),

  deleteEducationHistory: (id: number, eduId: number) =>
    api.delete(`${BASE}/${id}/education-histories/${eduId}`),

  // Work experiences (3.4)
  getWorkExperiences: (id: number) =>
    api.get<WorkExperienceRead[]>(`${BASE}/${id}/work-experiences`),

  createWorkExperience: (id: number, data: WorkExperienceCreate) =>
    api.post<WorkExperienceRead>(`${BASE}/${id}/work-experiences`, data),

  updateWorkExperience: (id: number, expId: number, data: WorkExperienceUpdate) =>
    api.put<WorkExperienceRead>(`${BASE}/${id}/work-experiences/${expId}`, data),

  deleteWorkExperience: (id: number, expId: number) =>
    api.delete(`${BASE}/${id}/work-experiences/${expId}`),

  // Skills (3.4)
  getEmployeeSkills: (id: number) =>
    api.get<EmployeeSkillRead[]>(`${BASE}/${id}/skills`),

  createEmployeeSkill: (id: number, data: EmployeeSkillCreate) =>
    api.post<EmployeeSkillRead>(`${BASE}/${id}/skills`, data),

  updateEmployeeSkill: (id: number, skillRecordId: number, data: EmployeeSkillUpdate) =>
    api.put<EmployeeSkillRead>(`${BASE}/${id}/skills/${skillRecordId}`, data),

  deleteEmployeeSkill: (id: number, skillRecordId: number) =>
    api.delete(`${BASE}/${id}/skills/${skillRecordId}`),

  // Certificates (3.4)
  getEmployeeCertificates: (id: number) =>
    api.get<EmployeeCertificateRead[]>(`${BASE}/${id}/certificates`),

  createEmployeeCertificate: (id: number, data: EmployeeCertificateCreate) =>
    api.post<EmployeeCertificateRead>(`${BASE}/${id}/certificates`, data),

  updateEmployeeCertificate: (id: number, certId: number, data: EmployeeCertificateUpdate) =>
    api.put<EmployeeCertificateRead>(`${BASE}/${id}/certificates/${certId}`, data),

  deleteEmployeeCertificate: (id: number, certId: number) =>
    api.delete(`${BASE}/${id}/certificates/${certId}`),

  // Languages (3.4)
  getEmployeeLanguages: (id: number) =>
    api.get<EmployeeLanguageRead[]>(`${BASE}/${id}/languages`),

  createEmployeeLanguage: (id: number, data: EmployeeLanguageCreate) =>
    api.post<EmployeeLanguageRead>(`${BASE}/${id}/languages`, data),

  updateEmployeeLanguage: (id: number, langId: number, data: EmployeeLanguageUpdate) =>
    api.put<EmployeeLanguageRead>(`${BASE}/${id}/languages/${langId}`, data),

  deleteEmployeeLanguage: (id: number, langId: number) =>
    api.delete(`${BASE}/${id}/languages/${langId}`),

  // Attachments (3.5)
  getAttachments: (id: number, documentType?: string) =>
    api.get<EmployeeAttachmentRead[]>(`${BASE}/${id}/attachments`, {
      params: documentType ? { document_type: documentType } : undefined,
    }),

  uploadAttachment: (id: number, formData: FormData) =>
    api.post<EmployeeAttachmentRead>(`${BASE}/${id}/attachments`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  deleteAttachment: (id: number, attId: number) =>
    api.delete(`${BASE}/${id}/attachments/${attId}`),

  getAttachmentDownloadUrl: (id: number, attId: number) =>
    `${BASE}/${id}/attachments/${attId}/download`,

  // Import / Export (3.7)
  downloadImportTemplate: () =>
    downloadBlob(`${BASE}/import/template`, 'mau_import_nhan_vien.xlsx'),

  importEmployees: (formData: FormData) =>
    api.post<ImportResult>(`${BASE}/import`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  exportEmployees: (params?: { keyword?: string; status?: string; is_active?: boolean }) => {
    const today = new Date().toISOString().slice(0, 10).replace(/-/g, '')
    return downloadBlob(`${BASE}/export`, `danh_sach_nhan_vien_${today}.xlsx`, params as Record<string, unknown>)
  },

  exportEmployeeProfile: (id: number) =>
    downloadBlob(`${BASE}/${id}/export`, `ho_so_${id}.xlsx`),

  // Document Checklist (13.6)
  getDocumentChecklist: (id: number) =>
    api.get<ChecklistItemRead[]>(`${BASE}/${id}/document-checklist`),

  updateChecklistItem: (id: number, itemId: number, data: ChecklistItemUpdate) =>
    api.put<ChecklistItemRead>(`${BASE}/${id}/document-checklist/${itemId}`, data),

  uploadChecklistFile: (id: number, itemId: number, file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post<ChecklistItemRead>(`${BASE}/${id}/document-checklist/${itemId}/upload`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  downloadChecklistFile: (id: number, itemId: number, fileName: string) =>
    downloadBlob(`${BASE}/${id}/document-checklist/${itemId}/download`, fileName),

  deleteChecklistFile: (id: number, itemId: number) =>
    api.delete<ChecklistItemRead>(`${BASE}/${id}/document-checklist/${itemId}/file`),

  waiveChecklistItem: (id: number, itemId: number, reason: string) =>
    api.post<ChecklistItemRead>(`${BASE}/${id}/document-checklist/${itemId}/waive`, null, {
      params: { reason },
    }),

  initDocumentChecklist: (id: number) =>
    api.post<ChecklistItemRead[]>(`${BASE}/${id}/document-checklist/init`),

  addChecklistItem: (id: number, documentTypeId: number) =>
    api.post<ChecklistItemRead>(`${BASE}/${id}/document-checklist`, null, {
      params: { document_type_id: documentTypeId },
    }),
}
