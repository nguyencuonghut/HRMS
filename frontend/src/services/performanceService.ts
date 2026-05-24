import api from './api'

// ── Types ─────────────────────────────────────────────────────────────────────

export interface KpiMonthlyRead {
  id: number
  employee_id: number
  employee_code: string
  employee_name: string
  department_name: string | null
  year: number
  month: number
  score: string          // Decimal as string from backend
  note: string | null
  created_by_name: string | null
  created_at: string
  updated_at: string
}

export interface KpiMonthlyCreate {
  employee_id: number
  year: number
  month: number
  score: number
  note?: string | null
}

export interface KpiMonthlyUpdate {
  score?: number | null
  note?: string | null
}

export interface KpiMonthlyListPage {
  items: KpiMonthlyRead[]
  total: number
  page: number
  page_size: number
}

export interface KpiImportResult {
  created: number
  updated: number
  skipped: number
  errors: string[]
}

export interface KpiListParams {
  year?: number | null
  month?: number | null
  department_id?: number | null
  search?: string | null
  page?: number
  page_size?: number
}

// ── API ───────────────────────────────────────────────────────────────────────

const BASE = '/performance/kpi'

export default {
  list: (params: KpiListParams = {}) =>
    api.get<KpiMonthlyListPage>(BASE, { params }),

  get: (id: number) =>
    api.get<KpiMonthlyRead>(`${BASE}/${id}`),

  create: (data: KpiMonthlyCreate) =>
    api.post<KpiMonthlyRead>(BASE, data),

  update: (id: number, data: KpiMonthlyUpdate) =>
    api.put<KpiMonthlyRead>(`${BASE}/${id}`, data),

  delete: (id: number) =>
    api.delete(`${BASE}/${id}`),

  importExcel: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post<KpiImportResult>(`${BASE}/import`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  downloadTemplate: () =>
    api.get(`${BASE}/template`, { responseType: 'blob' }),
}
