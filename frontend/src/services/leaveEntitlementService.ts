import api from './api'

export interface LeaveEntitlementRead {
  id: number
  employee_id: number
  employee_code: string
  employee_name: string
  leave_type_id: number
  leave_type_code: string
  leave_type_name: string
  year: number
  allocated_days: number
  carryover_days: number
  carryover_expires: string | null
  used_days: number
  remaining_days: number
  note: string | null
  created_by_id: number | null
  created_at: string
  updated_at: string | null
}

export interface LeaveEntitlementCreate {
  employee_id: number
  leave_type_id: number
  year: number
  allocated_days: number
  carryover_days?: number
  carryover_expires?: string | null
  note?: string | null
}

export interface LeaveEntitlementUpdate {
  allocated_days?: number
  carryover_days?: number
  carryover_expires?: string | null
  note?: string | null
}

export interface LeaveEntitlementListPage {
  items: LeaveEntitlementRead[]
  total: number
  page: number
  page_size: number
}

export interface BulkAllocateRequest {
  year: number
  leave_type_codes?: string[]
  employee_ids?: number[]
  overwrite?: boolean
}

export interface BulkAllocateResult {
  year: number
  allocated: number
  skipped: number
  errors: string[]
}

export default {
  list: (params?: Record<string, unknown>) =>
    api.get<LeaveEntitlementListPage>('/leave-entitlements', { params }),

  get: (id: number) =>
    api.get<LeaveEntitlementRead>(`/leave-entitlements/${id}`),

  create: (data: LeaveEntitlementCreate) =>
    api.post<LeaveEntitlementRead>('/leave-entitlements', data),

  update: (id: number, data: LeaveEntitlementUpdate) =>
    api.put<LeaveEntitlementRead>(`/leave-entitlements/${id}`, data),

  remove: (id: number) =>
    api.delete<void>(`/leave-entitlements/${id}`),

  bulkAllocate: (data: BulkAllocateRequest) =>
    api.post<BulkAllocateResult>('/leave-entitlements/bulk-allocate', data),
}
