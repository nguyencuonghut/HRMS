export interface HrEmployeeListParams {
  page: number
  page_size: number
  department_id?: number | null
  status?: string | null
  gender?: string | null
  document_kind?: string | null
  start_date_from?: string | null
  start_date_to?: string | null
  tenure_min?: number | null
  tenure_max?: number | null
}

export interface HrEmployeeListItem {
  id: number
  employee_code: string | null
  full_name: string
  gender: string
  date_of_birth: string | null
  status: string
  start_date: string
  resigned_date: string | null
  is_active: boolean
  department_id: number | null
  department_name: string | null
  job_title_name: string | null
  contract_category_name: string | null
  document_kind: string | null
  tenure_years: number
}

export interface HrEmployeeListResponse {
  items: HrEmployeeListItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export type HrMovementGroupBy = 'month' | 'quarter' | 'year'

export interface HrMovementParams {
  start_date: string
  end_date: string
  group_by?: HrMovementGroupBy
  department_id?: number | null
}

export interface HrMovementPeriodRow {
  period_label: string
  period_start: string
  period_end: string
  hired_count: number
  resigned_count: number
  transfer_count: number
  net_change: number
}

export interface HrMovementReportResponse {
  group_by: HrMovementGroupBy
  start_date: string
  end_date: string
  rows: HrMovementPeriodRow[]
  total_hired: number
  total_resigned: number
  total_transfers: number
}

export interface HrTenureGroupDetail {
  id: number
  full_name: string
  department_name: string | null
  start_date: string
  tenure_years: number
}

export interface HrTenureGroup {
  group_key: string
  group_label: string
  headcount: number
  percentage: number
  avg_tenure_years: number
  employees: HrTenureGroupDetail[]
}

export interface HrTenureReportResponse {
  department_id: number | null
  department_name: string | null
  total_active: number
  avg_tenure_years: number
  groups: HrTenureGroup[]
}

export interface HrJobTitleHeadcount {
  job_title_id: number | null
  job_title_name: string | null
  job_level: number | null
  headcount: number
}

export interface HrDepartmentNode {
  department_id: number
  department_name: string
  parent_id: number | null
  total_headcount: number
  direct_headcount: number
  by_job_title: HrJobTitleHeadcount[]
  children: HrDepartmentNode[]
}

export interface HrOrgStructureResponse {
  total_headcount: number
  department_count: number
  tree: HrDepartmentNode[]
}

export type HrExportType =
  | 'employee-list'
  | 'movement'
  | 'older-worker'
  | 'tenure'
  | 'org-structure'

export interface HrOlderWorkerParams {
  year: number
  month: number
  department_id?: number | null
  gender?: 'male' | 'female' | null
}

export interface HrOlderWorkerItem {
  id: number
  employee_code: string | null
  full_name: string
  gender: string
  date_of_birth: string
  start_date: string
  department_id: number | null
  department_name: string | null
  job_title_name: string | null
  retirement_age_years: number
  retirement_age_months: number
  retirement_date: string
  age_years: number
  age_months: number
  months_beyond_retirement: number
}

export interface HrOlderWorkerSummary {
  total: number
  male_count: number
  female_count: number
}

export interface HrOlderWorkerReportResponse {
  year: number
  month: number
  as_of_date: string
  department_id: number | null
  department_name: string | null
  gender: string | null
  policy_id: number
  policy_name: string
  legal_basis_summary: string | null
  male_threshold_label: string | null
  female_threshold_label: string | null
  summary: HrOlderWorkerSummary
  items: HrOlderWorkerItem[]
}

export interface HrRetirementAgeThresholdInput {
  gender: 'male' | 'female'
  applicable_year: number
  age_years: number
  age_months: number
}

export interface HrRetirementAgeThresholdRead extends HrRetirementAgeThresholdInput {
  id: number
}

export interface HrRetirementAgePolicyRead {
  id: number
  name: string
  legal_basis_summary: string | null
  effective_from: string
  effective_to: string | null
  note: string | null
  thresholds: HrRetirementAgeThresholdRead[]
  created_at: string
  updated_at: string | null
}

export interface HrRetirementAgePoliciesRead {
  current: HrRetirementAgePolicyRead | null
  history: HrRetirementAgePolicyRead[]
}

export interface HrRetirementAgePolicyCreate {
  name: string
  legal_basis_summary?: string | null
  effective_from: string
  note?: string | null
  thresholds: HrRetirementAgeThresholdInput[]
}

export interface HrRetirementAgePolicyUpdate {
  name?: string | null
  legal_basis_summary?: string | null
  note?: string | null
  thresholds?: HrRetirementAgeThresholdInput[] | null
}
