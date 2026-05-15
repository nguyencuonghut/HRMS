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
from app.models.employee import (  # noqa: F401
    Employee,
    EmployeeAddress,
    EmployeeBankAccount,
)
from app.models.employee_job import (  # noqa: F401
    EmployeeJobRecord,
)
from app.models.employee_relative import (  # noqa: F401
    EmployeeRelative,
)
