import api from './api'

export interface NotifTemplate {
  code: string
  event_type: string
  event_type_label: string
  event_type_order: number
  name: string
  subject: string
  body_html: string
  is_active: boolean
  is_system: boolean
  days_before: number | null
  recipient_type: string
  merge_fields: string[]
}

export interface NotifConfig {
  event_type: string
  event_type_label: string
  event_type_order: number
  is_enabled: boolean
  days_before: number[] | null
  extra_recipients: string[] | null
}

export interface EmailLogItem {
  id: number
  template_code: string | null
  event_type: string
  event_type_label: string
  event_type_order: number
  employee_id: number | null
  recipient_email: string
  recipient_name: string | null
  subject: string | null
  status: string
  error_message: string | null
  sent_at: string
}

export interface EmailLogListResponse {
  items: EmailLogItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface NotificationEventOption {
  code: string
  label: string
  order: number
}

export interface NotificationStatusOption {
  code: string
  label: string
  severity: string
  order: number
}

export interface NotificationMetaResponse {
  event_types: NotificationEventOption[]
  statuses: NotificationStatusOption[]
}

const BASE = '/notifications'

export default {
  getMeta: () => api.get<NotificationMetaResponse>(`${BASE}/meta`),
  getTemplates: () => api.get<NotifTemplate[]>(`${BASE}/templates`),
  getTemplate: (code: string) => api.get<NotifTemplate>(`${BASE}/templates/${code}`),
  updateTemplate: (code: string, data: Partial<Pick<NotifTemplate, 'subject' | 'body_html' | 'is_active'>>) =>
    api.put<NotifTemplate>(`${BASE}/templates/${code}`, data),
  previewTemplate: (code: string, sampleData: Record<string, string> = {}) =>
    api.post<{ html: string }>(`${BASE}/templates/${code}/preview`, { sample_data: sampleData }),
  getConfig: () => api.get<NotifConfig[]>(`${BASE}/config`),
  updateConfig: (eventType: string, data: { is_enabled?: boolean; days_before?: number[] | null; extra_recipients?: string[] | null }) =>
    api.put<NotifConfig>(`${BASE}/config/${eventType}`, data),
  getLogs: (params: { event_type?: string; status?: string; from_date?: string; to_date?: string; page?: number; page_size?: number }) =>
    api.get<EmailLogListResponse>(`${BASE}/logs`, { params }),
  testSend: (templateCode: string, recipientEmail: string) =>
    api.post<{ sent: boolean }>(`${BASE}/test-send`, { template_code: templateCode, recipient_email: recipientEmail }),
}
