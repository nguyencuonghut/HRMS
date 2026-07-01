"""Integration tests cho RBAC seed — roles, permissions, users."""
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.seeds import rbac


# ── Helpers — tạo fresh engine để tránh event loop conflict với TestClient ─────

def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


async def _scalar(sql: str, **params) -> int:
    async with _make_session()() as s:
        return (await s.execute(text(sql), params)).scalar()


async def _rows(sql: str, **params) -> list:
    async with _make_session()() as s:
        return (await s.execute(text(sql), params)).fetchall()


@pytest.fixture(scope="module", autouse=True)
async def ensure_latest_rbac_seed():
    async with _make_session()() as s:
        await s.execute(
            text("""
                INSERT INTO departments (code, name, short_name, parent_id, dept_type, order_no, is_active)
                VALUES ('KS', 'Phòng kiểm soát', NULL, NULL, 'PHONG', 1, TRUE)
                ON CONFLICT (code) WHERE deleted_at IS NULL DO NOTHING
            """)
        )
        await rbac.run(s)
    yield


# ── Permissions ────────────────────────────────────────────────────────────────

async def test_permissions_count():
    """17 modules × 5 actions = 85 permissions."""
    count = await _scalar("SELECT COUNT(*) FROM permissions")
    assert count == 85


async def test_permission_code_format():
    """Tất cả code phải theo format '{module}:{action}'."""
    bad = await _scalar(
        "SELECT COUNT(*) FROM permissions WHERE code NOT LIKE '%:%'"
    )
    assert bad == 0


async def test_permissions_have_all_actions():
    actions = await _rows(
        "SELECT DISTINCT action FROM permissions ORDER BY action"
    )
    assert {r.action for r in actions} == {"view", "create", "edit", "delete", "export"}


# ── Roles ──────────────────────────────────────────────────────────────────────

_SEED_ROLES = ("'admin'", "'hr_manager'", "'hr_officer'", "'line_manager'", "'finance'")

async def test_roles_count():
    count = await _scalar(f"SELECT COUNT(*) FROM roles WHERE code IN ({','.join(_SEED_ROLES)})")
    assert count == 5


async def test_all_system_roles_exist():
    codes = {r.code for r in await _rows(f"SELECT code FROM roles WHERE code IN ({','.join(_SEED_ROLES)})")}
    assert codes == {"admin", "hr_manager", "hr_officer", "line_manager", "finance"}


async def test_all_roles_are_system():
    non_system = await _scalar(
        f"SELECT COUNT(*) FROM roles WHERE is_system = false AND code IN ({','.join(_SEED_ROLES)})"
    )
    assert non_system == 0


# ── Role-Permissions ───────────────────────────────────────────────────────────

async def test_admin_has_all_permissions():
    admin_count = await _scalar("""
        SELECT COUNT(*) FROM role_permissions rp
        JOIN roles r ON rp.role_id = r.id
        WHERE r.code = 'admin'
    """)
    assert admin_count == 85


async def test_hr_manager_has_org_full_except_export():
    perms = {r.action for r in await _rows("""
        SELECT p.action FROM role_permissions rp
        JOIN roles r ON rp.role_id = r.id
        JOIN permissions p ON rp.permission_id = p.id
        WHERE r.code = 'hr_manager' AND p.module = 'org'
    """)}
    assert perms == {"view", "create", "edit", "delete"}
    assert "export" not in perms


async def test_hr_manager_can_view_audit_logs():
    count = await _scalar("""
        SELECT COUNT(*) FROM role_permissions rp
        JOIN roles r ON rp.role_id = r.id
        JOIN permissions p ON rp.permission_id = p.id
        WHERE r.code = 'hr_manager' AND p.code = 'audit_logs:view'
    """)
    assert count == 1


async def test_hr_manager_has_catalog_full():
    perms = {r.action for r in await _rows("""
        SELECT p.action FROM role_permissions rp
        JOIN roles r ON rp.role_id = r.id
        JOIN permissions p ON rp.permission_id = p.id
        WHERE r.code = 'hr_manager' AND p.module = 'catalog'
    """)}
    assert perms == {"view", "create", "edit", "delete", "export"}


async def test_hr_manager_has_settings_full():
    perms = {r.action for r in await _rows("""
        SELECT p.action FROM role_permissions rp
        JOIN roles r ON rp.role_id = r.id
        JOIN permissions p ON rp.permission_id = p.id
        WHERE r.code = 'hr_manager' AND p.module = 'settings'
    """)}
    assert perms == {"view", "create", "edit", "delete", "export"}


async def test_hr_officer_settings_has_no_delete():
    perms = {r.action for r in await _rows("""
        SELECT p.action FROM role_permissions rp
        JOIN roles r ON rp.role_id = r.id
        JOIN permissions p ON rp.permission_id = p.id
        WHERE r.code = 'hr_officer' AND p.module = 'settings'
    """)}
    assert perms == {"view", "create", "edit"}


async def test_hr_officer_catalog_has_no_delete():
    perms = {r.action for r in await _rows("""
        SELECT p.action FROM role_permissions rp
        JOIN roles r ON rp.role_id = r.id
        JOIN permissions p ON rp.permission_id = p.id
        WHERE r.code = 'hr_officer' AND p.module = 'catalog'
    """)}
    assert perms == {"view", "create", "edit", "export"}


async def test_hr_manager_cannot_manage_users():
    count = await _scalar("""
        SELECT COUNT(*) FROM role_permissions rp
        JOIN roles r ON rp.role_id = r.id
        JOIN permissions p ON rp.permission_id = p.id
        WHERE r.code = 'hr_manager' AND p.module IN ('users', 'roles')
    """)
    assert count == 0


async def test_hr_officer_has_no_delete():
    delete_count = await _scalar("""
        SELECT COUNT(*) FROM role_permissions rp
        JOIN roles r ON rp.role_id = r.id
        JOIN permissions p ON rp.permission_id = p.id
        WHERE r.code = 'hr_officer' AND p.action = 'delete'
    """)
    assert delete_count == 0


async def test_line_manager_limited_modules():
    modules = {r.module for r in await _rows("""
        SELECT DISTINCT p.module FROM role_permissions rp
        JOIN roles r ON rp.role_id = r.id
        JOIN permissions p ON rp.permission_id = p.id
        WHERE r.code = 'line_manager'
    """)}
    assert modules == {
        "org",
        "employees",
        "leaves",
        "performance",
        "rewards",
        "disciplines",
        "reports",
    }


async def test_line_manager_cannot_delete_anything():
    count = await _scalar("""
        SELECT COUNT(*) FROM role_permissions rp
        JOIN roles r ON rp.role_id = r.id
        JOIN permissions p ON rp.permission_id = p.id
        WHERE r.code = 'line_manager' AND p.action = 'delete'
    """)
    assert count == 0


async def test_line_manager_exact_actions_per_module():
    rows = await _rows("""
        SELECT p.module, array_agg(p.action ORDER BY p.action) AS actions
        FROM role_permissions rp
        JOIN roles r ON rp.role_id = r.id
        JOIN permissions p ON rp.permission_id = p.id
        WHERE r.code = 'line_manager'
        GROUP BY p.module
        ORDER BY p.module
    """)
    actual = {row.module: list(row.actions) for row in rows}
    assert actual == {
        "disciplines": ["create", "edit", "view"],
        "employees": ["view"],
        "leaves": ["create", "edit", "view"],
        "org": ["view"],
        "performance": ["create", "edit", "view"],
        "reports": ["export", "view"],
        "rewards": ["create", "edit", "view"],
    }


async def test_finance_only_insurance_salary_reports():
    modules = {r.module for r in await _rows("""
        SELECT DISTINCT p.module FROM role_permissions rp
        JOIN roles r ON rp.role_id = r.id
        JOIN permissions p ON rp.permission_id = p.id
        WHERE r.code = 'finance'
    """)}
    assert modules == {"insurance", "salary", "reports"}


# ── Users ──────────────────────────────────────────────────────────────────────

_SEED_EMAILS = (
    "'admin@hrms.local'", "'hrmanager@hrms.local'", "'hrofficer@hrms.local'",
    "'linemanager@hrms.local'", "'finance@hrms.local'",
)

async def test_seed_users_count():
    count = await _scalar(f"SELECT COUNT(*) FROM users WHERE email IN ({','.join(_SEED_EMAILS)})")
    assert count == 5


async def test_admin_user_is_superuser():
    row = (await _rows(
        "SELECT is_superuser FROM users WHERE email = 'admin@hrms.local'"
    ))[0]
    assert row.is_superuser is True


async def test_non_admin_users_not_superuser():
    count = await _scalar("""
        SELECT COUNT(*) FROM users
        WHERE email IN ('hrmanager@hrms.local', 'hrofficer@hrms.local', 'linemanager@hrms.local', 'finance@hrms.local')
          AND is_superuser = true
    """)
    assert count == 0


async def test_all_users_active():
    inactive = await _scalar(
        f"SELECT COUNT(*) FROM users WHERE is_active = false AND email IN ({','.join(_SEED_EMAILS)})"
    )
    assert inactive == 0


async def test_passwords_are_hashed():
    plain = await _scalar(
        "SELECT COUNT(*) FROM users WHERE hashed_password NOT LIKE '$2b$%'"
    )
    assert plain == 0


# ── User-Roles ─────────────────────────────────────────────────────────────────

async def test_each_user_has_exactly_one_role():
    rows = await _rows(f"""
        SELECT u.email, COUNT(ur.role_id) AS role_count
        FROM users u
        LEFT JOIN user_roles ur ON ur.user_id = u.id
        WHERE u.email IN ({','.join(_SEED_EMAILS)})
        GROUP BY u.email
    """)
    for r in rows:
        assert r.role_count == 1, f"{r.email} nên có đúng 1 role, thực tế: {r.role_count}"


async def test_user_role_assignments():
    expected = {
        "admin@hrms.local":       "admin",
        "hrmanager@hrms.local":   "hr_manager",
        "hrofficer@hrms.local":   "hr_officer",
        "linemanager@hrms.local": "line_manager",
        "finance@hrms.local":     "finance",
    }
    rows = await _rows(f"""
        SELECT u.email, r.code
        FROM user_roles ur
        JOIN users u ON ur.user_id = u.id
        JOIN roles r ON ur.role_id = r.id
        WHERE u.email IN ({','.join(_SEED_EMAILS)})
    """)
    actual = {r.email: r.code for r in rows}
    assert actual == expected


async def test_line_manager_seed_has_department_scope():
    row = (
        await _rows("""
            SELECT ur.scope_type, ur.department_ids
            FROM user_roles ur
            JOIN users u ON ur.user_id = u.id
            JOIN roles r ON ur.role_id = r.id
            WHERE u.email = 'linemanager@hrms.local'
              AND r.code = 'line_manager'
        """)
    )[0]
    assert row.scope_type == "department"
    assert isinstance(row.department_ids, list)
    assert len(row.department_ids) == 1

    dept_row = (
        await _rows("""
            SELECT d.code
            FROM departments d
            WHERE d.id = :department_id
        """, department_id=row.department_ids[0])
    )[0]
    assert dept_row.code == "KS"
