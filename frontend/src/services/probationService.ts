import api from '@/services/api'

// ── Interfaces ─────────────────────────────────────────────────────────────────

export interface ProbationLegalCheck {
  is_valid: boolean
  violations: string[]
  warnings: string[]
  probation_days: number
  probation_limit: number | null
  probation_limit_configured: boolean
  probation_legal_group_code: string | null
  probation_legal_group_label: string | null
}

export interface ProbationEvaluationRead {
  id: number
  employee_id: number
  job_record_id: number
  evaluation_date: string
  evaluator_id: number
  evaluator_name: string
  hr_reviewer_id: number | null
  attitude_score: number | null
  competence_score: number | null
  culture_score: number | null
  kpi_score: number | null
  overall_score: number | null
  manager_comment: string | null
  hr_comment: string | null
  result: string  // pending|passed|failed|extended
  extension_days: number | null
  status: string  // draft|submitted|approved
  approved_by_id: number | null
  approved_by_name: string | null
  approved_at: string | null
  created_at: string
  updated_at: string
}

export interface ProbationDetailRead {
  employee_id: number
  employee_name: string
  employee_code: string
  department_name: string | null
  job_position_name: string | null
  job_title_name: string | null
  job_title_level: number | null
  status: string
  probation_mode: 'active' | 'historical' | 'none'
  can_edit_evaluation: boolean
  can_generate_contract: boolean
  approval_triggers_workflow: boolean
  probation_start_date: string | null
  probation_end_date: string | null
  official_date: string | null
  days_remaining: number | null
  legal_check: ProbationLegalCheck
  evaluation: ProbationEvaluationRead | null
  contracts: unknown[]
}

export interface ProbationEvaluationCreate {
  evaluation_date: string
  evaluator_id: number
  attitude_score?: number | null
  competence_score?: number | null
  culture_score?: number | null
  kpi_score?: number | null
  result: string
  extension_days?: number | null
  manager_comment?: string | null
}

export interface ProbationEvaluationUpdate {
  evaluation_date?: string
  evaluator_id?: number
  attitude_score?: number | null
  competence_score?: number | null
  culture_score?: number | null
  kpi_score?: number | null
  result?: string
  extension_days?: number | null
  manager_comment?: string | null
}

export interface ProbationApprovePayload {
  result: string
  hr_comment?: string | null
  extension_days?: number | null
}

export interface EmployeeContractRead {
  id: number
  employee_id: number
  contract_number: string | null
  contract_type: string
  start_date: string
  end_date: string | null
  signed_date: string | null
  status: string
  created_at: string
  updated_at: string
}

// ── Service ────────────────────────────────────────────────────────────────────

export const probationService = {
  getDetail: (employeeId: number) =>
    api.get<ProbationDetailRead>(`/employees/${employeeId}/probation`),

  getLegalCheck: (employeeId: number) =>
    api.get<ProbationLegalCheck>(`/employees/${employeeId}/probation/legal-check`),

  createEvaluation: (employeeId: number, data: ProbationEvaluationCreate) =>
    api.post<ProbationEvaluationRead>(`/employees/${employeeId}/probation/evaluate`, data),

  updateEvaluation: (employeeId: number, evalId: number, data: ProbationEvaluationUpdate) =>
    api.patch<ProbationEvaluationRead>(`/employees/${employeeId}/probation/evaluate/${evalId}`, data),

  submitEvaluation: (employeeId: number) =>
    api.post<ProbationEvaluationRead>(`/employees/${employeeId}/probation/submit`),

  approveEvaluation: (employeeId: number, payload: ProbationApprovePayload) =>
    api.post<ProbationEvaluationRead>(`/employees/${employeeId}/probation/approve`, payload),

  recallEvaluation: (employeeId: number) =>
    api.post<ProbationEvaluationRead>(`/employees/${employeeId}/probation/recall`),

  getContracts: (employeeId: number) =>
    api.get<EmployeeContractRead[]>(`/employees/${employeeId}/probation/contract`),

  generateContract: (employeeId: number) =>
    api.post<EmployeeContractRead>(`/employees/${employeeId}/probation/contract/generate`),
}

export default probationService
