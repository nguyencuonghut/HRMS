import api from './api'
import employeeService from './employeeService'

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
  // ── Phòng ban ──────────────────────────────────────────────────────────────
  downloadDepartmentTemplate: () =>
    downloadBlob(`${BASE}/departments/template`, 'mau_import_phong_ban.xlsx'),

  importDepartments: (file: File) =>
    uploadXlsx(`${BASE}/departments`, file),

  // ── Chức danh ──────────────────────────────────────────────────────────────
  downloadJobTitleTemplate: () =>
    downloadBlob(`${BASE}/job-titles/template`, 'mau_import_chuc_danh.xlsx'),

  importJobTitles: (file: File) =>
    uploadXlsx(`${BASE}/job-titles`, file),

  // ── Vị trí công việc ───────────────────────────────────────────────────────
  downloadJobPositionTemplate: () =>
    downloadBlob(`${BASE}/job-positions/template`, 'mau_import_vi_tri_cong_viec.xlsx'),

  importJobPositions: (file: File) =>
    uploadXlsx(`${BASE}/job-positions`, file),

  // ── Nhân viên ──────────────────────────────────────────────────────────────
  downloadEmployeeTemplate: () =>
    employeeService.downloadImportTemplate(),

  importEmployees: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return employeeService.importEmployees(form)
  },

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
