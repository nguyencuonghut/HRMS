import api from './api'

export interface RewardTypeRead {
  id: number
  code: string
  name: string
  is_monetary: boolean
  sort_order: number
  is_active: boolean
}

export interface RewardTypeCreate {
  code: string
  name: string
  is_monetary?: boolean
  sort_order?: number
}

export interface RewardTypeUpdate {
  name?: string
  is_monetary?: boolean
  sort_order?: number
  is_active?: boolean
}

export interface RewardRead {
  id: number
  employee_id: number
  employee_code: string
  employee_name: string
  department_name: string | null
  reward_type_id: number
  reward_type_name: string
  reward_type_is_monetary: boolean
  title: string
  description: string | null
  reward_date: string
  decision_number: string | null
  issued_by: string | null
  value: string | null
  note: string | null
  has_file: boolean
  file_name: string | null
  file_size: number | null
  source_review_id: number | null
  created_by_id: number | null
  created_by_name: string | null
  created_at: string
  updated_at: string | null
}

export interface RewardCreate {
  employee_id: number
  reward_type_id: number
  title: string
  description?: string | null
  reward_date: string
  decision_number?: string | null
  issued_by?: string | null
  value?: number | null
  note?: string | null
}

export interface RewardUpdate {
  reward_type_id?: number
  title?: string
  description?: string | null
  reward_date?: string
  decision_number?: string | null
  issued_by?: string | null
  value?: number | null
  note?: string | null
}

export interface RewardListPage {
  items: RewardRead[]
  total: number
  page: number
  page_size: number
}

function buildFormData(data: RewardCreate | RewardUpdate, file?: File | null): FormData {
  const fd = new FormData()
  fd.append('body', JSON.stringify(data))
  if (file) fd.append('file', file)
  return fd
}

export default {
  // ── Catalog ───────────────────────────────────────────────────────────────
  listTypes: (includeInactive = false) =>
    api.get<RewardTypeRead[]>('/rewards/types', { params: { include_inactive: includeInactive } }),

  createType: (data: RewardTypeCreate) =>
    api.post<RewardTypeRead>('/rewards/types', data),

  updateType: (id: number, data: RewardTypeUpdate) =>
    api.put<RewardTypeRead>(`/rewards/types/${id}`, data),

  deleteType: (id: number) =>
    api.delete(`/rewards/types/${id}`),

  // ── Rewards ───────────────────────────────────────────────────────────────
  list: (params?: Record<string, unknown>) =>
    api.get<RewardListPage>('/rewards', { params }),

  get: (id: number) =>
    api.get<RewardRead>(`/rewards/${id}`),

  create: (data: RewardCreate, file?: File | null) =>
    api.post<RewardRead>('/rewards', buildFormData(data, file), {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  update: (id: number, data: RewardUpdate, file?: File | null) =>
    api.put<RewardRead>(`/rewards/${id}`, buildFormData(data, file), {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  delete: (id: number) =>
    api.delete(`/rewards/${id}`),

  downloadFile: (id: number) =>
    api.get(`/rewards/${id}/download`, { responseType: 'blob' }),

  // ── Employee history ──────────────────────────────────────────────────────
  getEmployeeHistory: (employeeId: number) =>
    api.get<RewardRead[]>(`/employees/${employeeId}/rewards`),
}
