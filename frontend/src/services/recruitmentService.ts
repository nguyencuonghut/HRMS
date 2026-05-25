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
}
