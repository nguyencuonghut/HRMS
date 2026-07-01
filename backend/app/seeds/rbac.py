"""
Seed dữ liệu RBAC — Roles, Permissions, Users mặc định.

Idempotent: chạy nhiều lần không sinh dữ liệu trùng.
Chạy trước: migration 0002 phải đã được apply.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac_catalog import ACTION_DEFS, MODULE_DEFS
from app.core.security import hash_password


# ── Cấu hình permissions ───────────────────────────────────────────────────────
_MODULES = MODULE_DEFS
_ACTIONS = ACTION_DEFS

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
        "settings":    _FULL,
        "employees":   _FULL,
        "contracts":   _FULL,
        "leaves":      _FULL,
        "insurance":   _FULL,
        "salary":      _FULL,
        "rewards":     _FULL,
        "disciplines": _FULL,
        "training":    _FULL,
        "recruitment": _FULL,
        "performance": _FULL,
        "reports":     _VIEW_EXPORT,
        "audit_logs":  {"view"},
    },

    "hr_officer": {
        "org":         _VCE,
        "catalog":     {"view", "create", "edit", "export"},
        "settings":    _VCE,
        "employees":   {"view", "create", "edit", "export"},
        "contracts":   {"view", "create", "edit", "export"},
        "leaves":      _VCE,
        "insurance":   _VCE,
        "salary":      _VCE,
        "rewards":     _VCE,
        "disciplines": _VCE,
        "training":    _VCE,
        "recruitment": _VCE,
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
        "scope_type":   "department",
        "department_codes": ["KS"],
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
                    ON CONFLICT (code) DO UPDATE SET
                        name = EXCLUDED.name,
                        module = EXCLUDED.module,
                        action = EXCLUDED.action
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
    # 1. Lấy map role_code -> role_id
    role_rows = (await session.execute(text("SELECT id, code FROM roles"))).fetchall()
    role_id_map = {row.code: row.id for row in role_rows}

    # 2. Lấy map perm_code -> perm_id
    perm_rows = (await session.execute(text("SELECT id, code FROM permissions"))).fetchall()
    perm_id_map = {row.code: row.id for row in perm_rows}

    for role_code, module_perms in _ROLE_PERMS.items():
        role_id = role_id_map.get(role_code)
        if not role_id:
            continue

        # Tập hợp các permission ID mong muốn cho role này
        expected_perm_ids = set()
        for module, actions in module_perms.items():
            for action in actions:
                perm_code = f"{module}:{action}"
                perm_id = perm_id_map.get(perm_code)
                if perm_id:
                    expected_perm_ids.add(perm_id)

        # 3. Lấy các permission hiện có của role này
        existing_rows = (await session.execute(
            text("SELECT permission_id FROM role_permissions WHERE role_id = :role_id"),
            {"role_id": role_id}
        )).fetchall()
        existing_perm_ids = {row[0] for row in existing_rows}

        # 4. Xác định các permission cần xóa và cần thêm
        to_delete = existing_perm_ids - expected_perm_ids
        to_insert = expected_perm_ids - existing_perm_ids

        # 5. Xóa các permission không còn trong cấu hình
        for pid in to_delete:
            await session.execute(
                text("DELETE FROM role_permissions WHERE role_id = :role_id AND permission_id = :pid"),
                {"role_id": role_id, "pid": pid}
            )

        # 6. Insert các permission chưa có
        for pid in to_insert:
            result = await session.execute(
                text("""
                    INSERT INTO role_permissions (role_id, permission_id)
                    VALUES (:role_id, :pid)
                    ON CONFLICT DO NOTHING
                """),
                {"role_id": role_id, "pid": pid},
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

        department_ids = None
        scope_type = u.get("scope_type")
        department_codes = u.get("department_codes") or []

        if scope_type == "department":
            if not department_codes:
                raise RuntimeError(
                    f"Seed user {u['email']} khai báo scope_type='department' nhưng không có department_codes"
                )
            dept_rows = (
                await session.execute(
                    text("""
                        SELECT id, code
                        FROM departments
                        WHERE code = ANY(:codes)
                    """),
                    {"codes": department_codes},
                )
            ).fetchall()
            department_ids_by_code = {row.code: row.id for row in dept_rows}
            missing_codes = [
                code for code in department_codes if code not in department_ids_by_code
            ]
            if missing_codes:
                raise RuntimeError(
                    "Thiếu phòng ban để seed scope cho user "
                    f"{u['email']}: {', '.join(missing_codes)}. "
                    "Hãy chạy bootstrap departments trước khi seed local users."
                )
            department_ids = [department_ids_by_code[code] for code in department_codes]

        # Gán role cho user (idempotent) + đồng bộ scope theo seed
        await session.execute(
            text("""
                INSERT INTO user_roles (user_id, role_id, scope_type, department_ids)
                SELECT u.id, r.id, :scope_type, :department_ids
                FROM users u, roles r
                WHERE u.email = :email AND r.code = :role_code
                ON CONFLICT (user_id, role_id) DO UPDATE
                SET scope_type = EXCLUDED.scope_type,
                    department_ids = EXCLUDED.department_ids
            """),
            {
                "email": u["email"],
                "role_code": u["role"],
                "scope_type": scope_type,
                "department_ids": department_ids,
            },
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
