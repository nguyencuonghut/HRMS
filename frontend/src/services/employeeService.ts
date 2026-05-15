import api from './api'

// ── Types ─────────────────────────────────────────────────────────────────────

export type GenderType = 'male' | 'female' | 'other'
export type StatusType = 'probation' | 'official' | 'long_leave' | 'resigned'
export type AddressType = 'permanent' | 'contact'

export interface EmployeeListItem {
  id: number
  employee_seq: number
  display_code: string
  full_name: string
  date_of_birth: string
  gender: GenderType
  nationality_id: number
  ethnicity_id: number | null
  id_number: string
  phone_number: string | null
  personal_email: string | null
  status: StatusType
  start_date: string
  resigned_date: string | null
  is_active: boolean
  created_at: string
  updated_at: string | null
  id_expires_on: string | null
  passport_expires_on: string | null
  work_permit_expires_on: string | null
}

export interface EmployeeListPage {
  items: EmployeeListItem[]
  total: number
  page: number
  page_size: number
}

export interface EmployeeAddressRead {
  id: number
  employee_id: number
  address_type: AddressType
  new_province_unit_id: number | null
  new_district_unit_id: number | null
  new_ward_unit_id: number | null
  new_address_line: string | null
  old_province_unit_id: number | null
  old_district_unit_id: number | null
  old_ward_unit_id: number | null
  old_address_line: string | null
  full_address_text: string | null
  created_at: string
  updated_at: string | null
  // Enriched unit names
  old_province_name: string | null
  old_district_name: string | null
  old_ward_name: string | null
  new_province_name: string | null
  new_ward_name: string | null
}

export interface EmployeeBankAccountRead {
  id: number
  employee_id: number
  bank_id: number
  account_number: string
  account_name: string
  branch_name: string | null
  is_primary: boolean
  is_active: boolean
  note: string | null
  created_at: string
  updated_at: string | null
}

// ── Job Records (3.2) ─────────────────────────────────────────────────────────

export interface DepartmentBrief {
  id: number
  code: string
  name: string
  display_prefix: string | null
}

export interface JobTitleBrief {
  id: number
  code: string
  name: string
}

export interface JobPositionBrief {
  id: number
  code: string
  name: string
}

export interface JobRecordRead {
  id: number
  employee_id: number
  department_id: number
  department: DepartmentBrief
  job_title_id: number | null
  job_title: JobTitleBrief | null
  job_position_id: number | null
  job_position: JobPositionBrief | null
  probation_start_date: string | null
  probation_end_date: string | null
  official_date: string | null
  effective_from: string
  effective_to: string | null
  is_current: boolean
  notes: string | null
  changed_by: number | null
  created_at: string
  updated_at: string | null
}

export interface JobRecordCreate {
  department_id: number
  job_title_id?: number | null
  job_position_id?: number | null
  probation_start_date?: string | null
  probation_end_date?: string | null
  official_date?: string | null
  effective_from: string
  notes?: string | null
}

export interface JobRecordUpdate {
  department_id?: number | null
  job_title_id?: number | null
  job_position_id?: number | null
  probation_start_date?: string | null
  probation_end_date?: string | null
  official_date?: string | null
  notes?: string | null
}

export interface JobRecordTransfer {
  department_id: number
  job_title_id?: number | null
  job_position_id?: number | null
  effective_from: string
  notes?: string | null
}

// ─────────────────────────────────────────────────────────────────────────────

// ── Relatives (3.3) ──────────────────────────────────────────────────────────

export type RelationshipType =
  'vo' | 'chong' | 'cha' | 'me' | 'con' | 'anh' | 'chi' | 'em' | 'khac'

export const RELATIONSHIP_LABELS: Record<RelationshipType, string> = {
  vo: 'Vợ', chong: 'Chồng', cha: 'Cha', me: 'Mẹ', con: 'Con',
  anh: 'Anh', chi: 'Chị', em: 'Em', khac: 'Khác',
}

export interface EmployeeRelativeRead {
  id: number
  employee_id: number
  full_name: string
  relationship_type: RelationshipType
  date_of_birth: string | null
  occupation: string | null
  phone_number: string | null
  is_emergency_contact: boolean
  note: string | null
  created_at: string
  updated_at: string | null
}

export interface RelativeCreate {
  full_name: string
  relationship_type: RelationshipType
  date_of_birth?: string | null
  occupation?: string | null
  phone_number?: string | null
  is_emergency_contact?: boolean
  note?: string | null
}

export interface RelativeUpdate {
  full_name?: string
  relationship_type?: RelationshipType
  date_of_birth?: string | null
  occupation?: string | null
  phone_number?: string | null
  is_emergency_contact?: boolean
  note?: string | null
}

// ─────────────────────────────────────────────────────────────────────────────

export interface EmployeeRead extends EmployeeListItem {
  last_name: string
  first_name: string
  religion_id: number | null
  id_issued_on: string
  id_issued_by: string
  id_expires_on: string | null
  passport_number: string | null
  passport_issued_on: string | null
  passport_expires_on: string | null
  work_permit_number: string | null
  work_permit_issued_on: string | null
  work_permit_expires_on: string | null
  personal_tax_code: string | null
  bhxh_code: string | null
  avatar_path: string | null
  user_id: number | null
  addresses: EmployeeAddressRead[]
  bank_accounts: EmployeeBankAccountRead[]
  current_job: JobRecordRead | null
  relatives: EmployeeRelativeRead[]
}

export interface EmployeeLookupItem {
  id: number
  employee_seq: number
  display_code: string
  full_name: string
  status: StatusType
}

export interface EmployeeCreate {
  employee_seq?: number | null
  full_name: string
  last_name: string
  first_name: string
  date_of_birth: string
  gender: GenderType
  nationality_id: number
  ethnicity_id?: number | null
  religion_id?: number | null
  id_number: string
  id_issued_on: string
  id_issued_by: string
  id_expires_on?: string | null
  passport_number?: string | null
  passport_issued_on?: string | null
  passport_expires_on?: string | null
  work_permit_number?: string | null
  work_permit_issued_on?: string | null
  work_permit_expires_on?: string | null
  phone_number?: string | null
  personal_email?: string | null
  personal_tax_code?: string | null
  bhxh_code?: string | null
  status?: StatusType
  start_date: string
  resigned_date?: string | null
}

export interface EmployeeUpdate {
  full_name?: string
  last_name?: string
  first_name?: string
  date_of_birth?: string
  gender?: GenderType
  nationality_id?: number
  ethnicity_id?: number | null
  religion_id?: number | null
  id_number?: string
  id_issued_on?: string
  id_issued_by?: string
  id_expires_on?: string | null
  passport_number?: string | null
  passport_issued_on?: string | null
  passport_expires_on?: string | null
  work_permit_number?: string | null
  work_permit_issued_on?: string | null
  work_permit_expires_on?: string | null
  phone_number?: string | null
  personal_email?: string | null
  personal_tax_code?: string | null
  bhxh_code?: string | null
  status?: StatusType
  start_date?: string
  resigned_date?: string | null
  is_active?: boolean
}

export interface EmployeeAddressWrite {
  address_type: AddressType
  new_province_unit_id?: number | null
  new_district_unit_id?: number | null
  new_ward_unit_id?: number | null
  new_address_line?: string | null
  old_province_unit_id?: number | null
  old_district_unit_id?: number | null
  old_ward_unit_id?: number | null
  old_address_line?: string | null
  full_address_text?: string | null
}

export interface EmployeeBankAccountWrite {
  bank_id: number
  account_number: string
  account_name: string
  branch_name?: string | null
  is_primary?: boolean
  note?: string | null
}

// ── Service ───────────────────────────────────────────────────────────────────

const BASE = '/employees'

export default {
  list: (params?: {
    keyword?: string
    status?: string
    is_active?: boolean
    page?: number
    page_size?: number
  }) => api.get<EmployeeListPage>(BASE, { params }),

  get: (id: number) => api.get<EmployeeRead>(`${BASE}/${id}`),

  create: (data: EmployeeCreate) => api.post<EmployeeRead>(BASE, data),

  update: (id: number, data: EmployeeUpdate) => api.put<EmployeeRead>(`${BASE}/${id}`, data),

  deactivate: (id: number) => api.delete(`${BASE}/${id}`),

  lookup: (params?: { keyword?: string; limit?: number }) =>
    api.get<EmployeeLookupItem[]>(`${BASE}/lookup`, { params }),

  // Addresses
  getAddresses: (id: number) => api.get<EmployeeAddressRead[]>(`${BASE}/${id}/addresses`),

  upsertAddress: (id: number, data: EmployeeAddressWrite) =>
    api.put<EmployeeAddressRead>(`${BASE}/${id}/addresses`, data),

  // Bank accounts
  getBankAccounts: (id: number) =>
    api.get<EmployeeBankAccountRead[]>(`${BASE}/${id}/bank-accounts`),

  createBankAccount: (id: number, data: EmployeeBankAccountWrite) =>
    api.post<EmployeeBankAccountRead>(`${BASE}/${id}/bank-accounts`, data),

  updateBankAccount: (id: number, accountId: number, data: EmployeeBankAccountWrite) =>
    api.put<EmployeeBankAccountRead>(`${BASE}/${id}/bank-accounts/${accountId}`, data),

  deleteBankAccount: (id: number, accountId: number) =>
    api.delete(`${BASE}/${id}/bank-accounts/${accountId}`),

  // Job records (3.2)
  getJobRecords: (id: number) =>
    api.get<JobRecordRead[]>(`${BASE}/${id}/job-records`),

  createJobRecord: (id: number, data: JobRecordCreate) =>
    api.post<JobRecordRead>(`${BASE}/${id}/job-records`, data),

  updateCurrentJobRecord: (id: number, data: JobRecordUpdate) =>
    api.put<JobRecordRead>(`${BASE}/${id}/job-records/current`, data),

  transferJobRecord: (id: number, data: JobRecordTransfer) =>
    api.post<JobRecordRead>(`${BASE}/${id}/job-records/transfer`, data),

  // Relatives (3.3)
  getRelatives: (id: number) =>
    api.get<EmployeeRelativeRead[]>(`${BASE}/${id}/relatives`),

  createRelative: (id: number, data: RelativeCreate) =>
    api.post<EmployeeRelativeRead>(`${BASE}/${id}/relatives`, data),

  updateRelative: (id: number, relId: number, data: RelativeUpdate) =>
    api.put<EmployeeRelativeRead>(`${BASE}/${id}/relatives/${relId}`, data),

  deleteRelative: (id: number, relId: number) =>
    api.delete(`${BASE}/${id}/relatives/${relId}`),
}
