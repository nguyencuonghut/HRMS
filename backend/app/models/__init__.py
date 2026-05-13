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
from app.models.salary import (  # noqa: F401
    RegionalMinimumWage,
    CompanyBhxhRegion,
    SalaryScale,
    SalaryScaleEntry,
)
