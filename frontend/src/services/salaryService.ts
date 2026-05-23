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
}
