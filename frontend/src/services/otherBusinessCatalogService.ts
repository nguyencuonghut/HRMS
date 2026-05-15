import api from './api'

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface ContractCategoryRead {
  id: number
  code: string
  name: string
  normalized_name: string
  document_kind: 'labor_contract' | 'contract_appendix'
  legal_contract_type: 'indefinite_term' | 'definite_term' | null
  business_group: string | null
  default_term_months: number | null
  sort_order: number
  is_active: boolean
  description: string | null
  created_at: string
  updated_at: string | null
}

export interface ContractCategoryCreate {
  code: string
  name: string
  document_kind: 'labor_contract' | 'contract_appendix'
  legal_contract_type?: 'indefinite_term' | 'definite_term' | null
  business_group?: string | null
  default_term_months?: number | null
  sort_order?: number
  is_active?: boolean
  description?: string | null
}

export interface ContractCategoryUpdate {
  name?: string
  document_kind?: 'labor_contract' | 'contract_appendix'
  legal_contract_type?: 'indefinite_term' | 'definite_term' | null
  business_group?: string | null
  default_term_months?: number | null
  sort_order?: number
  is_active?: boolean
  description?: string | null
}

export interface NationalityRead {
  id: number
  code: string
  name: string
  normalized_name: string
  iso2_code: string | null
  iso3_code: string | null
  is_active: boolean
  created_at: string
  updated_at: string | null
}

export interface NationalityCreate {
  code: string
  name: string
  iso2_code?: string | null
  iso3_code?: string | null
  is_active?: boolean
}

export interface NationalityUpdate {
  name?: string
  iso2_code?: string | null
  iso3_code?: string | null
  is_active?: boolean
}

export interface EthnicityRead {
  id: number
  code: string
  name: string
  normalized_name: string
  is_active: boolean
  created_at: string
  updated_at: string | null
}

export interface EthnicityCreate {
  code: string
  name: string
  is_active?: boolean
}

export interface EthnicityUpdate {
  name?: string
  is_active?: boolean
}

export interface ReligionRead {
  id: number
  code: string
  name: string
  normalized_name: string
  is_active: boolean
  created_at: string
  updated_at: string | null
}

export interface ReligionCreate {
  code: string
  name: string
  is_active?: boolean
}

export interface ReligionUpdate {
  name?: string
  is_active?: boolean
}

export interface BankRead {
  id: number
  code: string
  name: string
  normalized_name: string
  short_name: string | null
  bin_code: string | null
  swift_code: string | null
  is_active: boolean
  created_at: string
  updated_at: string | null
}

export interface BankCreate {
  code: string
  name: string
  short_name?: string | null
  bin_code?: string | null
  swift_code?: string | null
  is_active?: boolean
}

export interface BankUpdate {
  name?: string
  short_name?: string | null
  bin_code?: string | null
  swift_code?: string | null
  is_active?: boolean
}

export interface SkillRead {
  id: number
  code: string
  name: string
  normalized_name: string
  skill_group: string | null
  is_active: boolean
  created_at: string
  updated_at: string | null
}

export interface SkillCreate {
  code: string
  name: string
  skill_group?: string | null
  is_active?: boolean
}

export interface SkillUpdate {
  name?: string
  skill_group?: string | null
  is_active?: boolean
}

export interface CertificateRead {
  id: number
  code: string
  name: string
  normalized_name: string
  certificate_group: string | null
  issuer_name: string | null
  expiry_policy: 'none' | 'fixed_date' | 'months_after_issue' | null
  default_valid_months: number | null
  is_active: boolean
  created_at: string
  updated_at: string | null
}

export interface CertificateCreate {
  code: string
  name: string
  certificate_group?: string | null
  issuer_name?: string | null
  expiry_policy?: 'none' | 'fixed_date' | 'months_after_issue' | null
  default_valid_months?: number | null
  is_active?: boolean
}

export interface CertificateUpdate {
  name?: string
  certificate_group?: string | null
  issuer_name?: string | null
  expiry_policy?: 'none' | 'fixed_date' | 'months_after_issue' | null
  default_valid_months?: number | null
  is_active?: boolean
}

export interface LeaveTypeRead {
  id: number
  code: string
  name: string
  normalized_name: string
  is_paid_leave: boolean
  affects_annual_leave: boolean
  allow_half_day: boolean
  requires_attachment: boolean
  color_tag: string | null
  is_active: boolean
  description: string | null
  created_at: string
  updated_at: string | null
}

export interface LeaveTypeCreate {
  code: string
  name: string
  is_paid_leave?: boolean
  affects_annual_leave?: boolean
  allow_half_day?: boolean
  requires_attachment?: boolean
  color_tag?: string | null
  is_active?: boolean
  description?: string | null
}

export interface LeaveTypeUpdate {
  name?: string
  is_paid_leave?: boolean
  affects_annual_leave?: boolean
  allow_half_day?: boolean
  requires_attachment?: boolean
  color_tag?: string | null
  is_active?: boolean
  description?: string | null
}

export interface ContractTemplateRead {
  id: number
  code: string
  name: string
  normalized_name: string
  contract_category_id: number
  document_kind: 'labor_contract' | 'contract_appendix'
  template_engine: 'docx_placeholders'
  file_name: string
  storage_path: string | null
  mime_type: string
  file_size: number | null
  file_checksum: string | null
  version_no: number
  effective_from: string | null
  effective_to: string | null
  is_active: boolean
  note: string | null
  created_at: string
  updated_at: string | null
}

export interface ContractTemplateCreate {
  code: string
  name: string
  contract_category_id: number
  document_kind: 'labor_contract' | 'contract_appendix'
  template_engine?: 'docx_placeholders'
  file_name: string
  storage_path?: string | null
  mime_type: string
  file_size?: number | null
  file_checksum?: string | null
  version_no?: number
  effective_from?: string | null
  effective_to?: string | null
  is_active?: boolean
  note?: string | null
}

export interface ContractTemplateUpdate {
  name?: string
  contract_category_id?: number
  document_kind?: 'labor_contract' | 'contract_appendix'
  template_engine?: 'docx_placeholders'
  file_name?: string
  storage_path?: string | null
  mime_type?: string
  file_size?: number | null
  file_checksum?: string | null
  effective_from?: string | null
  effective_to?: string | null
  is_active?: boolean
  note?: string | null
}

export interface ContractTemplatePlaceholderRead {
  id: number
  template_id: number
  placeholder_key: string
  label: string
  source_scope: 'employee' | 'organization' | 'contract_draft' | 'signer' | 'system'
  source_path: string
  data_type: 'text' | 'date' | 'number' | 'currency' | 'boolean'
  formatter: string | null
  is_required: boolean
  default_value: string | null
  sort_order: number
  created_at: string
  updated_at: string | null
}

export interface ContractTemplatePlaceholderWrite {
  placeholder_key: string
  label: string
  source_scope: 'employee' | 'organization' | 'contract_draft' | 'signer' | 'system'
  source_path: string
  data_type: 'text' | 'date' | 'number' | 'currency' | 'boolean'
  formatter?: string | null
  is_required?: boolean
  default_value?: string | null
  sort_order?: number
}

export interface ContractTemplateFieldRegistryRead {
  token: string
  label: string
  source_scope: 'employee' | 'organization' | 'contract_draft' | 'signer' | 'system'
  source_path: string
  data_type: 'text' | 'date' | 'number' | 'currency' | 'boolean'
  formatter: string | null
  is_required: boolean
  recommended_token: string | null
}

export interface ContractTemplateDocxInspectionItemRead {
  placeholder_key: string
  syntax: string
  is_supported: boolean
  recommended_token: string | null
  label: string | null
  source_scope: 'employee' | 'organization' | 'contract_draft' | 'signer' | 'system' | null
  source_path: string | null
  data_type: 'text' | 'date' | 'number' | 'currency' | 'boolean' | null
  formatter: string | null
  is_required: boolean
}

export interface ContractTemplateHealthRead {
  id: number
  code: string
  name: string
  is_active: boolean
  effective_to: string | null
  storage_path: string | null
  placeholder_count: number
  health_warnings: string[]
}

export interface ContractTemplateDocxInspectionRead {
  template_id: number
  template_code: string
  template_name: string
  storage_path: string
  file_name: string
  styles: string[]
  warnings: string[]
  supported_count: number
  unsupported_count: number
  detected_placeholders: ContractTemplateDocxInspectionItemRead[]
  suggested_rows: ContractTemplatePlaceholderWrite[]
}

export default {
  getContractCategories: (params?: Record<string, unknown>) => api.get<Page<ContractCategoryRead>>('/contract-categories', { params }),
  createContractCategory: (data: ContractCategoryCreate) => api.post<ContractCategoryRead>('/contract-categories', data),
  updateContractCategory: (id: number, data: ContractCategoryUpdate) => api.put<ContractCategoryRead>(`/contract-categories/${id}`, data),
  deleteContractCategory: (id: number) => api.delete<{ message: string }>(`/contract-categories/${id}`),
  lookupContractCategories: (params?: Record<string, unknown>) => api.get<ContractCategoryRead[]>('/lookups/contract-categories', { params }),

  getNationalities: (params?: Record<string, unknown>) => api.get<Page<NationalityRead>>('/nationalities', { params }),
  getNationalityById: (id: number) => api.get<NationalityRead>(`/nationalities/${id}`),
  createNationality: (data: NationalityCreate) => api.post<NationalityRead>('/nationalities', data),
  updateNationality: (id: number, data: NationalityUpdate) => api.put<NationalityRead>(`/nationalities/${id}`, data),
  deleteNationality: (id: number) => api.delete<{ message: string }>(`/nationalities/${id}`),
  lookupNationalities: (params?: Record<string, unknown>) => api.get<NationalityRead[]>('/lookups/nationalities', { params }),

  getEthnicities: (params?: Record<string, unknown>) => api.get<Page<EthnicityRead>>('/ethnicities', { params }),
  getEthnicityById: (id: number) => api.get<EthnicityRead>(`/ethnicities/${id}`),
  createEthnicity: (data: EthnicityCreate) => api.post<EthnicityRead>('/ethnicities', data),
  updateEthnicity: (id: number, data: EthnicityUpdate) => api.put<EthnicityRead>(`/ethnicities/${id}`, data),
  deleteEthnicity: (id: number) => api.delete<{ message: string }>(`/ethnicities/${id}`),
  lookupEthnicities: (params?: Record<string, unknown>) => api.get<EthnicityRead[]>('/lookups/ethnicities', { params }),

  getReligions: (params?: Record<string, unknown>) => api.get<Page<ReligionRead>>('/religions', { params }),
  getReligionById: (id: number) => api.get<ReligionRead>(`/religions/${id}`),
  createReligion: (data: ReligionCreate) => api.post<ReligionRead>('/religions', data),
  updateReligion: (id: number, data: ReligionUpdate) => api.put<ReligionRead>(`/religions/${id}`, data),
  deleteReligion: (id: number) => api.delete<{ message: string }>(`/religions/${id}`),
  lookupReligions: (params?: Record<string, unknown>) => api.get<ReligionRead[]>('/lookups/religions', { params }),

  getBanks: (params?: Record<string, unknown>) => api.get<Page<BankRead>>('/banks', { params }),
  getBankById: (id: number) => api.get<BankRead>(`/banks/${id}`),
  createBank: (data: BankCreate) => api.post<BankRead>('/banks', data),
  updateBank: (id: number, data: BankUpdate) => api.put<BankRead>(`/banks/${id}`, data),
  deleteBank: (id: number) => api.delete<{ message: string }>(`/banks/${id}`),
  lookupBanks: (params?: Record<string, unknown>) => api.get<BankRead[]>('/lookups/banks', { params }),

  getSkills: (params?: Record<string, unknown>) => api.get<Page<SkillRead>>('/skills', { params }),
  getSkillById: (id: number) => api.get<SkillRead>(`/skills/${id}`),
  createSkill: (data: SkillCreate) => api.post<SkillRead>('/skills', data),
  updateSkill: (id: number, data: SkillUpdate) => api.put<SkillRead>(`/skills/${id}`, data),
  deleteSkill: (id: number) => api.delete<{ message: string }>(`/skills/${id}`),
  lookupSkills: (params?: Record<string, unknown>) => api.get<SkillRead[]>('/lookups/skills', { params }),

  getCertificates: (params?: Record<string, unknown>) => api.get<Page<CertificateRead>>('/certificates', { params }),
  createCertificate: (data: CertificateCreate) => api.post<CertificateRead>('/certificates', data),
  updateCertificate: (id: number, data: CertificateUpdate) => api.put<CertificateRead>(`/certificates/${id}`, data),
  deleteCertificate: (id: number) => api.delete<{ message: string }>(`/certificates/${id}`),
  lookupCertificates: (params?: Record<string, unknown>) => api.get<CertificateRead[]>('/lookups/certificates', { params }),

  getLeaveTypes: (params?: Record<string, unknown>) => api.get<Page<LeaveTypeRead>>('/leave-types', { params }),
  createLeaveType: (data: LeaveTypeCreate) => api.post<LeaveTypeRead>('/leave-types', data),
  updateLeaveType: (id: number, data: LeaveTypeUpdate) => api.put<LeaveTypeRead>(`/leave-types/${id}`, data),
  deleteLeaveType: (id: number) => api.delete<{ message: string }>(`/leave-types/${id}`),
  lookupLeaveTypes: (params?: Record<string, unknown>) => api.get<LeaveTypeRead[]>('/lookups/leave-types', { params }),

  getContractTemplates: (params?: Record<string, unknown>) => api.get<Page<ContractTemplateRead>>('/contract-templates', { params }),
  createContractTemplate: (data: ContractTemplateCreate) => api.post<ContractTemplateRead>('/contract-templates', data),
  updateContractTemplate: (id: number, data: ContractTemplateUpdate) => api.put<ContractTemplateRead>(`/contract-templates/${id}`, data),
  deleteContractTemplate: (id: number) => api.delete<{ message: string }>(`/contract-templates/${id}`),
  getContractTemplatePlaceholders: (id: number) => api.get<ContractTemplatePlaceholderRead[]>(`/contract-templates/${id}/placeholders`),
  replaceContractTemplatePlaceholders: (id: number, data: ContractTemplatePlaceholderWrite[]) => api.put<ContractTemplatePlaceholderRead[]>(`/contract-templates/${id}/placeholders`, data),
  inspectContractTemplateDocx: (id: number) => api.post<ContractTemplateDocxInspectionRead>(`/contract-templates/${id}/inspect-docx`),
  lookupContractTemplateFields: () => api.get<ContractTemplateFieldRegistryRead[]>('/lookups/contract-template-fields'),
  getContractTemplateHealthSummary: () => api.get<ContractTemplateHealthRead[]>('/contract-templates/health-summary'),
}
