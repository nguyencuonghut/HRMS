import api from './api'

export interface DepartmentRead {
  id: number
  code: string
  name: string
  short_name: string | null
  display_prefix: string | null
  parent_id: number | null
  dept_type: string
  dept_type_label: string
  order_no: number
  is_active: boolean
  created_at: string
  updated_at: string | null
}

export interface DepartmentTreeNode extends DepartmentRead {
  children: DepartmentTreeNode[]
}

export interface DepartmentCreate {
  code: string
  name: string
  short_name?: string | null
  display_prefix?: string | null
  parent_id?: number | null
  dept_type?: string
  order_no?: number
}

export interface DepartmentUpdate {
  name?: string
  short_name?: string | null
  display_prefix?: string | null
  parent_id?: number | null
  dept_type?: string
  order_no?: number
  is_active?: boolean
}

export default {
  getTree: (is_active?: boolean) =>
    api.get<DepartmentTreeNode[]>('/departments/tree', {
      params: is_active !== undefined ? { is_active } : {},
    }),

  getList: (is_active?: boolean) =>
    api.get<DepartmentRead[]>('/departments', {
      params: is_active !== undefined ? { is_active } : {},
    }),

  create: (data: DepartmentCreate) =>
    api.post<DepartmentRead>('/departments', data),

  update: (id: number, data: DepartmentUpdate) =>
    api.put<DepartmentRead>(`/departments/${id}`, data),

  delete: (id: number) =>
    api.delete<{ message: string }>(`/departments/${id}`),
}
