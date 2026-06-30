import api from './api'

export interface AuditLogItem {
  id:          number
  user_id:     number | null
  user_email:  string | null
  user_name:   string | null
  action:      string
  action_label: string
  action_order: number
  action_severity: string
  entity_type: string | null
  entity_type_label: string | null
  entity_type_order: number | null
  entity_type_severity: string | null
  entity_id:   number | null
  entity_name: string | null
  old_data:    Record<string, unknown> | null
  new_data:    Record<string, unknown> | null
  ip_address:  string | null
  user_agent:  string | null
  created_at:  string
}

export interface AuditLogPageResponse {
  items:       AuditLogItem[]
  total:       number
  page:        number
  page_size:   number
  total_pages: number
}

export interface AuditActionOption {
  code: string
  label: string
  severity: string
  order: number
}

export interface AuditEntityTypeOption {
  code: string
  label: string
  severity: string
  order: number
}

export interface AuditLogMetaResponse {
  actions: AuditActionOption[]
  entity_types: AuditEntityTypeOption[]
}

export interface AuditLogFilter {
  user_id?:     number
  action?:      string
  entity_type?: string
  entity_id?:   number
  date_from?:   string
  date_to?:     string
  keyword?:     string
  page?:        number
  page_size?:   number
}

export default {
  getMeta() {
    return api.get<AuditLogMetaResponse>('/audit-logs/meta')
  },
  getList(params?: AuditLogFilter) {
    return api.get<AuditLogPageResponse>('/audit-logs', { params })
  },
}
