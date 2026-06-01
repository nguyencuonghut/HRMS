"""
Seed dữ liệu RBAC — Roles, Permissions, Users mặc định.

Idempotent: chạy nhiều lần không sinh dữ liệu trùng.
Chạy trước: migration 0002 phải đã được apply.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password


# ── Cấu hình permissions ───────────────────────────────────────────────────────

_MODULES = [
    ("org",         "Cơ cấu tổ chức"),
    ("catalog",     "Danh mục"),
    ("employees",   "Nhân sự"),
    ("contracts",   "Hợp đồng"),
    ("leaves",      "Nghỉ phép"),
    ("insurance",   "Bảo hiểm BHXH"),
    ("salary",      "Lương BHXH"),
    ("rewards",     "Khen thưởng & Kỷ luật"),
    ("training",    "Đào tạo"),
    ("performance", "Đánh giá KPI"),
    ("reports",     "Báo cáo"),
    ("users",       "Tài khoản người dùng"),
    ("roles",       "Vai trò & Quyền"),
    ("audit_logs",  "Nhật ký hệ thống"),
]

_ACTIONS = [
    ("view",   "Xem"),
    ("create", "Thêm mới"),
    ("edit",   "Chỉnh sửa"),
    ("delete", "Xóa"),
    ("export", "Xuất dữ liệu"),
]

# ── Cấu hình roles ─────────────────────────────────────────────────────────────

_ROLES = [
    ("admin",        "Quản trị viên",       "Toàn quyền hệ thống",                             True),
    ("hr_manager",   "HR Manager",           "Quản lý nhân sự toàn công ty",                    True),
    ("hr_officer",   "Nhân viên HR",         "Xem, thêm, sửa dữ liệu nhân sự; không xóa",      True),
    ("line_manager", "Quản lý phòng ban",    "Xem nhân viên & nghỉ phép, đánh giá KPI phòng",   True),
    ("finance",      "Kế toán / Tài chính",  "Quản lý BHXH và lương BHXH",                      True),
]

# ── Ma trận quyền theo role ────────────────────────────────────────────────────
# Format: {role_code: {module: set_of_actions}}

_FULL = {"view", "create", "edit", "delete", "export"}
_VIEW_EXPORT = {"view", "export"}
_VCE = {"view", "create", "edit"}   # view + create + edit

_ROLE_PERMS: dict[str, dict[str, set[str]]] = {
    "admin": {m: _FULL for m, _ in _MODULES},

    "hr_manager": {
        "org":         {"view", "create", "edit", "delete"},
        "catalog":     _FULL,
        "employees":   _FULL,
        "contracts":   _FULL,
        "leaves":      _FULL,
        "insurance":   _FULL,
        "salary":      _FULL,
        "rewards":     _FULL,
        "training":    _FULL,
        "performance": _FULL,
        "reports":     _VIEW_EXPORT,
        "audit_logs":  {"view"},
    },

    "hr_officer": {
        "org":         _VCE,
        "catalog":     {"view", "create", "edit", "export"},
        "employees":   {"view", "create", "edit", "export"},
        "contracts":   {"view", "create", "edit", "export"},
        "leaves":      _VCE,
        "insurance":   _VCE,
        "salary":      _VCE,
        "rewards":     _VCE,
        "training":    _VCE,
        "performance": _VCE,
        "reports":     _VIEW_EXPORT,
    },

    "line_manager": {
        "org":         {"view"},
        "employees":   {"view"},
        "leaves":      _VCE,
        "performance": _VCE,
    },

    "finance": {
        "insurance": _FULL,
        "salary":    _FULL,
        "reports":   _VIEW_EXPORT,
    },
}

# ── Seed users (1 per role) ────────────────────────────────────────────────────

_SEED_USERS = [
    {
        "email":        "admin@hrms.local",
        "full_name":    "Quản trị viên",
        "password":     "Hrms@2026",
        "is_superuser": True,
        "role":         "admin",
    },
    {
        "email":        "hrmanager@hrms.local",
        "full_name":    "HR Manager",
        "password":     "Hrms@2026",
        "is_superuser": False,
        "role":         "hr_manager",
    },
    {
        "email":        "hrofficer@hrms.local",
        "full_name":    "Nhân viên HR",
        "password":     "Hrms@2026",
        "is_superuser": False,
        "role":         "hr_officer",
    },
    {
        "email":        "linemanager@hrms.local",
        "full_name":    "Quản lý phòng ban",
        "password":     "Hrms@2026",
        "is_superuser": False,
        "role":         "line_manager",
    },
    {
        "email":        "finance@hrms.local",
        "full_name":    "Kế toán / Tài chính",
        "password":     "Hrms@2026",
        "is_superuser": False,
        "role":         "finance",
    },
]


# ── Các hàm seed ───────────────────────────────────────────────────────────────

async def seed_permissions(session: AsyncSession) -> int:
    inserted = 0
    for module, module_label in _MODULES:
        for action, action_label in _ACTIONS:
            result = await session.execute(
                text("""
                    INSERT INTO permissions (code, name, module, action)
                    VALUES (:code, :name, :module, :action)
                    ON CONFLICT (code) DO NOTHING
                """),
                {
                    "code":   f"{module}:{action}",
                    "name":   f"{action_label} — {module_label}",
                    "module": module,
                    "action": action,
                },
            )
            inserted += result.rowcount
    return inserted


async def seed_roles(session: AsyncSession) -> int:
    inserted = 0
    for code, name, description, is_system in _ROLES:
        result = await session.execute(
            text("""
                INSERT INTO roles (code, name, description, is_system)
                VALUES (:code, :name, :description, :is_system)
                ON CONFLICT (code) DO NOTHING
            """),
            {"code": code, "name": name, "description": description, "is_system": is_system},
        )
        inserted += result.rowcount
    return inserted


async def seed_role_permissions(session: AsyncSession) -> int:
    inserted = 0
    for role_code, module_perms in _ROLE_PERMS.items():
        for module, actions in module_perms.items():
            for action in actions:
                perm_code = f"{module}:{action}"
                result = await session.execute(
                    text("""
                        INSERT INTO role_permissions (role_id, permission_id)
                        SELECT r.id, p.id
                        FROM roles r, permissions p
                        WHERE r.code = :role_code AND p.code = :perm_code
                        ON CONFLICT DO NOTHING
                    """),
                    {"role_code": role_code, "perm_code": perm_code},
                )
                inserted += result.rowcount
    return inserted


async def seed_users(session: AsyncSession) -> int:
    inserted = 0
    for u in _SEED_USERS:
        result = await session.execute(
            text("""
                INSERT INTO users (email, full_name, hashed_password, is_active, is_superuser)
                VALUES (:email, :full_name, :hashed_password, true, :is_superuser)
                ON CONFLICT (email) DO NOTHING
            """),
            {
                "email":           u["email"],
                "full_name":       u["full_name"],
                "hashed_password": hash_password(u["password"]),
                "is_superuser":    u["is_superuser"],
            },
        )
        inserted += result.rowcount

        # Gán role cho user (idempotent)
        await session.execute(
            text("""
                INSERT INTO user_roles (user_id, role_id)
                SELECT u.id, r.id
                FROM users u, roles r
                WHERE u.email = :email AND r.code = :role_code
                ON CONFLICT DO NOTHING
            """),
            {"email": u["email"], "role_code": u["role"]},
        )
    return inserted


async def run_core(session: AsyncSession) -> tuple[int, int, int]:
    perm_added = await seed_permissions(session)
    role_added = await seed_roles(session)
    rp_added = await seed_role_permissions(session)
    return perm_added, role_added, rp_added


async def run(session: AsyncSession, *, include_users: bool = True) -> None:
    perm_added, role_added, rp_added = await run_core(session)
    user_added = 0
    if include_users:
        user_added = await seed_users(session)
    await session.commit()

    print(f"  [rbac] Permissions:        +{perm_added} dòng")
    print(f"  [rbac] Roles:              +{role_added} dòng")
    print(f"  [rbac] Role-Permissions:   +{rp_added} dòng")
    if include_users:
        print(f"  [rbac] Seed users:         +{user_added} dòng")
    else:
        print("  [rbac] Seed users:         bỏ qua")
