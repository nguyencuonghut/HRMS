import axios from 'axios'

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

const BASE = '/api/v1/org-history'

export default {
  getList: (params?: {
    entity_type?: string
    date_from?: string
    date_to?: string
    limit?: number
  }) => axios.get<OrgHistoryItem[]>(BASE, { params }),
}
