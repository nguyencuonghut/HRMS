import api from './api'

export interface CourseCompletionStat {
  course_id: number
  course_name: string
  course_type_label: string
  total_assigned: number
  completed: number
  not_completed: number
  in_progress: number
  completion_rate: number
}

export interface DepartmentTrainingStat {
  department_id: number | null
  department_name: string | null
  total_records: number
  completed: number
  completion_rate: number
  total_cost: string | null  // Decimal as string
}

export interface TrainingReportSummary {
  from_date: string
  to_date: string
  department_id: number | null
  department_name: string | null
  course_id: number | null
  course_name: string | null
  total_records: number
  total_completed: number
  total_not_completed: number
  total_in_progress: number
  total_cost: string  // Decimal as string
  avg_completion_rate: number
  by_course: CourseCompletionStat[]
  by_department: DepartmentTrainingStat[]
}

export interface IncompleteMandatoryEmployee {
  employee_id: number
  employee_code: string
  employee_name: string
  department_name: string | null
  incomplete_courses: string[]
  incomplete_count: number
}

export default {
  getSummary: (params: Record<string, unknown>) =>
    api.get<TrainingReportSummary>('/training/report/summary', { params }),

  getIncompleteMandatory: (params?: Record<string, unknown>) =>
    api.get<IncompleteMandatoryEmployee[]>('/training/report/incomplete-mandatory', { params }),

  exportExcel: async (params: Record<string, unknown>): Promise<void> => {
    const res = await api.get('/training/report/export', {
      params,
      responseType: 'blob',
    })
    const blob = new Blob([res.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    const from = String(params.from_date ?? '')
    const to = String(params.to_date ?? '')
    a.href = url
    a.download = `bao_cao_dao_tao_${from}_${to}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  },
}
