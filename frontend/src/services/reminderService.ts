import api from './api'

export type EventType = 'birthday' | 'anniversary' | 'probation_end' | 'contract_expiry'

export interface ReminderItem {
  employee_id:   number
  employee_code: string
  employee_name: string
  department:    string | null
  event_type:    EventType
  event_date:    string
  days_until:    number
  extra:         Record<string, unknown>
}

export interface RemindersResponse {
  birthday:        ReminderItem[]
  anniversary:     ReminderItem[]
  probation_end:   ReminderItem[]
  contract_expiry: ReminderItem[]
  total:           number
}

export const EVENT_TYPE_LABELS: Record<EventType, string> = {
  birthday:        'Sinh nhật',
  anniversary:     'Thâm niên',
  probation_end:   'Hết thử việc',
  contract_expiry: 'HĐ sắp hết hạn',
}

export const EVENT_TYPE_ICONS: Record<EventType, string> = {
  birthday:        '🎂',
  anniversary:     '⭐',
  probation_end:   '📋',
  contract_expiry: '📄',
}

export default {
  getReminders: (days = 30, types?: EventType[]) =>
    api.get<RemindersResponse>('/reminders', {
      params: {
        days,
        ...(types?.length ? { types: types.join(',') } : {}),
      },
    }),
}
