import api from '@/services/api'

export interface PermissionRead {
  id:          number
  code:        string
  name:        string
  module:      string
  module_label: string
  module_order: number
  action:      string
  action_label: string
  action_order: number
  description: string | null
}

export interface RoleListItem {
  id:               number
  code:             string
  name:             string
  description:      string | null
  is_system:        boolean
  created_at:       string
  permission_count: number
}

export interface RoleRead {
  id:          number
  code:        string
  name:        string
  description: string | null
  is_system:   boolean
  created_at:  string
  permissions: PermissionRead[]
}

export interface RoleCreate {
  code:         string
  name:         string
  description?: string
}

export interface RoleUpdate {
  name?:        string
  description?: string
}

const BASE = '/roles'

export default {
  list: () =>
    api.get<RoleListItem[]>(BASE),

  get: (id: number) =>
    api.get<RoleRead>(`${BASE}/${id}`),

  create: (data: RoleCreate) =>
    api.post<RoleRead>(BASE, data),

  update: (id: number, data: RoleUpdate) =>
    api.put<RoleRead>(`${BASE}/${id}`, data),

  delete: (id: number) =>
    api.delete(`${BASE}/${id}`),

  getPermissions: (id: number) =>
    api.get<PermissionRead[]>(`${BASE}/${id}/permissions`),

  replacePermissions: (id: number, permission_ids: number[]) =>
    api.put<PermissionRead[]>(`${BASE}/${id}/permissions`, { permission_ids }),

  listAllPermissions: () =>
    api.get<PermissionRead[]>(`${BASE}/permissions`),
}
