from fastapi import APIRouter

from app.api.v1.endpoints import auth
from app.api.v1.endpoints import admin_units
from app.api.v1.endpoints import education_catalog
from app.api.v1.endpoints import other_business_catalog
from app.api.v1.endpoints import employee_code_sequences
from app.api.v1.endpoints import departments
from app.api.v1.endpoints import job_titles
from app.api.v1.endpoints import job_positions
from app.api.v1.endpoints import org_history
from app.api.v1.endpoints import users
from app.api.v1.endpoints import roles
from app.api.v1.endpoints import audit_logs
from app.api.v1.endpoints import employees
from app.api.v1.endpoints import employee_io
from app.api.v1.endpoints import employee_contracts
from app.api.v1.endpoints import contracts
from app.api.v1.endpoints import reminders
from app.api.v1.endpoints import leave_entitlements
from app.api.v1.endpoints import leave_records
from app.api.v1.endpoints import leave_reports
from app.api.v1.endpoints import bhyt_clinic
from app.api.v1.endpoints import insurance
from app.api.v1.endpoints import salary
from app.api.v1.endpoints import rewards
from app.api.v1.endpoints import disciplines
from app.api.v1.endpoints import training
from app.api.v1.endpoints import performance
from app.api.v1.endpoints import recruitment
from app.api.v1.endpoints import onboarding
from app.api.v1.endpoints import probation
from app.api.v1.endpoints import probation_reports
from app.api.v1.endpoints import dashboard
from app.api.v1.endpoints import hr_reports
from app.api.v1.endpoints import leave_analytics
from app.api.v1.endpoints import data_imports
from app.api.v1.endpoints import insurance_reports
from app.api.v1.endpoints import contract_reports
from app.api.v1.endpoints import export

router = APIRouter()
router.include_router(auth.router,          prefix="/auth",          tags=["Xác thực"])
router.include_router(admin_units.router,   prefix="/admin-units",   tags=["Danh mục hành chính"])
router.include_router(admin_units.hierarchy_router, prefix="/admin-hierarchies", tags=["Danh mục hành chính"])
router.include_router(admin_units.lookup_router, tags=["Danh mục hành chính"])
router.include_router(education_catalog.level_router, prefix="/education-levels", tags=["Danh mục học vấn"])
router.include_router(education_catalog.institution_router, prefix="/educational-institutions", tags=["Danh mục học vấn"])
router.include_router(education_catalog.major_router, prefix="/education-majors", tags=["Danh mục học vấn"])
router.include_router(education_catalog.lookup_router, tags=["Danh mục học vấn"])
router.include_router(other_business_catalog.contract_category_router, prefix="/contract-categories", tags=["Danh mục nghiệp vụ khác"])
router.include_router(other_business_catalog.nationality_router, prefix="/nationalities", tags=["Danh mục nghiệp vụ khác"])
router.include_router(other_business_catalog.ethnicity_router, prefix="/ethnicities", tags=["Danh mục nghiệp vụ khác"])
router.include_router(other_business_catalog.religion_router, prefix="/religions", tags=["Danh mục nghiệp vụ khác"])
router.include_router(other_business_catalog.bank_router, prefix="/banks", tags=["Danh mục nghiệp vụ khác"])
router.include_router(other_business_catalog.skill_router, prefix="/skills", tags=["Danh mục nghiệp vụ khác"])
router.include_router(other_business_catalog.certificate_router, prefix="/certificates", tags=["Danh mục nghiệp vụ khác"])
router.include_router(other_business_catalog.leave_type_router, prefix="/leave-types", tags=["Danh mục nghiệp vụ khác"])
router.include_router(other_business_catalog.contract_template_router, prefix="/contract-templates", tags=["Danh mục nghiệp vụ khác"])
router.include_router(employee_code_sequences.router, prefix="/employee-code-sequences", tags=["Mã nhân viên"])
router.include_router(other_business_catalog.lookup_router, tags=["Danh mục nghiệp vụ khác"])
router.include_router(departments.router,   prefix="/departments",   tags=["Cơ cấu tổ chức"])
router.include_router(job_titles.router,    prefix="/job-titles",    tags=["Cơ cấu tổ chức"])
router.include_router(job_positions.router, prefix="/job-positions", tags=["Cơ cấu tổ chức"])
router.include_router(org_history.router,   prefix="/org-history",   tags=["Cơ cấu tổ chức"])
router.include_router(users.router,         prefix="/users",         tags=["Quản lý người dùng"])
router.include_router(roles.router,         prefix="/roles",         tags=["Vai trò & Quyền"])
router.include_router(audit_logs.router,    prefix="/audit-logs",    tags=["Nhật ký hệ thống"])
router.include_router(employee_io.router,        prefix="/employees",  tags=["Nhân sự — Import/Export"])
router.include_router(employee_contracts.router, prefix="/employees",  tags=["Hợp đồng nhân viên"])
router.include_router(employees.router,          prefix="/employees",  tags=["Nhân sự"])
router.include_router(contracts.router,          prefix="/contracts",  tags=["Hợp đồng"])
router.include_router(reminders.router,          prefix="/reminders",         tags=["Nhắc nhở"])
router.include_router(leave_entitlements.router, prefix="/leave-entitlements", tags=["Quản lý ngày phép"])
router.include_router(leave_records.router,     prefix="/leave-records",     tags=["Ghi nhận nghỉ phép"])
router.include_router(leave_reports.router,     prefix="/leave-reports",     tags=["Báo cáo nghỉ phép"])
router.include_router(bhyt_clinic.router,       prefix="/bhyt-clinics",      tags=["Danh mục bệnh viện KCB"])
router.include_router(insurance.router,         prefix="/insurance",         tags=["Bảo hiểm BHXH"])
router.include_router(salary.router,            prefix="/salary",            tags=["Lương BHXH"])
router.include_router(rewards.router,                prefix="/rewards",      tags=["Khen thưởng"])
router.include_router(rewards.employee_history_router, prefix="/employees",  tags=["Khen thưởng"])
router.include_router(disciplines.router,              prefix="/disciplines", tags=["Kỷ luật"])
router.include_router(disciplines.employee_history_router, prefix="/employees", tags=["Kỷ luật"])
router.include_router(training.router, prefix="/training", tags=["Đào tạo"])
router.include_router(training.employee_certificate_router, prefix="/employees", tags=["Đào tạo"])
router.include_router(performance.router, prefix="/performance", tags=["Hiệu suất KPI"])
router.include_router(performance.employee_perf_router, prefix="/employees", tags=["Hiệu suất KPI"])
router.include_router(recruitment.router, prefix="/recruitment", tags=["Tuyển dụng"])
router.include_router(onboarding.router,  prefix="/onboarding",  tags=["Onboarding"])
router.include_router(probation.router,   prefix="/employees",   tags=["Quản lý thử việc"])
router.include_router(probation_reports.router, prefix="/reports/probation", tags=["Báo cáo thử việc"])
router.include_router(dashboard.router, prefix="/reports/dashboard", tags=["Dashboard nhân sự"])
router.include_router(hr_reports.router, prefix="/reports/hr", tags=["Báo cáo nhân sự"])
router.include_router(leave_analytics.router, prefix="/reports/leaves", tags=["Phân tích nghỉ phép"])
router.include_router(insurance_reports.router, prefix="/reports/insurance", tags=["Báo cáo Bảo hiểm Analytics"])
router.include_router(contract_reports.router, prefix="/reports/contracts", tags=["Báo cáo Hợp đồng"])
router.include_router(export.router, prefix="/reports/export", tags=["Trung tâm xuất báo cáo"])
router.include_router(data_imports.router, prefix="/imports", tags=["Import dữ liệu"])
