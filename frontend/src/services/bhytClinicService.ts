import api from './api'

export interface BhytClinicRead {
  id: number
  code: string
  name: string
  province_code: string | null
}

export interface BhytClinicCreate {
  code: string
  name: string
  province_code?: string | null
}

export interface BhytClinicUpdate {
  name?: string
  province_code?: string | null
}

export interface BhytClinicListPage {
  items: BhytClinicRead[]
  total: number
  page: number
  page_size: number
}

export interface BhytClinicListFilters {
  keyword?: string | null
  province_code?: string | null
  page?: number
  page_size?: number
}

export default {
  list: (filters: BhytClinicListFilters) =>
    api.get<BhytClinicListPage>('/bhyt-clinics', { params: filters }),

  create: (payload: BhytClinicCreate) =>
    api.post<BhytClinicRead>('/bhyt-clinics', payload),

  update: (id: number, payload: BhytClinicUpdate) =>
    api.put<BhytClinicRead>(`/bhyt-clinics/${id}`, payload),

  delete: (id: number) =>
    api.delete(`/bhyt-clinics/${id}`),
}
