import api from './api'

// ── Task templates ────────────────────────────────────────────────────────────

export interface OnboardingTaskRead {
  id: number
  code: string
  name: string
  description: string | null
  group: string  // admin | it | training | specialty
  default_assignee_role: string | null
  due_offset_days: number
  sort_order: number
  is_active: boolean
  created_at: string
}

export interface OnboardingTaskCreate {
  code: string
  name: string
  description?: string | null
  group: string
  default_assignee_role?: string | null
  due_offset_days?: number
  sort_order?: number
}

export interface OnboardingTaskUpdate {
  name?: string
  description?: string | null
  group?: string
  default_assignee_role?: string | null
  due_offset_days?: number
  sort_order?: number
  is_active?: boolean
}

// ── Checklist items ───────────────────────────────────────────────────────────

export interface OnboardingChecklistItemRead {
  id: number
  checklist_id: number
  task_id: number
  task_code: string
  task_name: string
  task_group: string
  assignee_user_id: number | null
  assignee_name: string | null
  due_date: string
  completed_at: string | null
  status: string  // pending | in_progress | done | skipped
  note: string | null
  is_overdue: boolean
  created_at: string
  updated_at: string
}

export interface OnboardingChecklistItemUpdate {
  status: string
  assignee_user_id?: number | null
  note?: string | null
}

// ── Checklist ─────────────────────────────────────────────────────────────────

export interface OnboardingChecklistRead {
  id: number
  employee_id: number
  employee_name: string
  employee_code: string
  department_name: string | null
  start_date: string
  hiring_decision_id: number | null
  buddy_user_id: number | null
  buddy_name: string | null
  status: string  // in_progress | completed | cancelled
  completion_pct: number
  items: OnboardingChecklistItemRead[]
  created_by_id: number | null
  created_at: string
  updated_at: string
}

export interface OnboardingChecklistCreate {
  employee_id: number
  hiring_decision_id?: number | null
  buddy_user_id?: number | null
}

export interface OnboardingChecklistUpdate {
  buddy_user_id?: number | null
  status?: string
}

export interface OnboardingChecklistListItem {
  id: number
  employee_id: number
  employee_name: string
  employee_code: string
  department_name: string | null
  start_date: string
  buddy_name: string | null
  status: string
  completion_pct: number
  total_items: number
  done_items: number
  overdue_items: number
  days_since_start: number
}

export interface OnboardingChecklistPage {
  items: OnboardingChecklistListItem[]
  total: number
  page: number
  page_size: number
}

// ── Service objects ───────────────────────────────────────────────────────────

export const onboardingTaskService = {
  list: (params?: { is_active?: boolean; group?: string }) =>
    api.get<OnboardingTaskRead[]>('/onboarding/tasks', { params }).then((r) => r.data),

  create: (data: OnboardingTaskCreate) =>
    api.post<OnboardingTaskRead>('/onboarding/tasks', data).then((r) => r.data),

  update: (id: number, data: OnboardingTaskUpdate) =>
    api.put<OnboardingTaskRead>(`/onboarding/tasks/${id}`, data).then((r) => r.data),

  delete: (id: number) =>
    api.delete(`/onboarding/tasks/${id}`),
}

export const onboardingChecklistService = {
  list: (params?: {
    status?: string
    department_id?: number
    days_until_completion?: number
    page?: number
    page_size?: number
  }) =>
    api.get<OnboardingChecklistPage>('/onboarding', { params }).then((r) => r.data),

  create: (data: OnboardingChecklistCreate) =>
    api.post<OnboardingChecklistRead>('/onboarding', data).then((r) => r.data),

  getById: (id: number) =>
    api.get<OnboardingChecklistRead>(`/onboarding/${id}`).then((r) => r.data),

  getByEmployee: (employeeId: number) =>
    api.get<OnboardingChecklistRead>(`/onboarding/employee/${employeeId}`).then((r) => r.data),

  update: (id: number, data: OnboardingChecklistUpdate) =>
    api.patch<OnboardingChecklistRead>(`/onboarding/${id}`, data).then((r) => r.data),

  updateItem: (checklistId: number, itemId: number, data: OnboardingChecklistItemUpdate) =>
    api
      .patch<OnboardingChecklistItemRead>(`/onboarding/${checklistId}/items/${itemId}`, data)
      .then((r) => r.data),
}
