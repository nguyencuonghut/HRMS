import api from './api'
import { toDepartmentSelectOptions } from '@/utils/departmentOptions'

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

export interface DepartmentOption extends DepartmentRead {
  plain_name: string
  depth: number
}

export interface DepartmentTreeNode extends DepartmentRead {
  children: DepartmentTreeNode[]
}

export interface DepartmentBrief {
  id: number
  code: string
  name: string
  parent_id: number | null
  dept_type: string
  dept_type_label: string
  is_active: boolean
}

export interface DepartmentDetailSummary {
  direct_headcount: number
  total_headcount: number
  direct_child_count: number
  job_position_count: number
}

export interface DepartmentDirectEmployeeItem {
  id: number
  display_code: string
  full_name: string
  status: string
  start_date: string
  job_title_name: string | null
  job_position_name: string | null
}

export interface DepartmentDetailRead {
  department: DepartmentRead
  parent: DepartmentBrief | null
  summary: DepartmentDetailSummary
  direct_employees: DepartmentDirectEmployeeItem[]
}

export interface DepartmentHeadEmployeeRead {
  id: number
  display_code: string
  full_name: string
  status: string
  current_department_id: number | null
  current_department_name: string | null
  current_job_position_id: number | null
  current_job_position_name: string | null
  current_job_title_id: number | null
  current_job_title_name: string | null
  is_cross_department_assignment: boolean
}

export interface DepartmentHeadRead {
  id: number
  department_id: number
  employee_id: number
  head_role_label: string | null
  display_position_label: string
  effective_from: string
  effective_to: string | null
  is_current: boolean
  employee: DepartmentHeadEmployeeRead
}

export interface DepartmentHeadUpsert {
  employee_id: number
  head_role_label?: string | null
  effective_from: string
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
    api
      .get<DepartmentRead[]>('/departments', {
        params: is_active !== undefined ? { is_active } : {},
      })
      .then((response) => ({
        ...response,
        data: toDepartmentSelectOptions(response.data) as DepartmentOption[],
      })),

  getDetail: (id: number) =>
    api.get<DepartmentDetailRead>(`/departments/${id}/detail`),

  getHead: (id: number) =>
    api.get<DepartmentHeadRead | null>(`/departments/${id}/head`),

  upsertHead: (id: number, data: DepartmentHeadUpsert) =>
    api.put<DepartmentHeadRead>(`/departments/${id}/head`, data),

  deleteHead: (id: number) =>
    api.delete<{ message: string }>(`/departments/${id}/head`),

  create: (data: DepartmentCreate) =>
    api.post<DepartmentRead>('/departments', data),

  update: (id: number, data: DepartmentUpdate) =>
    api.put<DepartmentRead>(`/departments/${id}`, data),

  delete: (id: number) =>
    api.delete<{ message: string }>(`/departments/${id}`),
}
