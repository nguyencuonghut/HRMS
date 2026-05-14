import api from './api'

export interface AdministrativeUnitRead {
  id: number
  code: string
  name: string
  normalized_name: string
  unit_type: string
  official_name: string | null
  province_code: string | null
  is_active: boolean
  effective_from: string | null
  effective_to: string | null
  source_name: string | null
  source_version: string | null
  created_at: string
  updated_at: string | null
}

export interface AdministrativeTreeNode extends AdministrativeUnitRead {
  children: AdministrativeTreeNode[]
}

export interface AdministrativeUnitListPage {
  items: AdministrativeUnitRead[]
  total: number
  page: number
  page_size: number
}

export interface AdministrativeUnitCreate {
  code: string
  name: string
  unit_type: 'province' | 'district' | 'ward'
  official_name?: string | null
  province_code?: string | null
  effective_from?: string | null
  effective_to?: string | null
  source_name?: string | null
  source_version?: string | null
  is_active?: boolean
}

export interface AdministrativeUnitUpdate {
  name?: string
  official_name?: string | null
  province_code?: string | null
  effective_from?: string | null
  effective_to?: string | null
  is_active?: boolean
}

export interface AdministrativeImportRequest {
  system_type: 'old' | 'new'
  json_path?: string | null
  source_name: string
  source_version: string
  file_name?: string | null
  imported_by?: number | null
  mode: 'merge' | 'replace'
}

export interface AdministrativeImportResult {
  batch_id: number
  batch_status: string
  total_rows: number
  success_rows: number
  failed_rows: number
}

export interface AdministrativeImportBatchRead {
  id: number
  source_name: string
  source_version: string
  file_name: string | null
  imported_by: number | null
  imported_at: string
  status: string
  total_rows: number
  success_rows: number
  failed_rows: number
  error_summary: string | null
}

export interface AddressSystemRead {
  code: 'old' | 'new'
  label: string
  levels: number
}

export interface ValidateLocationPathRequest {
  system_type: 'old' | 'new'
  province_unit_id: number
  district_unit_id?: number | null
  ward_unit_id: number
}

export interface ValidateLocationPathResult {
  valid: boolean
  message: string
}

export default {
  getList: (params?: {
    is_active?: boolean | null
    unit_type?: string | null
    province_code?: string | null
    keyword?: string | null
    page?: number
    page_size?: number
  }) => api.get<AdministrativeUnitListPage>('/admin-units', { params }),

  getById: (id: number) =>
    api.get<AdministrativeUnitRead>(`/admin-units/${id}`),

  create: (data: AdministrativeUnitCreate) =>
    api.post<AdministrativeUnitRead>('/admin-units', data),

  update: (id: number, data: AdministrativeUnitUpdate) =>
    api.put<AdministrativeUnitRead>(`/admin-units/${id}`, data),

  delete: (id: number) =>
    api.delete<{ message: string }>(`/admin-units/${id}`),

  getTree: (params: { system_type: 'old' | 'new'; is_active?: boolean | null }) =>
    api.get<AdministrativeTreeNode[]>('/admin-hierarchies/tree', { params }),

  importData: (data: AdministrativeImportRequest) =>
    api.post<AdministrativeImportResult>('/admin-units/import', data),

  listImportBatches: () =>
    api.get<AdministrativeImportBatchRead[]>('/admin-units/import-batches'),

  listAddressSystems: () =>
    api.get<AddressSystemRead[]>('/address-systems'),

  listProvinces: (params: { system_type: 'old' | 'new'; is_active?: boolean | null }) =>
    api.get<AdministrativeUnitRead[]>('/locations/provinces', { params }),

  listChildren: (params: { system_type: 'old' | 'new'; parent_id: number; is_active?: boolean | null }) =>
    api.get<AdministrativeUnitRead[]>('/locations/children', { params }),

  searchLocations: (params: {
    system_type: 'old' | 'new'
    keyword: string
    unit_type?: string | null
    province_code?: string | null
    is_active?: boolean | null
  }) => api.get<AdministrativeUnitRead[]>('/locations/search', { params }),

  validateLocationPath: (data: ValidateLocationPathRequest) =>
    api.post<ValidateLocationPathResult>('/locations/validate-path', data),
}
