import api from './api'

export interface ImportRowError {
  row: number
  column: string
  message: string
}

export interface ImportResult {
  total: number
  success: number
  failed: number
  errors: ImportRowError[]
  created_ids: number[]
}

const BASE = '/imports'

async function downloadBlob(url: string, filename: string) {
  const res = await api.get(url, { responseType: 'blob' })
  const href = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = href
  a.download = filename
  a.click()
  URL.revokeObjectURL(href)
}

function uploadXlsx(url: string, file: File) {
  const form = new FormData()
  form.append('file', file)
  return api.post<ImportResult>(url, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export default {
  // ── Hợp đồng ──────────────────────────────────────────────────────────────
  downloadContractTemplate: () =>
    downloadBlob(`${BASE}/contracts/template`, 'mau_import_hop_dong.xlsx'),

  importContracts: (file: File) =>
    uploadXlsx(`${BASE}/contracts`, file),

  // ── Nghỉ phép ─────────────────────────────────────────────────────────────
  downloadLeaveRecordTemplate: () =>
    downloadBlob(`${BASE}/leave-records/template`, 'mau_import_nghi_phep.xlsx'),

  importLeaveRecords: (file: File) =>
    uploadXlsx(`${BASE}/leave-records`, file),

  // ── Bảo hiểm ──────────────────────────────────────────────────────────────
  downloadInsuranceTemplate: () =>
    downloadBlob(`${BASE}/insurance/template`, 'mau_import_bao_hiem.xlsx'),

  importInsurance: (file: File) =>
    uploadXlsx(`${BASE}/insurance`, file),
}
