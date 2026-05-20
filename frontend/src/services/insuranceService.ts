import api from './api'

export interface InsuranceContributionComponentRead {
  code: string
  name_vi: string
  insurance_kind: string
  sort_order: number
  is_active: boolean
}

export interface InsurancePolicyComponentRateInput {
  component_code: string
  employee_rate_percent: string
  employer_rate_percent: string
  employer_advances_employee_part: boolean
}

export interface InsurancePolicyComponentRateRead extends InsurancePolicyComponentRateInput {
  id: number
  component_name: string
  insurance_kind: string
  sort_order: number
  is_active: boolean
}

export interface InsurancePolicyVersionRead {
  id: number
  code: string
  name: string
  legal_basis_summary: string | null
  effective_from: string
  effective_to: string | null
  is_active: boolean
  company_region: number
  note: string | null
  components: InsurancePolicyComponentRateRead[]
  created_at: string
  updated_at: string | null
}

export interface InsurancePolicyVersionCreate {
  code: string
  name: string
  legal_basis_summary?: string | null
  effective_from: string
  company_region: number
  note?: string | null
  components: InsurancePolicyComponentRateInput[]
}

export interface InsurancePolicyVersionUpdate {
  name?: string
  legal_basis_summary?: string | null
  effective_from?: string
  company_region?: number
  note?: string | null
  components?: InsurancePolicyComponentRateInput[]
}

export interface CompanyRegionHistoryItem {
  id: number
  region: number
  effective_from: string
  effective_to: string | null
  note: string | null
}

export interface CompanyRegionRead {
  current: CompanyRegionHistoryItem | null
  history: CompanyRegionHistoryItem[]
}

export interface CompanyRegionUpsert {
  region: number
  effective_from: string
  note?: string | null
}

export interface InsuranceEffectiveContributionConfigRead {
  as_of_date: string
  company_region: CompanyRegionHistoryItem
  policy_version: InsurancePolicyVersionRead
}

// ── Employee insurance profile ────────────────────────────────────────────────

export interface InsuranceContributionComponentSnapshot {
  component_code: string
  component_name: string
  insurance_kind: string
  sort_order: number
  calc_mode: string // 'company_policy' | 'fixed_amount'
  employee_rate_percent: string | null
  employer_rate_percent: string | null
  fixed_employee_amount: string | null
  fixed_employer_amount: string | null
  employer_advances_employee_part: boolean
  employee_amount: string | null
  employer_amount: string | null
}

export interface EmployeeInsuranceListItem {
  employee_id: number
  employee_code: string
  employee_name: string
  department_name: string | null
  job_title_name: string | null
  bhxh_code: string | null
  bhyt_initial_clinic_name: string | null
  company_bhxh_joined_date: string | null
  participation_status: string
  insurance_basis_amount: string | null
  insurance_basis_source: string
  policy_version_id: number | null
  policy_version_name: string | null
  effective_regulation_code: string | null
  company_region: number | null
  has_component_overrides: boolean
  employer_pays_on_behalf: boolean
  contract_id: number | null
  contract_number: string | null
  contributions: InsuranceContributionComponentSnapshot[]
}

export interface EmployeeInsuranceListPage {
  items: EmployeeInsuranceListItem[]
  total: number
  page: number
  page_size: number
}

export interface EmployeeInsuranceProfileRead extends EmployeeInsuranceListItem {
  id: number
  status_effective_from: string | null
  status_note: string | null
  created_at: string
  updated_at: string | null
}

export interface EmployeeInsuranceComponentOverrideInput {
  component_code: string
  use_company_default: boolean
  fixed_employee_amount?: number | null
  fixed_employer_amount?: number | null
  employer_advances_employee_part?: boolean | null
}

export interface EmployeeInsuranceProfileUpdate {
  bhxh_code?: string | null
  bhyt_initial_clinic_name?: string | null
  company_bhxh_joined_date?: string | null
  participation_status: 'active' | 'paused' | 'stopped'
  status_effective_from?: string | null
  status_note?: string | null
  insurance_basis_source: 'contract' | 'computed' | 'manual_fixed'
  insurance_basis_amount?: number | null
  component_overrides?: EmployeeInsuranceComponentOverrideInput[]
}

export interface InsuranceListFilters {
  keyword?: string | null
  department_id?: number | null
  participation_status?: string | null
  has_bhxh_code?: boolean | null
  joined_from?: string | null
  joined_to?: string | null
  policy_version_id?: number | null
  has_component_overrides?: boolean | null
  employer_pays_on_behalf?: boolean | null
  page?: number
  page_size?: number
}

export default {
  getComponents: () =>
    api.get<InsuranceContributionComponentRead[]>('/insurance/components'),

  getPolicyVersions: () =>
    api.get<InsurancePolicyVersionRead[]>('/insurance/policy-versions'),

  createPolicyVersion: (payload: InsurancePolicyVersionCreate) =>
    api.post<InsurancePolicyVersionRead>('/insurance/policy-versions', payload),

  updatePolicyVersion: (policyId: number, payload: InsurancePolicyVersionUpdate) =>
    api.put<InsurancePolicyVersionRead>(`/insurance/policy-versions/${policyId}`, payload),

  activatePolicyVersion: (policyId: number) =>
    api.post<InsurancePolicyVersionRead>(`/insurance/policy-versions/${policyId}/activate`),

  deletePolicyVersion: (policyId: number) =>
    api.delete(`/insurance/policy-versions/${policyId}`),

  getCompanyRegion: () =>
    api.get<CompanyRegionRead>('/insurance/company-region'),

  updateCompanyRegion: (payload: CompanyRegionUpsert) =>
    api.put<CompanyRegionRead>('/insurance/company-region', payload),

  getEffectiveConfig: (asOfDate: string) =>
    api.get<InsuranceEffectiveContributionConfigRead>('/insurance/effective-config', { params: { as_of_date: asOfDate } }),

  // Employee insurance profiles
  listEmployeeProfiles: (filters: InsuranceListFilters) =>
    api.get<EmployeeInsuranceListPage>('/insurance/employees', { params: filters }),

  getEmployeeProfile: (employeeId: number) =>
    api.get<EmployeeInsuranceProfileRead>(`/insurance/employees/${employeeId}`),

  updateEmployeeProfile: (employeeId: number, payload: EmployeeInsuranceProfileUpdate) =>
    api.put<EmployeeInsuranceProfileRead>(`/insurance/employees/${employeeId}`, payload),
}
