import api from './api'

export interface MonthlyTrendPoint {
  month: number
  total_days: number
  total_records: number
  employee_count: number
}

export interface LeaveAnalyticsSummary {
  year: number
  department_id: number | null
  total_days_ytd: number
  avg_usage_rate: number
  employees_not_taken: number
  days_expiring_30d: number
  monthly_trend: MonthlyTrendPoint[]
}

export interface LeaveTypeStatRow {
  leave_type_id: number
  leave_type_name: string
  color_tag: string | null
  record_count: number
  total_days: number
  unique_employees: number
  percentage: number
}

export interface LeaveByTypeReport {
  year: number
  department_id: number | null
  items: LeaveTypeStatRow[]
  grand_total_days: number
}

export interface HeatmapDeptRow {
  dept_id: number | null
  dept_name: string | null
  monthly_days: Record<number, number>
  annual_total: number
}

export interface MonthlyHeatmapReport {
  year: number
  departments: HeatmapDeptRow[]
  company_monthly: Record<number, number>
}

export interface TopEmployeeRow {
  rank: number
  employee_id: number
  employee_code: string
  employee_name: string
  dept_name: string | null
  total_days_taken: number
  record_count: number
  total_entitled: number
  usage_rate: number
}

export interface TopEmployeesReport {
  year: number
  department_id: number | null
  items: TopEmployeeRow[]
}

export interface ExpiringBalanceRow {
  employee_id: number
  employee_code: string
  employee_name: string
  dept_name: string | null
  leave_type_name: string
  carryover_days: number
  remaining_days: number
  carryover_expires: string
  days_until_expire: number
}

export interface ExpiringBalanceReport {
  expire_days: number
  year: number
  department_id: number | null
  items: ExpiringBalanceRow[]
  total_expiring_days: number
}

export interface DeptComparisonRow {
  dept_id: number | null
  dept_name: string | null
  employee_count: number
  total_days_taken: number
  avg_days_per_employee: number
  allocated_total: number
  usage_rate: number
}

export interface DeptComparisonReport {
  year: number
  items: DeptComparisonRow[]
}

const leaveAnalyticsService = {
  getAnalyticsSummary: (params: { year: number; department_id?: number | null; leave_type_id?: number | null }) =>
    api.get<LeaveAnalyticsSummary>('/reports/leaves/analytics-summary', { params }),

  getByType: (params: { year: number; department_id?: number | null }) =>
    api.get<LeaveByTypeReport>('/reports/leaves/by-type', { params }),

  getMonthlyHeatmap: (params: { year: number }) =>
    api.get<MonthlyHeatmapReport>('/reports/leaves/monthly-heatmap', { params }),

  getTopEmployees: (params: { year: number; department_id?: number | null; leave_type_id?: number | null; limit?: number }) =>
    api.get<TopEmployeesReport>('/reports/leaves/top-employees', { params }),

  getExpiringBalance: (params: { year: number; department_id?: number | null; expire_days?: number }) =>
    api.get<ExpiringBalanceReport>('/reports/leaves/expiring-balance', { params }),

  getDeptComparison: (params: { year: number }) =>
    api.get<DeptComparisonReport>('/reports/leaves/department-comparison', { params }),

  exportAnalyticsUrl: (params: { year: number; department_id?: number | null }): string => {
    const qs = new URLSearchParams(
      Object.entries(params)
        .filter(([, v]) => v !== null && v !== undefined)
        .map(([k, v]) => [k, String(v)])
    ).toString()
    return `/api/v1/reports/leaves/export-analytics?${qs}`
  },
}

export default leaveAnalyticsService
