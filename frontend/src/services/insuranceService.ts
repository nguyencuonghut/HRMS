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
}
