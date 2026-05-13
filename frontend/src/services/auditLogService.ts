import api from './api'

export interface AuditLogItem {
  id:          number
  user_id:     number | null
  user_email:  string | null
  user_name:   string | null
  action:      string
  entity_type: string | null
  entity_id:   number | null
  entity_name: string | null
  old_data:    Record<string, unknown> | null
  new_data:    Record<string, unknown> | null
  ip_address:  string | null
  user_agent:  string | null
  created_at:  string
}

export interface AuditLogFilter {
  user_id?:     number
  action?:      string
  entity_type?: string
  entity_id?:   number
  date_from?:   string
  date_to?:     string
  limit?:       number
}

export default {
  getList(params?: AuditLogFilter) {
    return api.get<AuditLogItem[]>('/audit-logs', { params })
  },
}
