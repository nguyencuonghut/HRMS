import api from './api'

export const DISCIPLINE_FORMS = [
  { value: 'khien_trach',        label: 'Khiển trách' },
  { value: 'keo_dai_nang_luong', label: 'Kéo dài thời hạn nâng lương' },
  { value: 'cach_chuc',          label: 'Cách chức' },
  { value: 'sa_thai',            label: 'Sa thải' },
] as const

export type DisciplineFormValue = typeof DISCIPLINE_FORMS[number]['value']

export interface DisciplineRead {
  id: number
  employee_id: number
  employee_code: string
  employee_name: string
  department_name: string | null
  discipline_form: DisciplineFormValue
  discipline_form_label: string
  violation_date: string
  effective_date: string
  end_date: string | null
  extended_months: number | null
  title: string
  description: string | null
  decision_number: string | null
  issued_by: string | null
  note: string | null
  has_file: boolean
  file_name: string | null
  file_size: number | null
  created_by_id: number | null
  created_by_name: string | null
  created_at: string
  updated_at: string | null
}

export interface DisciplineCreate {
  employee_id: number
  discipline_form: DisciplineFormValue
  violation_date: string
  effective_date: string
  extended_months?: number | null
  title: string
  description?: string | null
  decision_number?: string | null
  issued_by?: string | null
  note?: string | null
}

export interface DisciplineUpdate {
  discipline_form?: DisciplineFormValue
  violation_date?: string
  effective_date?: string
  extended_months?: number | null
  title?: string
  description?: string | null
  decision_number?: string | null
  issued_by?: string | null
  note?: string | null
}

export interface DisciplineListPage {
  items: DisciplineRead[]
  total: number
  page: number
  page_size: number
}

function buildFormData(data: DisciplineCreate | DisciplineUpdate, file?: File | null): FormData {
  const fd = new FormData()
  fd.append('body', JSON.stringify(data))
  if (file) fd.append('file', file)
  return fd
}

export default {
  list: (params?: Record<string, unknown>) =>
    api.get<DisciplineListPage>('/disciplines', { params }),

  get: (id: number) =>
    api.get<DisciplineRead>(`/disciplines/${id}`),

  create: (data: DisciplineCreate, file?: File | null) =>
    api.post<DisciplineRead>('/disciplines', buildFormData(data, file), {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  update: (id: number, data: DisciplineUpdate, file?: File | null) =>
    api.put<DisciplineRead>(`/disciplines/${id}`, buildFormData(data, file), {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  delete: (id: number) =>
    api.delete(`/disciplines/${id}`),

  downloadFile: (id: number) =>
    api.get(`/disciplines/${id}/download`, { responseType: 'blob' }),

  getEmployeeHistory: (employeeId: number) =>
    api.get<DisciplineRead[]>(`/employees/${employeeId}/disciplines`),
}
