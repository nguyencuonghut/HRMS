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
  format: ExportFormat
  status: ExportStatus
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
  format: ExportFormat
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
