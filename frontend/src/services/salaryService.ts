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
}
