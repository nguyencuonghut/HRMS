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

// ── Service ────────────────────────────────────────────────────────────────────

const BASE = '/reports/probation'

export default {
  getActive: (params?: { department_id?: number; keyword?: string }) =>
    api.get<ActiveProbationReport>(`${BASE}/active`, { params }),

  getChecklistCompletion: (params: { start_date: string; end_date: string; department_id?: number }) =>
    api.get<ChecklistCompletionReport>(`${BASE}/checklist-completion`, { params }),

  getPassRate: (params: { start_date: string; end_date: string; department_id?: number }) =>
    api.get<ProbationPassRateReport>(`${BASE}/pass-rate`, { params }),

  getFailureReasons: (params: { start_date: string; end_date: string }) =>
    api.get<FailureReasonReport>(`${BASE}/failure-reasons`, { params }),

  getExportUrl: (params: { start_date: string; end_date: string; department_id?: number }) => {
    const token = localStorage.getItem('access_token') ?? ''
    const qs = new URLSearchParams({
      start_date: params.start_date,
      end_date: params.end_date,
      ...(params.department_id ? { department_id: String(params.department_id) } : {}),
    })
    return { url: `/api/v1${BASE}/export?${qs}`, token }
  },
}
