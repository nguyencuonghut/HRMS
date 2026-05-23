import api from './api'

export interface SalaryEmployeeRow {
  employee_id: number
  employee_code: string
  full_name: string
  department_id: number | null
  department_name: string | null
  position_title: string | null
  insurance_basis_amount: string | null   // Decimal serialized as string
  insurance_basis_source: string | null   // 'contract' | 'manual_fixed' | 'computed'
  participation_status: string | null     // 'active' | 'paused' | 'stopped'
  active_contract_insurance_salary: string | null
  has_discrepancy: boolean
}

export interface SalaryEmployeeListPage {
  items: SalaryEmployeeRow[]
  total: number
  page: number
  page_size: number
}

export interface SalaryBhxhBasisDetail {
  employee_id: number
  employee_code: string
  full_name: string
  department_name: string | null
  position_title: string | null
  insurance_basis_amount: string | null
  insurance_basis_source: string | null
  participation_status: string | null
  active_contract_id: number | null
  active_contract_type: string | null
  active_contract_insurance_salary: string | null
  active_contract_effective_from: string | null
  has_discrepancy: boolean
}

export interface BhxhSalaryHistoryItem {
  effective_date: string
  basis_amount: string
  source_type: string             // 'contract' | 'manual_adjustment'
  note: string | null
  decision_number: string | null
  old_basis_amount: string | null
  created_by_name: string | null
}

export interface BhxhSalaryAdjustmentCreate {
  employee_id: number
  new_basis_amount: number
  effective_date: string          // 'YYYY-MM-DD'
  reason: string
  decision_number?: string | null
}

export interface BhxhSalaryAdjustmentRead {
  id: number
  employee_id: number
  employee_code: string
  employee_name: string
  department_name: string | null
  decision_number: string | null
  old_basis_amount: string
  new_basis_amount: string
  change_direction: 'increase' | 'decrease'
  change_amount: string
  change_pct: number
  effective_date: string
  reason: string
  created_by_id: number | null
  created_by_name: string | null
  created_at: string
  insurance_change_event_id: number | null
}

export interface BhxhSalaryAdjustmentListPage {
  items: BhxhSalaryAdjustmentRead[]
  total: number
  page: number
  page_size: number
}

export interface SalarySummaryRates {
  bhxh_employee_rate: string
  bhyt_employee_rate: string
  bhtn_employee_rate: string
  bhxh_employer_rate: string
  bhyt_employer_rate: string
  bhtn_employer_rate: string
}

export interface SalarySummaryRow {
  stt: number
  employee_id: number
  employee_code: string
  full_name: string
  department_name: string | null
  basis_amount: string
  bhxh_employee: string
  bhyt_employee: string
  bhtn_employee: string
  total_employee: string
  bhxh_employer: string
  bhyt_employer: string
  bhtn_employer: string
  total_employer: string
  grand_total: string
}

export interface SalarySummaryTotals {
  total_employees: number
  sum_basis: string
  sum_bhxh_employee: string
  sum_bhyt_employee: string
  sum_bhtn_employee: string
  sum_total_employee: string
  sum_bhxh_employer: string
  sum_bhyt_employer: string
  sum_bhtn_employer: string
  sum_total_employer: string
  sum_grand_total: string
}

export interface SalarySummaryPage {
  year: number
  month: number
  rates: SalarySummaryRates
  items: SalarySummaryRow[]
  totals: SalarySummaryTotals
  total: number
  page: number
  page_size: number
}

export default {
  listEmployees(params: {
    department_id?: number | null
    search?: string | null
    participation_status?: string | null
    page?: number
    page_size?: number
  }) {
    return api.get<SalaryEmployeeListPage>('/salary/employees', { params })
  },

  getEmployeeBhxhBasis(employeeId: number) {
    return api.get<SalaryBhxhBasisDetail>(`/salary/employees/${employeeId}/bhxh-basis`)
  },

  getEmployeeBhxhHistory(employeeId: number) {
    return api.get<BhxhSalaryHistoryItem[]>(`/salary/employees/${employeeId}/bhxh-history`)
  },

  createAdjustment(data: BhxhSalaryAdjustmentCreate) {
    return api.post<BhxhSalaryAdjustmentRead>('/salary/adjustments', data)
  },

  listAdjustments(params: {
    employee_id?: number | null
    department_id?: number | null
    search?: string | null
    from_date?: string | null
    to_date?: string | null
    page?: number
    page_size?: number
  }) {
    return api.get<BhxhSalaryAdjustmentListPage>('/salary/adjustments', { params })
  },

  getEmployeeAdjustmentHistory(employeeId: number) {
    return api.get<BhxhSalaryAdjustmentRead[]>(`/salary/employees/${employeeId}/adjustment-history`)
  },

  getSalarySummary(params: {
    year: number
    month: number
    department_id?: number | null
    page?: number
    page_size?: number
  }) {
    return api.get<SalarySummaryPage>('/salary/summary', { params })
  },

  exportSalarySummary(params: { year: number; month: number; department_id?: number | null }) {
    return api.get('/salary/summary/export', { params, responseType: 'blob' })
  },
}
