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

export const RECORD_STATUSES = [
  { value: 'chua_bat_dau',     label: 'Chưa bắt đầu' },
  { value: 'dang_hoc',         label: 'Đang học' },
  { value: 'hoan_thanh',       label: 'Hoàn thành' },
  { value: 'khong_hoan_thanh', label: 'Không hoàn thành' },
  { value: 'vang_mat',         label: 'Vắng mặt' },
] as const

export const RECORD_RESULTS = [
  { value: 'dat',      label: 'Đạt' },
  { value: 'khong_dat', label: 'Không đạt' },
] as const

export type CourseTypeValue = 'noi_bo' | 'ben_ngoai' | 'online'
export type PlanStatusValue = 'draft' | 'approved' | 'cancelled'
export type RecordStatusValue = 'chua_bat_dau' | 'dang_hoc' | 'hoan_thanh' | 'khong_hoan_thanh' | 'vang_mat'
export type RecordResultValue = 'dat' | 'khong_dat'

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

export interface TrainingRecordRead {
  id: number
  employee_id: number
  employee_code: string
  employee_name: string
  department_name: string | null
  course_id: number
  course_name: string
  course_type: string
  course_type_label: string
  plan_id: number | null
  plan_title: string | null
  status: RecordStatusValue
  status_label: string
  result: RecordResultValue | null
  result_label: string | null
  score: string | null   // Decimal as string
  start_date: string | null
  end_date: string | null
  note: string | null
  source_review_id: number | null
  created_by_name: string | null
  created_at: string
}

export interface TrainingRecordCreate {
  employee_id: number
  course_id: number
  plan_id?: number | null
  status?: RecordStatusValue
  start_date?: string | null
  end_date?: string | null
  note?: string | null
}

export interface TrainingRecordUpdate {
  status?: RecordStatusValue | null
  result?: RecordResultValue | null
  score?: number | null
  start_date?: string | null
  end_date?: string | null
  note?: string | null
}

export interface TrainingRecordListPage {
  items: TrainingRecordRead[]
  total: number
  page: number
  page_size: number
}

export type ExpiryStatusValue = 'valid' | 'expiring_soon' | 'expired' | 'no_expiry'

export interface CertificateRead {
  id: number
  employee_id: number
  employee_code: string
  employee_name: string
  department_name: string | null
  certificate_name: string
  issuing_organization: string | null
  issued_date: string
  expiry_date: string | null
  expiry_status: ExpiryStatusValue
  days_until_expiry: number | null
  related_course_id: number | null
  related_course_name: string | null
  note: string | null
  has_file: boolean
  file_name: string | null
  file_size: number | null
  created_by_name: string | null
  created_at: string
}

export interface CertificateCreate {
  employee_id: number
  certificate_name: string
  issuing_organization?: string | null
  issued_date: string
  expiry_date?: string | null
  related_course_id?: number | null
  note?: string | null
}

export interface CertificateUpdate {
  certificate_name?: string | null
  issuing_organization?: string | null
  issued_date?: string | null
  expiry_date?: string | null
  related_course_id?: number | null
  note?: string | null
}

export interface CertificateListPage {
  items: CertificateRead[]
  total: number
  page: number
  page_size: number
}

export interface BulkAssignRequest {
  employee_ids?: number[]
  department_ids?: number[]
  plan_id: number
  course_id: number
  note?: string | null
}

export interface BulkAssignResult {
  created: number
  skipped: number
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

  // Training records (9.2)
  getRecords: (params?: Record<string, unknown>) =>
    api.get<TrainingRecordListPage>('/training/records', { params }),
  getRecord: (id: number) =>
    api.get<TrainingRecordRead>(`/training/records/${id}`),
  createRecord: (data: TrainingRecordCreate) =>
    api.post<TrainingRecordRead>('/training/records', data),
  updateRecord: (id: number, data: TrainingRecordUpdate) =>
    api.put<TrainingRecordRead>(`/training/records/${id}`, data),
  deleteRecord: (id: number) =>
    api.delete(`/training/records/${id}`),
  bulkAssign: (planId: number, data: BulkAssignRequest) =>
    api.post<BulkAssignResult>(`/training/plans/${planId}/assign`, data),
  getPassport: (employeeId: number) =>
    api.get<TrainingRecordRead[]>(`/training/passport/${employeeId}`),

  // Certificates (9.3)
  getCertificates: (params?: Record<string, unknown>) =>
    api.get<CertificateListPage>('/training/certificates', { params }),
  getCertificate: (id: number) =>
    api.get<CertificateRead>(`/training/certificates/${id}`),
  createCertificate: (body: CertificateCreate, file?: File | null) => {
    const fd = new FormData()
    fd.append('body', JSON.stringify(body))
    if (file) fd.append('file', file)
    return api.post<CertificateRead>('/training/certificates', fd)
  },
  updateCertificate: (id: number, body: CertificateUpdate, file?: File | null) => {
    const fd = new FormData()
    fd.append('body', JSON.stringify(body))
    if (file) fd.append('file', file)
    return api.put<CertificateRead>(`/training/certificates/${id}`, fd)
  },
  deleteCertificate: (id: number) =>
    api.delete(`/training/certificates/${id}`),
  downloadCertificateFile: async (id: number, fileName: string): Promise<void> => {
    const res = await api.get(`/training/certificates/${id}/download`, { responseType: 'blob' })
    const url = URL.createObjectURL(new Blob([res.data]))
    const a = document.createElement('a')
    a.href = url
    a.download = fileName
    a.click()
    URL.revokeObjectURL(url)
  },
}
