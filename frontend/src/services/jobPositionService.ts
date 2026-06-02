import api from './api'

export interface JobPositionListItem {
  id:                 number
  code:               string
  name:               string
  department_id:      number
  department_name:    string
  job_title_id:       number | null
  job_title_name:     string | null
  bhxh_allowance:     number
  non_bhxh_allowance: number
  is_active:          boolean
  created_at:         string
  updated_at:         string | null
}

export interface JobPositionRead {
  id:                 number
  code:               string
  name:               string
  department_id:      number
  job_title_id:       number | null
  default_grade:      number
  bhxh_allowance:     number
  non_bhxh_allowance: number
  description:        string | null
  requirements:       string | null
  is_active:          boolean
  created_at:         string
  updated_at:         string | null
}

export interface JobPositionCreate {
  code:               string
  name:               string
  department_id:      number
  job_title_id?:      number | null
  default_grade?:     number
  bhxh_allowance?:    number
  non_bhxh_allowance?: number
  description?:       string | null
  requirements?:      string | null
}

export interface JobPositionUpdate {
  name?:               string
  department_id?:      number
  job_title_id?:       number | null
  default_grade?:      number
  bhxh_allowance?:     number
  non_bhxh_allowance?: number
  description?:        string | null
  requirements?:       string | null
  is_active?:          boolean
}

const BASE = '/job-positions'

export default {
  getList: (params?: { department_id?: number; is_active?: boolean; search?: string }) =>
    api.get<JobPositionListItem[]>(BASE, { params }),
  getById: (id: number) =>
    api.get<JobPositionRead>(`${BASE}/${id}`),
  create:  (data: JobPositionCreate) =>
    api.post<JobPositionRead>(BASE, data),
  update:  (id: number, data: JobPositionUpdate) =>
    api.put<JobPositionRead>(`${BASE}/${id}`, data),
  delete:  (id: number) =>
    api.delete<{ message: string }>(`${BASE}/${id}`),
}
