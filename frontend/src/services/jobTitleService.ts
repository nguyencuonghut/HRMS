import api from './api'

export interface JobTitleRead {
  id:         number
  code:       string
  name:       string
  level:      number
  is_active:  boolean
  created_at: string
  updated_at: string | null
}

export interface JobTitleCreate {
  code:  string
  name:  string
  level: number
}

export interface JobTitleUpdate {
  name?:      string
  level?:     number
  is_active?: boolean
}

const BASE = '/job-titles'

export default {
  getList: (isActive?: boolean) =>
    api.get<JobTitleRead[]>(BASE, {
      params: isActive !== undefined ? { is_active: isActive } : undefined,
    }),
  create:  (data: JobTitleCreate)              => api.post<JobTitleRead>(BASE, data),
  update:  (id: number, data: JobTitleUpdate)  => api.put<JobTitleRead>(`${BASE}/${id}`, data),
  delete:  (id: number)                        => api.delete<{ message: string }>(`${BASE}/${id}`),
}
