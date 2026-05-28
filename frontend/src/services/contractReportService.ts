import api from './api'

export interface ContractSummaryOut {
  total_active: number
  expiring_0_30: number
  expiring_31_60: number
  expiring_61_90: number
  already_expired: number
  renewal_rate: number
  as_of_date: string
}

export type UrgencyTier = 'CRITICAL' | 'WARNING' | 'NOTICE'

export interface ContractExpiringRow {
  contract_id: number
  contract_number: string
  employee_id: number
  employee_code: string
  employee_name: string
  department_id: number | null
  department_name: string | null
  category_name: string
  business_group: string
  effective_from: string
  effective_to: string
  days_remaining: number
  urgency: UrgencyTier
  signed_date: string
  insurance_salary: number | null
}

export interface ContractExpiringPage {
  items: ContractExpiringRow[]
  total: number
  page: number
  page_size: number
  days_ahead: number
}

export interface ContractTypeBreakdown {
  category_id: number
  category_name: string
  business_group: string
  legal_contract_type: string | null
  total: number
  active: number
  expired: number
  terminated: number
  percentage: number
}

export interface ContractByTypeOut {
  items: ContractTypeBreakdown[]
  total_contracts: number
  department_id: number | null
  year: number | null
}

export interface ForecastMonthItem {
  year_month: string
  expiring_count: number
}

export interface ContractForecastOut {
  months: ForecastMonthItem[]
  months_ahead: number
  total_expiring: number
}

export interface ContractHistoryItem {
  contract_id: number
  contract_number: string
  category_name: string
  document_kind: string
  is_appendix: boolean
  parent_contract_id: number | null
  effective_from: string
  effective_to: string | null
  signed_date: string
  status: string
  insurance_salary: number | null
  file_name: string | null
}

export interface ContractHistoryOut {
  employee_id: number
  employee_code: string
  employee_name: string
  items: ContractHistoryItem[]
  total: number
}

async function downloadBlob(url: string, fallbackFilename: string, params?: Record<string, unknown>) {
  const res = await api.get(url, { responseType: 'blob', params })
  const href = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = href

  const disposition = String(res.headers['content-disposition'] || '')
  const match = disposition.match(/filename="?([^"]+)"?/)
  a.download = match?.[1] || fallbackFilename
  a.click()
  URL.revokeObjectURL(href)
}

const contractReportService = {
  getSummary: (params: { department_id?: number | null }) =>
    api.get<ContractSummaryOut>('/reports/contracts/summary', { params }),

  getExpiring: (params: {
    days_ahead?: number
    department_id?: number | null
    keyword?: string
    page?: number
    page_size?: number
  }) => api.get<ContractExpiringPage>('/reports/contracts/expiring', { params }),

  getByType: (params: { department_id?: number | null; year?: number | null }) =>
    api.get<ContractByTypeOut>('/reports/contracts/by-type', { params }),

  getForecast: (params: { months_ahead?: number }) =>
    api.get<ContractForecastOut>('/reports/contracts/expiry-forecast', { params }),

  getHistory: (employee_id: number) =>
    api.get<ContractHistoryOut>('/reports/contracts/history', { params: { employee_id } }),

  exportXlsxUrl: (params: { department_id?: number | null; status?: string; days_ahead?: number | null }): string => {
    const qs = new URLSearchParams(
      Object.entries(params)
        .filter(([, v]) => v !== null && v !== undefined)
        .map(([k, v]) => [k, String(v)])
    ).toString()
    return `/api/v1/reports/contracts/export?${qs}`
  },

  exportXlsx: (params: { department_id?: number | null; status?: string; days_ahead?: number | null }) =>
    downloadBlob('/reports/contracts/export', 'bao_cao_hop_dong.xlsx', params),
}

export default contractReportService
