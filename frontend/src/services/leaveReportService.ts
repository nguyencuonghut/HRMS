import api from './api'

export interface EmployeeSummaryRow {
  employee_id: number
  employee_code: string
  employee_name: string
  department_name: string | null
  leave_type_id: number
  leave_type_name: string
  leave_type_code: string
  allocated_days: number
  carryover_days: number
  carryover_expires: string | null
  used_days: number
  remaining_days: number
  record_count: number
}

export interface EmployeeSummaryReport {
  year: number
  items: EmployeeSummaryRow[]
  total: number
  page: number
  page_size: number
}

export interface DepartmentSummaryRow {
  department_id: number | null
  department_name: string | null
  leave_type_id: number
  leave_type_name: string
  employee_count: number
  total_records: number
  total_days_taken: number
  avg_days_per_employee: number
}

export interface DepartmentSummaryReport {
  year: number
  month_from: number | null
  month_to: number | null
  items: DepartmentSummaryRow[]
}

export interface YearEndRow {
  employee_id: number
  employee_code: string
  employee_name: string
  department_name: string | null
  leave_type_name: string
  leave_type_code: string
  allocated_days: number
  carryover_days: number
  used_days: number
  remaining_days: number
  will_carry: number
}

export interface YearEndReport {
  year: number
  items: YearEndRow[]
  total: number
  page: number
  page_size: number
}

export default {
  employeeSummary: (params: Record<string, unknown>) =>
    api.get<EmployeeSummaryReport>('/leave-reports/employee-summary', { params }),

  departmentSummary: (params: Record<string, unknown>) =>
    api.get<DepartmentSummaryReport>('/leave-reports/department-summary', { params }),

  yearEnd: (params: Record<string, unknown>) =>
    api.get<YearEndReport>('/leave-reports/year-end', { params }),

  exportUrl: (reportType: 'A' | 'B' | 'C', params: Record<string, unknown>): string => {
    const qs = new URLSearchParams({
      report_type: reportType,
      ...Object.fromEntries(
        Object.entries(params)
          .filter(([, v]) => v !== null && v !== undefined && v !== '')
          .map(([k, v]) => [k, String(v)])
      ),
    }).toString()
    return `/api/v1/leave-reports/export?${qs}`
  },
}
