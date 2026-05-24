import api from './api'

export const COURSE_TYPES = [
  { value: 'noi_bo',     label: 'Nội bộ' },
  { value: 'ben_ngoai',  label: 'Bên ngoài' },
  { value: 'online',     label: 'Online' },
] as const

export const PLAN_STATUSES = [
  { value: 'draft',     label: 'Dự thảo' },
  { value: 'approved',  label: 'Đã duyệt' },
  { value: 'cancelled', label: 'Đã hủy' },
] as const

export type CourseTypeValue = 'noi_bo' | 'ben_ngoai' | 'online'
export type PlanStatusValue = 'draft' | 'approved' | 'cancelled'

export interface CourseRead {
  id: number
  code: string
  name: string
  course_type: CourseTypeValue
  course_type_label: string
  duration_hours: number | null
  organizer: string | null
  description: string | null
  cost_per_person: string | null   // Decimal as string from backend
  is_mandatory: boolean
  is_active: boolean
  created_at: string
}

export interface CourseCreate {
  code: string
  name: string
  course_type: CourseTypeValue
  duration_hours?: number | null
  organizer?: string | null
  description?: string | null
  cost_per_person?: number | null
  is_mandatory?: boolean
}

export interface CourseUpdate {
  code?: string | null
  name?: string | null
  course_type?: CourseTypeValue | null
  duration_hours?: number | null
  organizer?: string | null
  description?: string | null
  cost_per_person?: number | null
  is_mandatory?: boolean | null
  is_active?: boolean | null
}

export interface CourseListPage {
  items: CourseRead[]
  total: number
  page: number
  page_size: number
}

export interface PlanCourseRead {
  id: number
  plan_id: number
  course_id: number
  course_code: string
  course_name: string
  course_type_label: string
  duration_hours: number | null
  target_count: number | null
  scheduled_date: string | null
  note: string | null
}

export interface PlanCourseCreate {
  course_id: number
  target_count?: number | null
  scheduled_date?: string | null
  note?: string | null
}

export interface PlanCourseUpdate {
  target_count?: number | null
  scheduled_date?: string | null
  note?: string | null
}

export interface PlanRead {
  id: number
  title: string
  year: number
  quarter: number | null
  department_id: number | null
  department_name: string | null
  status: PlanStatusValue
  status_label: string
  description: string | null
  created_by_name: string | null
  created_at: string
  course_count: number
}

export interface PlanReadDetail extends PlanRead {
  courses: PlanCourseRead[]
}

export interface PlanCreate {
  title: string
  year: number
  quarter?: number | null
  department_id?: number | null
  description?: string | null
}

export interface PlanUpdate {
  title?: string | null
  description?: string | null
}

export interface PlanListPage {
  items: PlanRead[]
  total: number
  page: number
  page_size: number
}

export default {
  // Courses
  listCourses: (params?: Record<string, unknown>) =>
    api.get<CourseListPage>('/training/courses', { params }),
  getCourse: (id: number) =>
    api.get<CourseRead>(`/training/courses/${id}`),
  createCourse: (data: CourseCreate) =>
    api.post<CourseRead>('/training/courses', data),
  updateCourse: (id: number, data: CourseUpdate) =>
    api.put<CourseRead>(`/training/courses/${id}`, data),
  deleteCourse: (id: number) =>
    api.delete(`/training/courses/${id}`),

  // Plans
  listPlans: (params?: Record<string, unknown>) =>
    api.get<PlanListPage>('/training/plans', { params }),
  getPlanDetail: (id: number) =>
    api.get<PlanReadDetail>(`/training/plans/${id}`),
  createPlan: (data: PlanCreate) =>
    api.post<PlanRead>('/training/plans', data),
  updatePlan: (id: number, data: PlanUpdate) =>
    api.put<PlanRead>(`/training/plans/${id}`, data),
  deletePlan: (id: number) =>
    api.delete(`/training/plans/${id}`),
  approvePlan: (id: number) =>
    api.post<PlanRead>(`/training/plans/${id}/approve`),
  cancelPlan: (id: number) =>
    api.post<PlanRead>(`/training/plans/${id}/cancel`),

  // Plan courses
  listPlanCourses: (planId: number) =>
    api.get<PlanCourseRead[]>(`/training/plans/${planId}/courses`),
  addCourseToPlan: (planId: number, data: PlanCourseCreate) =>
    api.post<PlanCourseRead>(`/training/plans/${planId}/courses`, data),
  updatePlanCourse: (planId: number, courseId: number, data: PlanCourseUpdate) =>
    api.put<PlanCourseRead>(`/training/plans/${planId}/courses/${courseId}`, data),
  removeFromPlan: (planId: number, courseId: number) =>
    api.delete(`/training/plans/${planId}/courses/${courseId}`),
}
