"""Tạo bảng xác thực và phân quyền (RBAC)

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-13

Bảng được tạo (6 bảng):
  Xác thực & Phân quyền:
    - users              Tài khoản người dùng (email làm login identifier)
    - roles              Vai trò hệ thống
    - permissions        Quyền hạn theo format {module}:{action}
    - role_permissions   Many-to-many: Role ↔ Permission
    - user_roles         Many-to-many: User ↔ Role (với phạm vi tổ chức)
    - audit_logs         Nhật ký thao tác toàn hệ thống

Thay đổi bảng hiện có:
    - org_change_logs.changed_by → thêm FK → users.id (ON DELETE SET NULL)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ──────────────────────────────────────────────────────────────────────
    # 1. users — Tài khoản người dùng hệ thống
    #    Email là định danh đăng nhập (không dùng username).
    #    is_superuser=True → bypass mọi permission check.
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        # Email là login identifier — duy nhất trong hệ thống
        sa.Column("email", sa.String(200), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        # Mật khẩu đã hash (bcrypt) — không bao giờ lưu plain text
        sa.Column("hashed_password", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        # Superuser: bypass mọi permission check, chỉ dùng cho admin hệ thống
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default="false"),
        # Liên kết hồ sơ nhân viên — NULL nếu chưa liên kết (Phase 2)
        sa.Column("employee_id", sa.Integer(), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ──────────────────────────────────────────────────────────────────────
    # 2. roles — Vai trò hệ thống
    #    is_system=True → không xóa được qua API (admin, hr_manager, ...).
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        # Mã định danh bất biến — VD: 'admin', 'hr_manager', 'finance'
        sa.Column("code", sa.String(50), nullable=False),
        # Tên hiển thị — VD: 'Quản trị viên', 'HR Manager'
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        # TRUE = role mặc định của hệ thống, không xóa được
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("code", name="uq_roles_code"),
    )
    op.create_index("ix_roles_code", "roles", ["code"], unique=True)

    # ──────────────────────────────────────────────────────────────────────
    # 3. permissions — Quyền hạn theo format '{module}:{action}'
    #    Seeded, KHÔNG sửa qua UI. Permissions là code contract.
    #    VD: 'employees:view', 'contracts:export', 'users:delete'
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        # '{module}:{action}' — định danh duy nhất dùng trong code
        sa.Column("code", sa.String(100), nullable=False),
        # Tên hiển thị cho UI permission matrix
        sa.Column("name", sa.String(200), nullable=False),
        # Module/chức năng: 'org', 'employees', 'contracts', 'leaves', ...
        sa.Column("module", sa.String(50), nullable=False),
        # Hành động: 'view', 'create', 'edit', 'delete', 'export'
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.UniqueConstraint("code", name="uq_permissions_code"),
    )
    op.create_index("ix_permissions_code", "permissions", ["code"], unique=True)
    op.create_index("ix_permissions_module", "permissions", ["module"])

    # ──────────────────────────────────────────────────────────────────────
    # 4. role_permissions — Bảng trung gian Role ↔ Permission
    #    Cascade xóa khi role hoặc permission bị xóa.
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("role_id", "permission_id", name="pk_role_permissions"),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"],
            name="fk_role_permissions_role",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"], ["permissions.id"],
            name="fk_role_permissions_permission",
            ondelete="CASCADE",
        ),
    )

    # ──────────────────────────────────────────────────────────────────────
    # 5. user_roles — Bảng trung gian User ↔ Role (với phạm vi tổ chức)
    #    scope_type NULL = toàn công ty.
    #    scope_type 'department' → department_ids chứa danh sách phòng ban
    #    được phép (dùng cho Line Manager giới hạn phòng ban).
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        # NULL = toàn công ty | 'company' | 'department'
        sa.Column("scope_type", sa.String(20), nullable=True),
        # Danh sách ID phòng ban cho phạm vi 'department'
        sa.Column("department_ids", ARRAY(sa.Integer()), nullable=True),
        sa.PrimaryKeyConstraint("user_id", "role_id", name="pk_user_roles"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_user_roles_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"],
            name="fk_user_roles_role",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"])

    # ──────────────────────────────────────────────────────────────────────
    # 6. audit_logs — Nhật ký thao tác toàn hệ thống
    #    BigInteger PK để đáp ứng lượng lớn bản ghi dài hạn.
    #    Không bao giờ xóa/sửa dòng cũ (immutable log).
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        # Người thực hiện — NULL nếu chưa đăng nhập hoặc system action
        sa.Column("user_id", sa.Integer(), nullable=True),
        # LOGIN | CREATE | UPDATE | DELETE | EXPORT | RESET_PASSWORD | VIEW_SENSITIVE
        sa.Column("action", sa.String(50), nullable=False),
        # Loại đối tượng bị tác động: 'employee', 'contract', 'user', 'role', ...
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        # Snapshot tên đối tượng tại thời điểm thao tác (giữ lại kể cả khi đã xóa)
        sa.Column("entity_name", sa.String(200), nullable=True),
        # Dữ liệu trước khi thay đổi
        sa.Column("old_data", JSONB, nullable=True),
        # Dữ liệu sau khi thay đổi
        sa.Column("new_data", JSONB, nullable=True),
        # Địa chỉ IP (IPv4 hoặc IPv6)
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # FK → users.id với SET NULL để giữ log kể cả khi user bị xóa
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_audit_logs_user",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    # ──────────────────────────────────────────────────────────────────────
    # 7. Thêm FK thực vào org_change_logs.changed_by → users.id
    #    ON DELETE SET NULL: giữ log kể cả khi user bị xóa
    # ──────────────────────────────────────────────────────────────────────
    op.create_foreign_key(
        "fk_org_change_logs_changed_by",
        "org_change_logs", "users",
        ["changed_by"], ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_org_change_logs_changed_by", "org_change_logs", type_="foreignkey")

    op.drop_table("audit_logs")
    op.drop_table("user_roles")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("users")
