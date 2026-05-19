import api from './api'

export interface EmployeeCodeSequenceRead {
  id: number
  code: string
  name: string
  description: string | null
  min_digits: number
  next_value: number
  is_active: boolean
}

export interface EmployeeCodeSequenceRuleRead {
  id: number
  employee_code_sequence_id: number
  employee_code_sequence_code: string
  employee_code_sequence_name: string
  department_id: number | null
  job_position_id: number | null
  apply_to_descendants: boolean
  note: string | null
}

export interface EmployeeCodeSequenceRuleUpsert {
  employee_code_sequence_id: number
  apply_to_descendants?: boolean
  note?: string | null
}

export default {
  getSequences: () =>
    api.get<EmployeeCodeSequenceRead[]>('/employee-code-sequences'),

  getDepartmentRule: (departmentId: number) =>
    api.get<EmployeeCodeSequenceRuleRead | null>(`/departments/${departmentId}/employee-code-rule`),

  upsertDepartmentRule: (departmentId: number, data: EmployeeCodeSequenceRuleUpsert) =>
    api.put<EmployeeCodeSequenceRuleRead>(`/departments/${departmentId}/employee-code-rule`, data),

  deleteDepartmentRule: (departmentId: number) =>
    api.delete<{ message: string }>(`/departments/${departmentId}/employee-code-rule`),

  getJobPositionRule: (jobPositionId: number) =>
    api.get<EmployeeCodeSequenceRuleRead | null>(`/job-positions/${jobPositionId}/employee-code-rule`),

  upsertJobPositionRule: (jobPositionId: number, data: EmployeeCodeSequenceRuleUpsert) =>
    api.put<EmployeeCodeSequenceRuleRead>(`/job-positions/${jobPositionId}/employee-code-rule`, data),

  deleteJobPositionRule: (jobPositionId: number) =>
    api.delete<{ message: string }>(`/job-positions/${jobPositionId}/employee-code-rule`),
}
