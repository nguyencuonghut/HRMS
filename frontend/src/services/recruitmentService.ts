import api from './api'

// ── Headcount Plan ────────────────────────────────────────────────────────────

export interface HeadcountPlanRead {
  id: number
  year: number
  department_id: number | null
  department_name: string | null
  job_position_id: number | null
  job_position_name: string | null
  current_count: number
  planned_count: number
  reason: string | null
  created_by_id: number | null
  created_by_name: string | null
  created_at: string
  updated_at: string
}

export interface HeadcountPlanCreate {
  year: number
  department_id?: number | null
  job_position_id?: number | null
  current_count?: number
  planned_count: number
  reason?: string | null
}

export interface HeadcountPlanUpdate {
  current_count?: number
  planned_count?: number
  reason?: string | null
}

export interface HeadcountPlanListPage {
  items: HeadcountPlanRead[]
  total: number
  page: number
  page_size: number
}

// ── Job Requisition ───────────────────────────────────────────────────────────

export interface JobRequisitionListItem {
  id: number
  code: string
  job_position_name: string
  department_name: string
  quantity: number
  quantity_remaining: number
  reason_type: string
  reason_type_label: string
  deadline: string | null
  status: string
  status_label: string
  created_at: string
}

export interface JobRequisitionRead {
  id: number
  code: string
  job_position_id: number
  job_position_name: string
  department_id: number
  department_name: string
  headcount_plan_id: number | null
  quantity: number
  quantity_remaining: number
  reason_type: string
  reason_type_label: string
  deadline: string | null
  salary_min: string | null
  salary_max: string | null
  effective_description: string | null
  effective_requirements: string | null
  status: string
  status_label: string
  submitted_at: string | null
  submitted_by_name: string | null
  approved_by_id: number | null
  approved_by_name: string | null
  approved_at: string | null
  rejection_note: string | null
  internal_note: string | null
  created_by_id: number
  created_by_name: string | null
  created_at: string
  updated_at: string
}

export interface JobRequisitionCreate {
  job_position_id: number
  department_id: number
  headcount_plan_id?: number | null
  quantity?: number
  reason_type: string
  deadline?: string | null
  salary_min?: number | null
  salary_max?: number | null
  jd_description?: string | null
  jd_requirements?: string | null
  internal_note?: string | null
}

export interface JobRequisitionUpdate {
  department_id?: number
  headcount_plan_id?: number | null
  quantity?: number
  reason_type?: string
  deadline?: string | null
  salary_min?: number | null
  salary_max?: number | null
  jd_description?: string | null
  jd_requirements?: string | null
  internal_note?: string | null
}

export interface JobRequisitionListPage {
  items: JobRequisitionListItem[]
  total: number
  page: number
  page_size: number
}

// ── Budget ────────────────────────────────────────────────────────────────────

export interface BudgetItemRead {
  id: number
  job_requisition_id: number
  item_name: string
  estimated_amount: string | null
  actual_amount: string | null
  note: string | null
  created_by_id: number | null
  created_at: string
}

export interface BudgetItemCreate {
  item_name: string
  estimated_amount?: number | null
  actual_amount?: number | null
  note?: string | null
}

export interface BudgetItemUpdate {
  item_name?: string
  estimated_amount?: number | null
  actual_amount?: number | null
  note?: string | null
}

export interface BudgetSummary {
  items: BudgetItemRead[]
  total_estimated: string
  total_actual: string
}

// ── Recruitment Channel ───────────────────────────────────────────────────────

export interface RecruitmentChannelRead {
  id: number
  code: string
  name: string
  is_active: boolean
  sort_order: number
}

// ── Job Posting ───────────────────────────────────────────────────────────────

export interface JobPostingRead {
  id: number
  job_requisition_id: number
  job_requisition_code: string
  job_position_name: string
  department_name: string
  title: string
  description: string
  requirements: string | null
  benefits: string | null
  work_location: string | null
  deadline: string | null
  salary_display: string | null
  posting_type: string
  posting_type_label: string
  channels: RecruitmentChannelRead[]
  status: string
  status_label: string
  opened_at: string | null
  closed_at: string | null
  candidate_count: number
  note: string | null
  created_by_name: string | null
  created_at: string
  updated_at: string
}

export interface JobPostingCreate {
  job_requisition_id: number
  title: string
  description: string
  requirements?: string | null
  benefits?: string | null
  work_location?: string | null
  deadline?: string | null
  salary_display?: string | null
  posting_type?: 'internal' | 'external'
  channels?: number[]
  note?: string | null
}

export interface JobPostingUpdate {
  title?: string
  description?: string
  requirements?: string | null
  benefits?: string | null
  work_location?: string | null
  deadline?: string | null
  salary_display?: string | null
  posting_type?: 'internal' | 'external'
  channels?: number[]
  note?: string | null
}

export interface JobPostingListPage {
  items: JobPostingRead[]
  total: number
  page: number
  page_size: number
}

// ── Service ───────────────────────────────────────────────────────────────────

export default {
  // Headcount Plans
  listPlans: (params?: Record<string, unknown>) =>
    api.get<HeadcountPlanListPage>('/recruitment/headcount-plans', { params }),

  createPlan: (data: HeadcountPlanCreate) =>
    api.post<HeadcountPlanRead>('/recruitment/headcount-plans', data),

  updatePlan: (id: number, data: HeadcountPlanUpdate) =>
    api.put<HeadcountPlanRead>(`/recruitment/headcount-plans/${id}`, data),

  deletePlan: (id: number) =>
    api.delete(`/recruitment/headcount-plans/${id}`),

  getFulfillmentRate: (year: number, department_id?: number | null) =>
    api.get<{ year: number; total_planned: number; completed_jr: number; fulfillment_rate: number }>(
      '/recruitment/headcount-plans/fulfillment',
      { params: { year, department_id: department_id ?? undefined } },
    ),

  // Job Requisitions
  listJR: (params?: Record<string, unknown>) =>
    api.get<JobRequisitionListPage>('/recruitment/job-requisitions', { params }),

  getJR: (id: number) =>
    api.get<JobRequisitionRead>(`/recruitment/job-requisitions/${id}`),

  createJR: (data: JobRequisitionCreate) =>
    api.post<JobRequisitionRead>('/recruitment/job-requisitions', data),

  updateJR: (id: number, data: JobRequisitionUpdate) =>
    api.put<JobRequisitionRead>(`/recruitment/job-requisitions/${id}`, data),

  deleteJR: (id: number) =>
    api.delete(`/recruitment/job-requisitions/${id}`),

  submitJR: (id: number) =>
    api.post<JobRequisitionRead>(`/recruitment/job-requisitions/${id}/submit`),

  approveJR: (id: number) =>
    api.post<JobRequisitionRead>(`/recruitment/job-requisitions/${id}/approve`),

  rejectJR: (id: number, rejection_note: string) =>
    api.post<JobRequisitionRead>(`/recruitment/job-requisitions/${id}/reject`, { rejection_note }),

  cancelJR: (id: number, reason?: string) =>
    api.post<JobRequisitionRead>(`/recruitment/job-requisitions/${id}/cancel`, { reason }),

  // Budget
  getBudget: (jr_id: number) =>
    api.get<BudgetSummary>(`/recruitment/job-requisitions/${jr_id}/budget`),

  addBudgetItem: (jr_id: number, data: BudgetItemCreate) =>
    api.post<BudgetItemRead>(`/recruitment/job-requisitions/${jr_id}/budget`, data),

  updateBudgetItem: (jr_id: number, item_id: number, data: BudgetItemUpdate) =>
    api.put<BudgetItemRead>(`/recruitment/job-requisitions/${jr_id}/budget/${item_id}`, data),

  deleteBudgetItem: (jr_id: number, item_id: number) =>
    api.delete(`/recruitment/job-requisitions/${jr_id}/budget/${item_id}`),

  // Channels
  listChannels: () =>
    api.get<RecruitmentChannelRead[]>('/recruitment/channels'),

  createChannel: (data: { code: string; name: string; sort_order?: number }) =>
    api.post<RecruitmentChannelRead>('/recruitment/channels', data),

  updateChannel: (id: number, data: { name?: string; is_active?: boolean; sort_order?: number }) =>
    api.put<RecruitmentChannelRead>(`/recruitment/channels/${id}`, data),

  deleteChannel: (id: number) =>
    api.delete(`/recruitment/channels/${id}`),

  // Job Postings
  listPostings: (params?: Record<string, unknown>) =>
    api.get<JobPostingListPage>('/recruitment/job-postings', { params }),

  getPosting: (id: number) =>
    api.get<JobPostingRead>(`/recruitment/job-postings/${id}`),

  createPosting: (data: JobPostingCreate) =>
    api.post<JobPostingRead>('/recruitment/job-postings', data),

  updatePosting: (id: number, data: JobPostingUpdate) =>
    api.put<JobPostingRead>(`/recruitment/job-postings/${id}`, data),

  publishPosting: (id: number) =>
    api.post<JobPostingRead>(`/recruitment/job-postings/${id}/publish`),

  closePosting: (id: number) =>
    api.post<JobPostingRead>(`/recruitment/job-postings/${id}/close`),

  reopenPosting: (id: number) =>
    api.post<JobPostingRead>(`/recruitment/job-postings/${id}/reopen`),

  validateLanguage: (text: string) =>
    api.post<{ warnings: string[] }>('/recruitment/job-postings/validate-language', { text }),

  // ── Candidates (13.3) ──────────────────────────────────────────────────────

  listCandidates: (params?: Record<string, unknown>) =>
    api.get<CandidateListPage>('/recruitment/candidates', { params }),

  getCandidate: (id: number) =>
    api.get<CandidateRead>(`/recruitment/candidates/${id}`),

  checkCandidateDuplicates: (data: CandidateDuplicateCheck) =>
    api.post<CandidateDuplicateCheckResult>('/recruitment/candidates/check-duplicates', data),

  createCandidate: (data: CandidateCreate) =>
    api.post<CandidateRead>('/recruitment/candidates', data),

  updateCandidate: (id: number, data: CandidateUpdate) =>
    api.put<CandidateRead>(`/recruitment/candidates/${id}`, data),

  deleteCandidate: (id: number) =>
    api.delete(`/recruitment/candidates/${id}`),

  addEducation: (candidateId: number, data: CandidateEducationCreate) =>
    api.post<CandidateEducationRead>(`/recruitment/candidates/${candidateId}/educations`, data),

  updateEducation: (candidateId: number, eduId: number, data: CandidateEducationCreate) =>
    api.put<CandidateEducationRead>(`/recruitment/candidates/${candidateId}/educations/${eduId}`, data),

  deleteEducation: (candidateId: number, eduId: number) =>
    api.delete(`/recruitment/candidates/${candidateId}/educations/${eduId}`),

  addWorkExperience: (candidateId: number, data: CandidateWorkExpCreate) =>
    api.post<CandidateWorkExpRead>(`/recruitment/candidates/${candidateId}/work-experiences`, data),

  updateWorkExperience: (candidateId: number, expId: number, data: CandidateWorkExpCreate) =>
    api.put<CandidateWorkExpRead>(`/recruitment/candidates/${candidateId}/work-experiences/${expId}`, data),

  deleteWorkExperience: (candidateId: number, expId: number) =>
    api.delete(`/recruitment/candidates/${candidateId}/work-experiences/${expId}`),

  addSkill: (candidateId: number, data: { skill_name: string; proficiency_level?: string }) =>
    api.post<CandidateSkillRead>(`/recruitment/candidates/${candidateId}/skills`, data),

  deleteSkill: (candidateId: number, skillId: number) =>
    api.delete(`/recruitment/candidates/${candidateId}/skills/${skillId}`),

  uploadAttachment: (candidateId: number, formData: FormData) =>
    api.post<CandidateAttachmentRead>(`/recruitment/candidates/${candidateId}/attachments`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  deleteAttachment: (candidateId: number, attId: number) =>
    api.delete(`/recruitment/candidates/${candidateId}/attachments/${attId}`),

  getAttachmentDownloadUrl: (candidateId: number, attId: number) =>
    `/api/v1/recruitment/candidates/${candidateId}/attachments/${attId}/download`,

  applyCandidate: (candidateId: number, data: ApplicationCreate) =>
    api.post<ApplicationRead>(`/recruitment/candidates/${candidateId}/apply`, data),

  listApplications: (jrId: number, params?: Record<string, unknown>) =>
    api.get<ApplicationListPage>(
      `/recruitment/job-requisitions/${jrId}/applications`, { params }
    ),

  listCandidateApplications: (candidateId: number, params?: Record<string, unknown>) =>
    api.get<ApplicationListPage>(`/recruitment/candidates/${candidateId}/applications`, { params }),

  downloadImportTemplate: () =>
    api.get('/recruitment/candidates/import-template', { responseType: 'blob' }),

  importCandidates: (formData: FormData) =>
    api.post<ImportResult>('/recruitment/candidates/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
}

// ── Candidate interfaces ──────────────────────────────────────────────────────

export interface CandidateEducationRead {
  id: number
  candidate_id: number
  education_level_id: number | null
  education_level_name: string | null
  institution_name: string | null
  major_name: string | null
  graduation_year: number | null
  is_main: boolean
  note: string | null
}

export interface CandidateEducationCreate {
  education_level_id?: number | null
  institution_name?: string | null
  major_name?: string | null
  graduation_year?: number | null
  is_main?: boolean
  note?: string | null
}

export interface CandidateWorkExpRead {
  id: number
  candidate_id: number
  company_name: string
  position_name: string | null
  start_date: string | null
  end_date: string | null
  description: string | null
  sort_order: number
}

export interface CandidateWorkExpCreate {
  company_name: string
  position_name?: string | null
  start_date?: string | null
  end_date?: string | null
  description?: string | null
  sort_order?: number
}

export interface CandidateSkillRead {
  id: number
  candidate_id: number
  skill_name: string
  proficiency_level: string | null
}

export interface CandidateAttachmentRead {
  id: number
  candidate_id: number
  attachment_type: string
  attachment_type_label: string
  file_name: string
  file_size: number | null
  mime_type: string | null
  note: string | null
  uploaded_at: string
  download_url: string
}

export interface CandidateRead {
  id: number
  full_name: string
  last_name: string | null
  first_name: string | null
  date_of_birth: string | null
  gender: string | null
  gender_label: string | null
  nationality_id: number | null
  nationality_name: string | null
  raw_nationality_text: string | null
  ethnicity_id: number | null
  ethnicity_name: string | null
  religion_id: number | null
  religion_name: string | null
  id_number: string | null
  id_issued_on: string | null
  id_issued_by: string | null
  id_expires_on: string | null
  passport_number: string | null
  passport_issued_on: string | null
  passport_expires_on: string | null
  work_permit_number: string | null
  work_permit_issued_on: string | null
  work_permit_expires_on: string | null
  phone_number: string | null
  personal_email: string | null
  personal_tax_code: string | null
  bhxh_code: string | null
  address: string | null
  current_company: string | null
  current_position: string | null
  expected_salary: number | null
  source_channel_id: number | null
  source_channel_name: string | null
  source_note: string | null
  internal_note: string | null
  tags: string[]
  is_active: boolean
  educations: CandidateEducationRead[]
  work_experiences: CandidateWorkExpRead[]
  skills: CandidateSkillRead[]
  attachments: CandidateAttachmentRead[]
  active_applications: number
  identity_strength: 'weak' | 'medium' | 'strong'
  identity_strength_label: string
  conversion_ready: boolean
  conversion_missing_fields: string[]
  created_by_name: string | null
  created_at: string
  updated_at: string
}

export interface CandidateListItem {
  id: number
  full_name: string
  phone_number: string | null
  personal_email: string | null
  current_position: string | null
  current_company: string | null
  nationality_name: string | null
  source_channel_name: string | null
  active_applications: number
  identity_strength: 'weak' | 'medium' | 'strong'
  identity_strength_label: string
  created_at: string
}

export interface CandidateListPage {
  items: CandidateListItem[]
  total: number
  page: number
  page_size: number
}

export interface CandidateDuplicateCheck {
  full_name?: string | null
  date_of_birth?: string | null
  id_number?: string | null
  passport_number?: string | null
  phone_number?: string | null
  personal_email?: string | null
  exclude_candidate_id?: number | null
}

export interface CandidateDuplicateMatch {
  candidate_id: number
  full_name: string
  date_of_birth: string | null
  id_number: string | null
  passport_number: string | null
  phone_number: string | null
  personal_email: string | null
  current_company: string | null
  current_position: string | null
  match_level: 'exact' | 'possible'
  reason_codes: string[]
  reason_labels: string[]
}

export interface CandidateDuplicateCheckResult {
  exact_matches: CandidateDuplicateMatch[]
  possible_matches: CandidateDuplicateMatch[]
}

export interface CandidateCreate {
  full_name: string
  last_name?: string | null
  first_name?: string | null
  date_of_birth?: string | null
  gender?: string | null
  nationality_id?: number | null
  raw_nationality_text?: string | null
  ethnicity_id?: number | null
  religion_id?: number | null
  id_number?: string | null
  id_issued_on?: string | null
  id_issued_by?: string | null
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
  address?: string | null
  current_company?: string | null
  current_position?: string | null
  expected_salary?: number | null
  source_channel_id?: number | null
  source_note?: string | null
  internal_note?: string | null
  tags?: string[]
}

export interface CandidateUpdate extends Partial<CandidateCreate> {}

export interface ApplicationCreate {
  job_requisition_id: number
  applied_date?: string
  source_channel_id?: number | null
  internal_note?: string | null
}

export interface ApplicationRead {
  id: number
  candidate_id: number
  candidate_name: string
  job_requisition_id: number
  job_requisition_code: string
  job_position_name: string
  department_name: string
  applied_date: string
  source_channel_name: string | null
  current_stage: string
  rejection_reason: string | null
  internal_note: string | null
  created_at: string
  updated_at: string
}

export interface ApplicationListPage {
  items: ApplicationRead[]
  total: number
  page: number
  page_size: number
}

export interface ImportResult {
  created: number
  updated: number
  skipped: number
  errors: string[]
}
