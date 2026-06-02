import api from '@/services/api'

// ── Interfaces ─────────────────────────────────────────────────────────────────

export interface ActiveProbationRow {
  employee_id: number
  employee_name: string
  employee_code: string
  department_id: number | null
  department_name: string | null
  probation_start_date: string | null
  probation_end_date: string | null
  days_remaining: number | null
  urgency: 'normal' | 'warning' | 'critical'
  onboarding_status: string | null
  completion_pct: number | null
  evaluation_result: 'not_started' | 'pending' | 'passed' | 'failed' | 'extended'
}

export interface ActiveProbationReport {
  items: ActiveProbationRow[]
  total: number
}

export interface ChecklistCompletionRow {
  department_id: number
  department_name: string
  total_checklists: number
  completed_count: number
  completion_rate: number
  avg_completion_pct: number
}

export interface ChecklistCompletionReport {
  period_start: string
  period_end: string
  items: ChecklistCompletionRow[]
}

export interface ProbationHistoryRow {
  employee_id: number
  employee_name: string
  employee_code: string
  employee_status: string
  department_id: number | null
  department_name: string | null
  probation_start_date: string | null
  probation_end_date: string | null
  days_remaining: number | null
  onboarding_status: string | null
  completion_pct: number | null
  evaluation_result: 'not_started' | 'pending' | 'passed' | 'failed' | 'extended'
  evaluation_status: string | null
}

export interface ProbationHistoryReport {
  period_start: string | null
  period_end: string | null
  items: ProbationHistoryRow[]
  total: number
  page: number
  page_size: number
}

export interface ProbationPassRateStat {
  group_id: number | null
  group_name: string
  passed: number
  failed: number
  extended: number
  total_decided: number
  pass_rate: number | null
}

export interface MonthlyProbationTrend {
  year: number
  month: number
  passed: number
  failed: number
  extended: number
  total: number
}

export interface ProbationPassRateReport {
  period_start: string
  period_end: string
  overall: ProbationPassRateStat
  by_department: ProbationPassRateStat[]
  by_position: ProbationPassRateStat[]
  monthly_trend: MonthlyProbationTrend[]
}

export interface FailureKeywordCount {
  keyword: string
  count: number
  pct: number
}

export interface FailureCommentItem {
  employee_id: number
  employee_name: string
  evaluation_date: string
  manager_comment: string | null
}

export interface FailureReasonReport {
  total_failed: number
  reasons: FailureKeywordCount[]
  raw_comments: FailureCommentItem[]
}

export interface ProbationExportParams {
  start_date: string
  end_date: string
  department_id?: number
}

// ── Service ────────────────────────────────────────────────────────────────────

const BASE = '/reports/probation'

export default {
  getActive: (params?: { department_id?: number; keyword?: string }) =>
    api.get<ActiveProbationReport>(`${BASE}/active`, { params }),

  getHistory: (params: { start_date?: string; end_date?: string; department_id?: number; keyword?: string; page?: number; page_size?: number }) =>
    api.get<ProbationHistoryReport>(`${BASE}/history`, { params }),

  getChecklistCompletion: (params: { start_date: string; end_date: string; department_id?: number }) =>
    api.get<ChecklistCompletionReport>(`${BASE}/checklist-completion`, { params }),

  getPassRate: (params: { start_date: string; end_date: string; department_id?: number }) =>
    api.get<ProbationPassRateReport>(`${BASE}/pass-rate`, { params }),

  getFailureReasons: (params: { start_date: string; end_date: string }) =>
    api.get<FailureReasonReport>(`${BASE}/failure-reasons`, { params }),

  exportReport: (params: ProbationExportParams) =>
    api.get<Blob>(`${BASE}/export`, {
      params,
      responseType: 'blob',
    }),
}
