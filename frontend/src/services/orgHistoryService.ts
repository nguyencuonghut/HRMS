import api from './api'

export interface OrgHistoryItem {
  id:           number
  entity_type:  string
  entity_label: string
  entity_id:    number
  entity_name:  string
  action:       string
  action_label: string
  changed_by:   number | null
  changed_at:   string
  old_data:     Record<string, unknown> | null
  new_data:     Record<string, unknown> | null
}

export interface OrgHistoryPageResponse {
  items:       OrgHistoryItem[]
  total:       number
  page:        number
  page_size:   number
  total_pages: number
}

export interface OrgHistoryFilter {
  entity_type?: string
  date_from?:   string
  date_to?:     string
  page?:        number
  page_size?:   number
}

export default {
  getList: (params?: OrgHistoryFilter) =>
    api.get<OrgHistoryPageResponse>('/org-history', { params }),
}
