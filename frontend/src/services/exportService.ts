import api from './api'

export type ExportReportType =
  | 'dashboard'
  | 'hr-employee-list'
  | 'hr-movement'
  | 'hr-tenure'
  | 'hr-org-structure'
  | 'leaves'
  | 'insurance'
  | 'contracts'
  | 'recruitment'
  | 'probation'
  | 'comprehensive-employee-list'
  | 'salary-summary'
  | 'leave-employee-summary'
  | 'leave-department-summary'
  | 'leave-year-end'

export type ExportFormat = 'xlsx' | 'pdf'
export type ExportStatus = 'pending' | 'processing' | 'done' | 'failed'

export interface ExportJobRequest {
  report_type: ExportReportType
  format: ExportFormat
  filters: Record<string, unknown>
  filename?: string | null
}

export interface ExportJobResponse {
  id: string
  report_type: ExportReportType
  report_type_label: string
  report_type_order: number
  format: ExportFormat
  format_label: string
  format_order: number
  status: ExportStatus
  status_label: string
  status_order: number
  status_severity: string
  filename: string | null
  file_size_bytes: number | null
  row_count: number | null
  error_message: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
  expires_at: string | null
  download_url: string | null
}

export interface ExportJobStatusResponse {
  id: string
  status: ExportStatus
  status_label: string
  status_order: number
  status_severity: string
  progress_pct: number | null
  error_message: string | null
  download_url: string | null
}

export interface ExportHistoryResponse {
  items: ExportJobResponse[]
  total: number
  page: number
  page_size: number
}

export interface ReportTemplateResponse {
  id: number
  name: string
  description: string | null
  report_type: ExportReportType
  report_type_label: string
  report_type_order: number
  format: ExportFormat
  format_label: string
  format_order: number
  filters: Record<string, unknown>
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface ReportTemplateCreate {
  name: string
  description?: string | null
  report_type: ExportReportType
  format: ExportFormat
  filters: Record<string, unknown>
  is_default?: boolean
}

export interface ReportTemplateUpdate {
  name?: string
  description?: string | null
  filters?: Record<string, unknown>
  format?: ExportFormat
  is_default?: boolean
}

export interface ExportReportTypeOption {
  code: ExportReportType
  label: string
  order: number
}

export interface ExportFormatOption {
  code: ExportFormat
  label: string
  order: number
}

export interface ExportStatusOption {
  code: ExportStatus
  label: string
  severity: string
  order: number
}

export interface ExportMetaResponse {
  report_types: ExportReportTypeOption[]
  formats: ExportFormatOption[]
  statuses: ExportStatusOption[]
}

function cleanParams<T extends object>(
  params: T,
): Record<string, string | number | boolean> {
  return Object.fromEntries(
    Object.entries(params).filter(
      ([, value]) => value !== null && value !== undefined && value !== '',
    ),
  ) as Record<string, string | number | boolean>
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function filenameFromDisposition(header?: string, fallback = 'bao_cao.xlsx') {
  if (!header) return fallback
  const match = header.match(/filename="?([^"]+)"?/i)
  return match?.[1] ?? fallback
}

const BASE = '/reports/export'

export default {
  getMeta: () =>
    api.get<ExportMetaResponse>(`${BASE}/meta`),
  createJob: (payload: ExportJobRequest) =>
    api.post<ExportJobResponse>(BASE, payload),

  getStatus: (jobId: string) =>
    api.get<ExportJobStatusResponse>(`${BASE}/${jobId}/status`),

  getHistory: (params: { page?: number; page_size?: number }) =>
    api.get<ExportHistoryResponse>(`${BASE}/history`, {
      params: cleanParams(params),
    }),

  downloadJob: async (jobId: string, fallbackFilename?: string) => {
    const res = await api.get(`${BASE}/${jobId}/download`, {
      responseType: 'blob',
    })
    downloadBlob(
      new Blob([res.data]),
      filenameFromDisposition(res.headers['content-disposition'], fallbackFilename),
    )
  },

  deleteJob: (jobId: string) => api.delete(`${BASE}/${jobId}`),

  listTemplates: () =>
    api.get<ReportTemplateResponse[]>(`${BASE}/templates`),

  createTemplate: (payload: ReportTemplateCreate) =>
    api.post<ReportTemplateResponse>(`${BASE}/templates`, payload),

  updateTemplate: (templateId: number, payload: ReportTemplateUpdate) =>
    api.put<ReportTemplateResponse>(`${BASE}/templates/${templateId}`, payload),

  deleteTemplate: (templateId: number) =>
    api.delete(`${BASE}/templates/${templateId}`),
}
