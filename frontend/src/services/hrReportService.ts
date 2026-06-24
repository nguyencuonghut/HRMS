import api from './api'
import type {
  HrEmployeeListParams,
  HrEmployeeListResponse,
  HrExportType,
  HrMovementParams,
  HrMovementReportResponse,
  HrOlderWorkerParams,
  HrOlderWorkerReportResponse,
  HrOrgStructureResponse,
  HrTenureReportResponse,
} from '@/types/hr_report.types'

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

function filenameFromDisposition(header?: string, fallback = 'bao_cao_nhan_su.xlsx') {
  if (!header) return fallback
  const match = header.match(/filename="([^"]+)"/i)
  return match?.[1] ?? fallback
}

const BASE = '/reports/hr'

export default {
  getEmployeeList: (params: HrEmployeeListParams) =>
    api.get<HrEmployeeListResponse>(`${BASE}/employee-list`, {
      params: cleanParams(params),
    }),

  getMovementReport: (params: HrMovementParams) =>
    api.get<HrMovementReportResponse>(`${BASE}/movement`, {
      params: cleanParams(params),
    }),

  getTenureReport: (department_id?: number | null) =>
    api.get<HrTenureReportResponse>(`${BASE}/tenure`, {
      params: cleanParams({ department_id }),
    }),

  getOlderWorkerReport: (params: HrOlderWorkerParams) =>
    api.get<HrOlderWorkerReportResponse>(`${BASE}/older-workers`, {
      params: cleanParams(params),
    }),

  getOrgStructure: (department_id?: number | null) =>
    api.get<HrOrgStructureResponse>(`${BASE}/org-structure`, {
      params: cleanParams({ department_id }),
    }),
  exportReport: async (
    type: HrExportType,
    params: Record<string, unknown>,
  ): Promise<void> => {
    const res = await api.get(`${BASE}/export`, {
      params: cleanParams({ type, ...params }),
      responseType: 'blob',
    })
    const blob = new Blob([res.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    downloadBlob(
      blob,
      filenameFromDisposition(
        res.headers['content-disposition'],
        `bao_cao_nhan_su_${type}.xlsx`,
      ),
    )
  },
}
