# Import tất cả models để SQLModel.metadata nhận diện đủ bảng khi Alembic chạy.
from app.models.auth import (  # noqa: F401
    AuditLog,
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)
from app.models.org import (  # noqa: F401
    Department,
    JobTitle,
    JobPosition,
    JobPositionAttachment,
    OrgChangeLog,
)
from app.models.catalog import (  # noqa: F401
    AdministrativeUnit,
    AdministrativeHierarchy,
    AdministrativeImportBatch,
    AdministrativeImportError,
    Bank,
    Certificate,
    ContractCategory,
    ContractTemplate,
    ContractTemplatePlaceholder,
    EducationLevel,
    EducationalInstitution,
    EducationMajor,
    Ethnicity,
    LeaveType,
    Nationality,
    Religion,
    Skill,
)
from app.models.salary import (  # noqa: F401
    RegionalMinimumWage,
    CompanyBhxhRegion,
    SalaryScale,
    SalaryScaleEntry,
)
from app.models.insurance import (  # noqa: F401
    InsuranceContributionComponent,
    InsurancePolicyVersion,
    InsurancePolicyComponentRate,
    InsuranceChangeEvent,
)
from app.models.employee import (  # noqa: F401
    Employee,
    EmployeeAddress,
    EmployeeBankAccount,
)
from app.models.employee_insurance import (  # noqa: F401
    EmployeeInsuranceProfile,
    EmployeeInsuranceComponentOverride,
)
from app.models.employee_code import (  # noqa: F401
    EmployeeCodeSequence,
    EmployeeCodeSequenceRule,
)
from app.models.employee_job import (  # noqa: F401
    EmployeeJobRecord,
)
from app.models.employee_relative import (  # noqa: F401
    EmployeeRelative,
)
from app.models.employee_education import (  # noqa: F401
    EmployeeEducationHistory,
    EmployeeWorkExperience,
    EmployeeSkill,
    EmployeeCertificate,
    EmployeeLanguage,
)
from app.models.employee_attachment import EmployeeAttachment  # noqa: F401
from app.models.employee_contract import EmployeeContract  # noqa: F401
from app.models.leave_entitlement import LeaveEntitlement  # noqa: F401
from app.models.leave_record import LeaveRecord  # noqa: F401
from app.models.bhyt_clinic import BhytClinic  # noqa: F401
from app.models.salary_adjustment import BhxhSalaryAdjustment  # noqa: F401
from app.models.reward import RewardType, EmployeeReward  # noqa: F401
from app.models.discipline import EmployeeDiscipline  # noqa: F401
from app.models.training import TrainingCourse, TrainingPlan, TrainingPlanCourse, EmployeeTrainingRecord, EmployeeTrainingCertificate  # noqa: F401
