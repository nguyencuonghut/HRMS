import axios from 'axios'

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

const BASE = '/api/v1/job-titles'

export default {
  getList: (isActive?: boolean) =>
    axios.get<JobTitleRead[]>(BASE, {
      params: isActive !== undefined ? { is_active: isActive } : undefined,
    }),
  create:  (data: JobTitleCreate)              => axios.post<JobTitleRead>(BASE, data),
  update:  (id: number, data: JobTitleUpdate)  => axios.put<JobTitleRead>(`${BASE}/${id}`, data),
  delete:  (id: number)                        => axios.delete<{ message: string }>(`${BASE}/${id}`),
}
