import api from './api'

export interface LeaveRecordRead {
  id: number
  employee_id: number
  employee_code: string
  employee_name: string
  leave_type_id: number
  leave_type_code: string
  leave_type_name: string
  entitlement_id: number | null
  start_date: string
  end_date: string
  start_half: 'AM' | 'PM' | null
  end_half: 'AM' | 'PM' | null
  total_days: number
  reason: string | null
  status: 'active' | 'cancelled'
  cancel_reason: string | null
  note: string | null
  created_by_id: number | null
  created_at: string
  updated_at: string | null
  remaining_days_after: number | null
  warning: string | null
}

export interface LeaveRecordCreate {
  employee_id: number
  leave_type_id: number
  start_date: string
  end_date: string
  start_half?: 'AM' | 'PM' | null
  end_half?: 'AM' | 'PM' | null
  reason?: string | null
  note?: string | null
}

export interface LeaveRecordUpdate {
  start_date?: string
  end_date?: string
  start_half?: 'AM' | 'PM' | null
  end_half?: 'AM' | 'PM' | null
  reason?: string | null
  note?: string | null
}

export interface LeaveRecordListPage {
  items: LeaveRecordRead[]
  total: number
  page: number
  page_size: number
}

export default {
  list: (params?: Record<string, unknown>) =>
    api.get<LeaveRecordListPage>('/leave-records', { params }),
  get: (id: number) =>
    api.get<LeaveRecordRead>(`/leave-records/${id}`),
  create: (data: LeaveRecordCreate) =>
    api.post<LeaveRecordRead>('/leave-records', data),
  update: (id: number, data: LeaveRecordUpdate) =>
    api.put<LeaveRecordRead>(`/leave-records/${id}`, data),
  cancel: (id: number, cancelReason?: string | null) =>
    api.post<LeaveRecordRead>(`/leave-records/${id}/cancel`, { cancel_reason: cancelReason ?? null }),
  remove: (id: number) =>
    api.delete<void>(`/leave-records/${id}`),
}
