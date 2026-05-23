import api from './api'
import type { RewardRead } from './rewardService'
import type { DisciplineRead } from './disciplineService'

export interface RewardTypeStat {
  reward_type_id: number
  reward_type_name: string
  count: number
  total_value: string | null  // Decimal from backend, null if non-monetary
}

export interface DisciplineFormStat {
  discipline_form: string
  discipline_form_label: string
  count: number
}

export interface DepartmentRewardStat {
  department_id: number | null
  department_name: string | null
  reward_count: number
  discipline_count: number
}

export interface RewardDisciplineSummary {
  total_rewards: number
  total_disciplines: number
  total_reward_value: string  // Decimal string
  by_reward_type: RewardTypeStat[]
  by_discipline_form: DisciplineFormStat[]
  by_department: DepartmentRewardStat[]
}

export interface RewardDisciplineReportPage {
  from_date: string
  to_date: string
  department_id: number | null
  department_name: string | null
  summary: RewardDisciplineSummary
  reward_items: RewardRead[]
  discipline_items: DisciplineRead[]
  total_rewards: number
  total_disciplines: number
}

export default {
  getSummary: (params: {
    from_date: string
    to_date: string
    department_id?: number | null
    reward_page?: number
    reward_page_size?: number
    discipline_page?: number
    discipline_page_size?: number
  }) => api.get<RewardDisciplineReportPage>('/rewards/report/summary', { params }),

  exportExcel: (params: {
    from_date: string
    to_date: string
    department_id?: number | null
  }) => api.get('/rewards/report/export', { params, responseType: 'blob' }),
}
