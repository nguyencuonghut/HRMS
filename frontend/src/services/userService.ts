import api from '@/services/api'

export interface RoleRef {
  id:   number
  code: string
  name: string
}

export interface UserRead {
  id:            number
  email:         string
  full_name:     string
  is_active:     boolean
  is_superuser:  boolean
  last_login_at: string | null
  created_at:    string
  updated_at:    string | null
  roles:         RoleRef[]
}

export interface UserListItem {
  id:            number
  email:         string
  full_name:     string
  is_active:     boolean
  is_superuser:  boolean
  last_login_at: string | null
  roles:         RoleRef[]
}

export interface UserListResponse {
  items: UserListItem[]
  total: number
  skip:  number
  limit: number
}

export interface UserCreate {
  email:        string
  full_name:    string
  password:     string
  is_active?:   boolean
  is_superuser?: boolean
}

export interface UserUpdate {
  email?:     string
  full_name?: string
  is_active?: boolean
}

export interface RoleAssign {
  role_id:        number
  scope_type?:    string
  department_ids?: number[]
}

const BASE = '/users'

export default {
  list: (params?: { search?: string; is_active?: boolean; skip?: number; limit?: number }) =>
    api.get<UserListResponse>(BASE, { params }),

  get: (id: number) =>
    api.get<UserRead>(`${BASE}/${id}`),

  create: (data: UserCreate) =>
    api.post<UserRead>(BASE, data),

  update: (id: number, data: UserUpdate) =>
    api.put<UserRead>(`${BASE}/${id}`, data),

  deactivate: (id: number) =>
    api.delete(`${BASE}/${id}`),

  resetPassword: (id: number, new_password: string) =>
    api.post(`${BASE}/${id}/reset-password`, { new_password }),

  getRoles: (id: number) =>
    api.get<RoleRef[]>(`${BASE}/${id}/roles`),

  assignRole: (id: number, data: RoleAssign) =>
    api.post<RoleRef>(`${BASE}/${id}/roles`, data),

  removeRole: (id: number, role_id: number) =>
    api.delete(`${BASE}/${id}/roles/${role_id}`),
}
