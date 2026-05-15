import api from './api'

export interface EducationLevelRead {
  id: number
  code: string
  name: string
  normalized_name: string
  rank_no: number
  is_active: boolean
  created_at: string
  updated_at: string | null
}

export interface EducationLevelListPage {
  items: EducationLevelRead[]
  total: number
  page: number
  page_size: number
}

export interface EducationLevelCreate {
  code: string
  name: string
  rank_no: number
  is_active?: boolean
}

export interface EducationLevelUpdate {
  name?: string
  rank_no?: number
  is_active?: boolean
}

export interface EducationalInstitutionRead {
  id: number
  code: string | null
  name: string
  normalized_name: string
  short_name: string | null
  institution_type: string | null
  country_code: string | null
  province_code: string | null
  is_active: boolean
  created_at: string
  updated_at: string | null
}

export interface EducationalInstitutionListPage {
  items: EducationalInstitutionRead[]
  total: number
  page: number
  page_size: number
}

export interface EducationalInstitutionCreate {
  code?: string | null
  name: string
  short_name?: string | null
  institution_type?: 'university' | 'college' | 'vocational' | 'high_school' | 'other' | null
  country_code?: string | null
  province_code?: string | null
  is_active?: boolean
}

export interface EducationalInstitutionUpdate {
  name?: string
  short_name?: string | null
  institution_type?: 'university' | 'college' | 'vocational' | 'high_school' | 'other' | null
  country_code?: string | null
  province_code?: string | null
  is_active?: boolean
}

export interface EducationMajorRead {
  id: number
  code: string | null
  name: string
  normalized_name: string
  major_group: string | null
  is_active: boolean
  created_at: string
  updated_at: string | null
}

export interface EducationMajorListPage {
  items: EducationMajorRead[]
  total: number
  page: number
  page_size: number
}

export interface EducationMajorCreate {
  code?: string | null
  name: string
  major_group?: string | null
  is_active?: boolean
}

export interface EducationMajorUpdate {
  name?: string
  major_group?: string | null
  is_active?: boolean
}

export default {
  getEducationLevels: (params?: {
    keyword?: string | null
    is_active?: boolean | null
    page?: number
    page_size?: number
  }) => api.get<EducationLevelListPage>('/education-levels', { params }),

  getEducationLevelById: (id: number) =>
    api.get<EducationLevelRead>(`/education-levels/${id}`),

  createEducationLevel: (data: EducationLevelCreate) =>
    api.post<EducationLevelRead>('/education-levels', data),

  updateEducationLevel: (id: number, data: EducationLevelUpdate) =>
    api.put<EducationLevelRead>(`/education-levels/${id}`, data),

  deleteEducationLevel: (id: number) =>
    api.delete<{ message: string }>(`/education-levels/${id}`),

  getEducationalInstitutions: (params?: {
    keyword?: string | null
    institution_type?: string | null
    country_code?: string | null
    is_active?: boolean | null
    page?: number
    page_size?: number
  }) => api.get<EducationalInstitutionListPage>('/educational-institutions', { params }),

  getEducationalInstitutionById: (id: number) =>
    api.get<EducationalInstitutionRead>(`/educational-institutions/${id}`),

  createEducationalInstitution: (data: EducationalInstitutionCreate) =>
    api.post<EducationalInstitutionRead>('/educational-institutions', data),

  updateEducationalInstitution: (id: number, data: EducationalInstitutionUpdate) =>
    api.put<EducationalInstitutionRead>(`/educational-institutions/${id}`, data),

  deleteEducationalInstitution: (id: number) =>
    api.delete<{ message: string }>(`/educational-institutions/${id}`),

  getEducationMajors: (params?: {
    keyword?: string | null
    major_group?: string | null
    is_active?: boolean | null
    page?: number
    page_size?: number
  }) => api.get<EducationMajorListPage>('/education-majors', { params }),

  getEducationMajorById: (id: number) =>
    api.get<EducationMajorRead>(`/education-majors/${id}`),

  createEducationMajor: (data: EducationMajorCreate) =>
    api.post<EducationMajorRead>('/education-majors', data),

  updateEducationMajor: (id: number, data: EducationMajorUpdate) =>
    api.put<EducationMajorRead>(`/education-majors/${id}`, data),

  deleteEducationMajor: (id: number) =>
    api.delete<{ message: string }>(`/education-majors/${id}`),

  lookupEducationLevels: (params?: {
    keyword?: string | null
    limit?: number
  }) => api.get<EducationLevelRead[]>('/lookups/education-levels', { params }),

  lookupEducationalInstitutions: (params?: {
    keyword?: string | null
    institution_type?: string | null
    country_code?: string | null
    limit?: number
  }) => api.get<EducationalInstitutionRead[]>('/lookups/educational-institutions', { params }),

  lookupEducationMajors: (params?: {
    keyword?: string | null
    major_group?: string | null
    limit?: number
  }) => api.get<EducationMajorRead[]>('/lookups/education-majors', { params }),
}
