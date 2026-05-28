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
  bhyt_initial_clinic_code: string | null
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
  bhyt_initial_clinic_code?: string | null
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

export interface InsuranceChangeEventRead {
  id: number
  employee_id: number
  change_type: 'increase' | 'decrease'
  change_reason: string
  ibhxh_reason_code: string
  effective_date: string
  period_year: number
  period_month: number
  employee_name_snapshot: string
  date_of_birth_snapshot: string
  gender_snapshot: string
  nationality_code_snapshot: string
  identity_number_snapshot: string | null
  contract_number_snapshot: string | null
  contract_type_code_snapshot: string | null
  contract_signed_date_snapshot: string | null
  contract_from_snapshot: string | null
  contract_to_snapshot: string | null
  bhxh_code_snapshot: string | null
  basis_amount: number
  allowances_amount: number
  bhyt_clinic_name_snapshot: string | null
  bhyt_clinic_code_snapshot: string | null
  policy_version_code_snapshot: string | null
  employee_rate_total_snapshot: number
  employer_rate_total_snapshot: number
  ethnicity_bhxh_code_snapshot: string | null
  old_status: string | null
  new_status: string
  suggested_declaration_year: number
  suggested_declaration_month: number
  is_manual: boolean
  note: string | null
  created_by_id: number | null
  created_at: string
}

export interface InsuranceChangeEventListPage {
  items: InsuranceChangeEventRead[]
  total: number
  page: number
  page_size: number
}

export interface InsuranceMonthlyChangeSummary {
  period_year: number
  period_month: number
  increase_count: number
  decrease_count: number
  total_basis_increase: number
  total_basis_decrease: number
}

export interface InsuranceChangeEventCreate {
  employee_id: number
  change_type: 'increase' | 'decrease'
  change_reason: string
  effective_date: string
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

  getEffectiveConfig: (asOfDate: string) =>
    api.get<InsuranceEffectiveContributionConfigRead>('/insurance/effective-config', { params: { as_of_date: asOfDate } }),

  // Employee insurance profiles
  listEmployeeProfiles: (filters: InsuranceListFilters) =>
    api.get<EmployeeInsuranceListPage>('/insurance/employees', { params: filters }),

  getEmployeeProfile: (employeeId: number) =>
    api.get<EmployeeInsuranceProfileRead>(`/insurance/employees/${employeeId}`),

  updateEmployeeProfile: (employeeId: number, payload: EmployeeInsuranceProfileUpdate) =>
    api.put<EmployeeInsuranceProfileRead>(`/insurance/employees/${employeeId}`, payload),

  // Change events
  listChangeEvents: (params: {
    employee_id?: number
    change_type?: string
    period_year?: number
    period_month?: number
    page?: number
    page_size?: number
  }) =>
    api.get<InsuranceChangeEventListPage>('/insurance/change-events', { params }),

  getMonthlySummary: (year: number, month: number) =>
    api.get<InsuranceMonthlyChangeSummary>('/insurance/change-events/monthly-summary', {
      params: { year, month },
    }),

  createManualChangeEvent: (payload: InsuranceChangeEventCreate) =>
    api.post<InsuranceChangeEventRead>('/insurance/change-events', payload),

  deleteChangeEvent: (eventId: number) =>
    api.delete(`/insurance/change-events/${eventId}`),

  // Export VNPT D02-TS (Slice 4b)
  exportVnptD02Ts: (year: number, month: number) =>
    api.get(`/insurance/change-events/export/vnpt-d02-ts`, {
      params: { period_year: year, period_month: month },
      responseType: 'blob',
    }),

  // ── Báo cáo biến động (6.4) ────────────────────────────────────────────────

  listReports: (params: { year?: number; status?: string; page?: number; page_size?: number }) =>
    api.get<InsurancePeriodReportListPage>('/insurance/reports', { params }),

  createReport: (payload: InsurancePeriodReportCreate) =>
    api.post<InsurancePeriodReportRead>('/insurance/reports', payload),

  getReport: (reportId: number) =>
    api.get<InsurancePeriodReportDetail>(`/insurance/reports/${reportId}`),

  updateReport: (reportId: number, payload: { note?: string | null }) =>
    api.patch<InsurancePeriodReportRead>(`/insurance/reports/${reportId}`, payload),

  deleteReport: (reportId: number) =>
    api.delete(`/insurance/reports/${reportId}`),

  submitReport: (reportId: number) =>
    api.post<InsurancePeriodReportRead>(`/insurance/reports/${reportId}/submit`),

  approveReport: (reportId: number, payload: { note?: string | null }) =>
    api.post<InsurancePeriodReportRead>(`/insurance/reports/${reportId}/approve`, payload),

  rejectReport: (reportId: number, payload: { review_note: string }) =>
    api.post<InsurancePeriodReportRead>(`/insurance/reports/${reportId}/reject`, payload),

  listLineItems: (reportId: number) =>
    api.get<InsuranceReportLineItemRead[]>(`/insurance/reports/${reportId}/line-items`),

  addLineItem: (reportId: number, payload: { event_id: number; declared_year?: number; declared_month?: number }) =>
    api.post<InsuranceReportLineItemRead>(`/insurance/reports/${reportId}/line-items`, payload),

  updateLineItem: (reportId: number, lineItemId: number, payload: { declared_year: number; declared_month: number; adjustment_note: string }) =>
    api.patch<InsuranceReportLineItemRead>(`/insurance/reports/${reportId}/line-items/${lineItemId}`, payload),

  removeLineItem: (reportId: number, lineItemId: number) =>
    api.delete(`/insurance/reports/${reportId}/line-items/${lineItemId}`),

  exportReportD02Ts: (reportId: number) =>
    api.get(`/insurance/reports/${reportId}/export/d02-ts`, { responseType: 'blob' }),

  // ── Insurance Analytics Endpoints (11.4) ──
  getAnalyticsDashboard: (params: { year: number; month: number; department_id?: number | null }) =>
    api.get<InsuranceDashboardKPI>('/reports/insurance/dashboard', { params }),

  getMonthlyChanges: (params: { year: number; department_id?: number | null }) =>
    api.get<InsuranceMonthlyChangesResponse>('/reports/insurance/monthly-changes', { params }),

  getPayrollFund: (params: { year: number; department_id?: number | null }) =>
    api.get<InsurancePayrollFundResponse>('/reports/insurance/payroll-fund', { params }),

  getNonParticipants: (params: { department_id?: number | null; page?: number; page_size?: number }) =>
    api.get<InsuranceNonParticipantsResponse>('/reports/insurance/non-participants', { params }),

  getDepartmentBreakdown: (params: { year: number; month: number }) =>
    api.get<InsuranceDepartmentBreakdownResponse>('/reports/insurance/by-department', { params }),

  getEmployeeHistory: (params: { employee_id: number; year?: number | null }) =>
    api.get<InsuranceEmployeeHistoryResponse>('/reports/insurance/employee-history', { params }),

  exportAnalyticsUrl: (params: { year: number; month: number; department_id?: number | null }): string => {
    const qs = new URLSearchParams(
      Object.entries(params)
        .filter(([, v]) => v !== null && v !== undefined)
        .map(([k, v]) => [k, String(v)])
    ).toString()
    return `/api/v1/reports/insurance/export?${qs}`
  },
}

// ── Report types (6.4) ────────────────────────────────────────────────────────

export type ReportStatus = 'draft' | 'pending_review' | 'approved' | 'rejected'
export type SubmissionType = 'initial' | 'supplement' | 'correction'

export interface InsurancePeriodReportRead {
  id: number
  period_year: number
  period_month: number
  submission_type: SubmissionType
  status: ReportStatus
  prepared_by_id: number | null
  prepared_by_name: string | null
  prepared_at: string | null
  reviewed_by_id: number | null
  reviewed_by_name: string | null
  reviewed_at: string | null
  review_note: string | null
  note: string | null
  line_item_count: number
  adjusted_count: number
  missing_clinic_code_count: number
  created_at: string
}

export interface InsuranceReportLineItemRead {
  id: number
  report_id: number
  event_id: number
  employee_name: string
  employee_code: string
  bhxh_code: string | null
  change_type: 'increase' | 'decrease'
  change_reason: string
  effective_date: string
  basis_amount: number
  bhyt_clinic_code: string | null
  suggested_year: number
  suggested_month: number
  declared_year: number
  declared_month: number
  is_adjusted: boolean
  adjustment_note: string | null
  sort_order: number
}

export interface InsurancePeriodReportDetail extends InsurancePeriodReportRead {
  line_items: InsuranceReportLineItemRead[]
}

export interface InsurancePeriodReportListPage {
  items: InsurancePeriodReportRead[]
  total: number
  page: number
  page_size: number
}

export interface InsurancePeriodReportCreate {
  period_year: number
  period_month: number
  submission_type: SubmissionType
  note?: string | null
}

// ── Insurance Analytics Types (11.4) ──────────────────────────────────────────

export interface InsuranceDashboardKPI {
  year: number
  month: number
  department_id: number | null
  participating_count: number
  total_active_employees: number
  participation_rate: number
  total_basis_amount: number
  increased_count: number
  decreased_count: number
  net_change: number
}

export interface MonthlyChangePoint {
  month: number
  increased: number
  decreased: number
  net: number
}

export interface InsuranceMonthlyChangesResponse {
  year: number
  department_id: number | null
  data: MonthlyChangePoint[]
}

export interface PayrollFundPoint {
  month: number
  added_amount: number
  removed_amount: number
  snapshot_amount: number | null
}

export interface InsurancePayrollFundResponse {
  year: number
  department_id: number | null
  data: PayrollFundPoint[]
}

export interface NonParticipantRow {
  employee_id: number
  employee_code: string
  full_name: string
  department_name: string
  participation_status: string | null
  status_effective_from: string | null
  status_note: string | null
  company_bhxh_joined_date: string | null
}

export interface InsuranceNonParticipantsResponse {
  items: NonParticipantRow[]
  total: number
  page: number
  page_size: number
}

export interface DepartmentBreakdownRow {
  department_id: number
  department_name: string
  participating_count: number
  total_count: number
  participation_rate: number
  total_basis_amount: number | null
}

export interface InsuranceDepartmentBreakdownResponse {
  year: number
  month: number
  items: DepartmentBreakdownRow[]
}

export interface EmployeeHistoryPoint {
  effective_date: string
  change_type: string
  change_reason: string
  basis_amount: number | null
  participation_status_after: string | null
}

export interface InsuranceEmployeeHistoryResponse {
  employee_id: number
  full_name: string
  current_participation_status: string | null
  current_basis_amount: number | null
  history: EmployeeHistoryPoint[]
}

