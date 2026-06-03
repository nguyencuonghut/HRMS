import api from './api'

export type InsuranceSalaryMode = 'computed_by_position_group' | 'fixed_manual'

export interface ContractRead {
  id: number
  employee_id: number
  parent_contract_id: number | null
  contract_category_id: number
  category_name: string
  document_kind: 'labor_contract' | 'contract_appendix'
  contract_number: string
  signed_date: string
  effective_from: string
  effective_to: string | null
  insurance_salary: string | null
  insurance_salary_mode: InsuranceSalaryMode
  bhxh_position_group_id: number | null
  bhxh_position_group_code: string | null
  bhxh_position_group_name: string | null
  insurance_salary_grade_no: number | null
  insurance_salary_fixed_amount: string | null
  status: string
  status_display: string
  days_until_expiry: number | null
  has_file: boolean
  file_name: string | null
  file_size: number | null
  mime_type: string | null
  notes: string | null
  created_at: string
  updated_at: string | null
  appendices: ContractRead[]
}

export interface ContractCreate {
  contract_category_id: number
  contract_number: string
  signed_date: string
  effective_from: string
  effective_to?: string | null
  insurance_salary_mode?: InsuranceSalaryMode | null
  bhxh_position_group_id?: number | null
  insurance_salary_grade_no?: number | null
  insurance_salary_fixed_amount?: string | null
  insurance_salary?: string | null
  parent_contract_id?: number | null
  notes?: string | null
}

export interface ContractUpdate {
  contract_number?: string
  signed_date?: string
  effective_from?: string
  effective_to?: string | null
  insurance_salary_mode?: InsuranceSalaryMode | null
  bhxh_position_group_id?: number | null
  insurance_salary_grade_no?: number | null
  insurance_salary_fixed_amount?: string | null
  insurance_salary?: string | null
  status?: string
  notes?: string | null
}

export interface ContractInsuranceSalaryPreviewInput {
  effective_from: string
  insurance_salary_mode: InsuranceSalaryMode
  bhxh_position_group_id?: number | null
  insurance_salary_grade_no?: number | null
  insurance_salary_fixed_amount?: string | null
}

export interface ContractInsuranceSalaryPreviewRead {
  insurance_salary_mode: InsuranceSalaryMode
  insurance_salary: string | null
  bhxh_position_group_id: number | null
  bhxh_position_group_code: string | null
  bhxh_position_group_name: string | null
  insurance_salary_grade_no: number | null
  insurance_salary_fixed_amount: string | null
  company_region: number | null
  regional_minimum_wage: string | null
  salary_scale_id: number | null
  salary_scale_name: string | null
  coefficient: string | null
}

export interface ContractListPage {
  items: ContractRead[]
  total: number
  page: number
  page_size: number
}

export const DOCUMENT_KIND_LABELS: Record<string, string> = {
  labor_contract: 'Hợp đồng lao động',
  contract_appendix: 'Phụ lục hợp đồng',
}

export const DOCUMENT_KIND_OPTIONS = [
  { label: 'Hợp đồng lao động', value: 'labor_contract' },
  { label: 'Phụ lục hợp đồng', value: 'contract_appendix' },
]

export const CONTRACT_STATUS_OPTIONS = [
  { label: 'Đang hiệu lực', value: 'active' },
  { label: 'Hết hạn', value: 'expired' },
  { label: 'Đã hủy', value: 'terminated' },
  { label: 'Chưa hiệu lực', value: 'draft' },
]

export const EXPIRING_OPTIONS = [
  { label: '7 ngày tới', value: 7 },
  { label: '30 ngày tới', value: 30 },
  { label: '60 ngày tới', value: 60 },
  { label: '90 ngày tới', value: 90 },
]

export function statusSeverity(status: string): 'success' | 'warn' | 'danger' | 'secondary' {
  if (status === 'active') return 'success'
  if (status === 'draft') return 'warn'
  if (status === 'terminated') return 'danger'
  return 'secondary'
}

async function downloadFile(employeeId: number, contractId: number, fileName: string) {
  const resp = await api.get(`/employees/${employeeId}/contracts/${contractId}/download`, {
    responseType: 'blob',
  })
  const url = URL.createObjectURL(resp.data as Blob)
  const a = document.createElement('a')
  a.href = url
  a.download = fileName
  a.click()
  URL.revokeObjectURL(url)
}

export default {
  listContracts: (employeeId: number) =>
    api.get<ContractRead[]>(`/employees/${employeeId}/contracts`),

  previewInsuranceSalary: (employeeId: number, data: ContractInsuranceSalaryPreviewInput) =>
    api.post<ContractInsuranceSalaryPreviewRead>(`/employees/${employeeId}/contracts/preview-insurance-salary`, data),

  createContract: (employeeId: number, data: ContractCreate) =>
    api.post<ContractRead>(`/employees/${employeeId}/contracts`, data),

  updateContract: (employeeId: number, contractId: number, data: ContractUpdate) =>
    api.put<ContractRead>(`/employees/${employeeId}/contracts/${contractId}`, data),

  terminateContract: (employeeId: number, contractId: number) =>
    api.delete<ContractRead>(`/employees/${employeeId}/contracts/${contractId}`),

  uploadFile: (employeeId: number, contractId: number, file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post<ContractRead>(`/employees/${employeeId}/contracts/${contractId}/upload`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  downloadFile,

  deleteFile: (employeeId: number, contractId: number) =>
    api.delete<ContractRead>(`/employees/${employeeId}/contracts/${contractId}/file`),

  generateContract: async (employeeId: number, contractId: number, templateId: number, filename: string) => {
    const resp = await api.post(
      `/employees/${employeeId}/contracts/${contractId}/generate`,
      { template_id: templateId },
      { responseType: 'blob' },
    )
    const url = URL.createObjectURL(resp.data as Blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  },

  listContractsGlobal: (params?: Record<string, unknown>) =>
    api.get<ContractListPage>('/contracts', { params }),
}
