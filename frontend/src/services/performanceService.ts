import api from './api'
import type { RewardRead } from './rewardService'
import type { TrainingRecordRead } from './trainingService'

// ── Types ─────────────────────────────────────────────────────────────────────

export interface KpiMonthlyRead {
  id: number
  employee_id: number
  employee_code: string
  employee_name: string
  department_name: string | null
  year: number
  month: number
  score: string          // Decimal as string from backend
  note: string | null
  created_by_name: string | null
  created_at: string
  updated_at: string
}

export interface KpiMonthlyCreate {
  employee_id: number
  year: number
  month: number
  score: number
  note?: string | null
}

export interface KpiMonthlyUpdate {
  score?: number | null
  note?: string | null
}

export interface KpiMonthlyListPage {
  items: KpiMonthlyRead[]
  total: number
  page: number
  page_size: number
}

export interface KpiImportResult {
  created: number
  updated: number
  skipped: number
  errors: string[]
}

export interface KpiListParams {
  year?: number | null
  month?: number | null
  department_id?: number | null
  search?: string | null
  page?: number
  page_size?: number
}

// ── Yearly Review types ───────────────────────────────────────────────────────

export interface MonthlyScore {
  month: number
  score: string
}

export interface YearlyKpiSummary {
  employee_id: number
  employee_code: string
  employee_name: string
  department_name: string | null
  year: number
  monthly_scores: MonthlyScore[]
  months_count: number
  avg_score: string | null
  has_discipline: boolean
  suggested_rating: string | null
  has_review: boolean
  review_id: number | null
}

export interface YearlyReviewRead {
  id: number
  employee_id: number
  employee_code: string
  employee_name: string
  department_name: string | null
  year: number
  months_count: number
  avg_score: string | null
  rating: string
  rating_label: string
  review_note: string | null
  created_by_name: string | null
  created_at: string
  updated_at: string
}

export interface YearlyReviewCreate {
  employee_id: number
  year: number
  rating: string
  review_note?: string | null
}

export interface YearlyReviewUpdate {
  rating?: string | null
  review_note?: string | null
}

export interface YearlyReviewListPage {
  items: YearlyReviewRead[]
  total: number
  page: number
  page_size: number
}

export interface YearlyReviewListParams {
  year?: number | null
  department_id?: number | null
  rating?: string | null
  search?: string | null
  page?: number
  page_size?: number
}

// ── Report types (10.4) ───────────────────────────────────────────────────────

export interface RatingCount {
  rating: string
  rating_label: string
  count: number
  percentage: number
}

export interface RatingDistributionReport {
  year: number
  total_reviewed: number
  total_employees: number
  coverage_rate: number
  distribution: RatingCount[]
}

export interface DepartmentKpiStat {
  department_id: number | null
  department_name: string | null
  employee_count: number
  avg_score: string | null
  min_score: string | null
  max_score: string | null
  months_data_count: number
}

export interface MonthlyPoint {
  month: number
  avg_score: string | null
  employee_count: number
}

export interface MonthlyKpiTrend {
  year: number
  department_id: number | null
  department_name: string | null
  points: MonthlyPoint[]
}

// ── API ───────────────────────────────────────────────────────────────────────

const BASE = '/performance/kpi'

export default {
  list: (params: KpiListParams = {}) =>
    api.get<KpiMonthlyListPage>(BASE, { params }),

  get: (id: number) =>
    api.get<KpiMonthlyRead>(`${BASE}/${id}`),

  create: (data: KpiMonthlyCreate) =>
    api.post<KpiMonthlyRead>(BASE, data),

  update: (id: number, data: KpiMonthlyUpdate) =>
    api.put<KpiMonthlyRead>(`${BASE}/${id}`, data),

  delete: (id: number) =>
    api.delete(`${BASE}/${id}`),

  importExcel: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post<KpiImportResult>(`${BASE}/import`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  downloadTemplate: () =>
    api.get(`${BASE}/template`, { responseType: 'blob' }),

  // Yearly Reviews (10.2)
  getYearlySummary: (employee_id: number, year: number) =>
    api.get<YearlyKpiSummary>(`/performance/yearly-summary/${employee_id}`, { params: { year } }),

  listYearlyReviews: (params: YearlyReviewListParams = {}) =>
    api.get<YearlyReviewListPage>('/performance/yearly-reviews', { params }),

  getYearlyReview: (id: number) =>
    api.get<YearlyReviewRead>(`/performance/yearly-reviews/${id}`),

  createYearlyReview: (data: YearlyReviewCreate) =>
    api.post<YearlyReviewRead>('/performance/yearly-reviews', data),

  updateYearlyReview: (id: number, data: YearlyReviewUpdate) =>
    api.put<YearlyReviewRead>(`/performance/yearly-reviews/${id}`, data),

  deleteYearlyReview: (id: number) =>
    api.delete(`/performance/yearly-reviews/${id}`),

  // Link (10.3)
  createRewardFromReview: (reviewId: number, data: { reward_type_id: number; decision_date: string; amount?: number | null; note?: string | null }) =>
    api.post<RewardRead>(`/performance/yearly-reviews/${reviewId}/create-reward`, data),

  createTrainingFromReview: (reviewId: number, data: { course_id: number; plan_id?: number | null; note?: string | null }) =>
    api.post<TrainingRecordRead>(`/performance/yearly-reviews/${reviewId}/create-training`, data),

  getEmployeeKpiHistory: (employeeId: number, year?: number | null) =>
    api.get<KpiMonthlyRead[]>(`/employees/${employeeId}/performance/kpi`, { params: year ? { year } : {} }),

  getEmployeeReviewHistory: (employeeId: number) =>
    api.get<YearlyReviewRead[]>(`/employees/${employeeId}/performance/reviews`),

  // Reports (10.4)
  getRatingDistribution: (year: number) =>
    api.get<RatingDistributionReport>('/performance/report/rating-distribution', { params: { year } }),

  getDepartmentKpi: (year: number, month?: number | null, department_id?: number | null) =>
    api.get<DepartmentKpiStat[]>('/performance/report/department-kpi', {
      params: { year, ...(month ? { month } : {}), ...(department_id ? { department_id } : {}) },
    }),

  getMonthlyTrend: (year: number, department_id?: number | null) =>
    api.get<MonthlyKpiTrend>('/performance/report/monthly-trend', {
      params: { year, ...(department_id ? { department_id } : {}) },
    }),

  exportReport: (year: number) =>
    api.get('/performance/report/export', { params: { year }, responseType: 'blob' }),
}
