import api from './api'

export interface BhxhExportParams {
  year: number
  month: number
  department_id?: number | null
}

async function downloadBhxhBlob(url: string, filename: string, params: Record<string, unknown>) {
  const cleaned = Object.fromEntries(Object.entries(params).filter(([, v]) => v != null))
  const res = await api.get(url, { params: cleaned, responseType: 'blob' })
  const href = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = href
  a.download = filename
  a.click()
  URL.revokeObjectURL(href)
}

export default {
  exportD02Lt: (params: BhxhExportParams) =>
    downloadBhxhBlob(
      '/exports/bhxh/d02-lt',
      `D02-LT_T${String(params.month).padStart(2, '0')}_${params.year}.xlsx`,
      params as unknown as Record<string, unknown>,
    ),
  exportD03Ts: (params: BhxhExportParams) =>
    downloadBhxhBlob(
      '/exports/bhxh/d03-ts',
      `D03-TS_T${String(params.month).padStart(2, '0')}_${params.year}.xlsx`,
      params as unknown as Record<string, unknown>,
    ),
}
