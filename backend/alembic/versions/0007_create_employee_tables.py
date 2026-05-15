"""Create employee tables and add display_prefix to departments

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Thêm display_prefix vào departments ───────────────────────────
    op.add_column(
        "departments",
        sa.Column("display_prefix", sa.String(length=5), nullable=True),
    )

    # ── 2. Bảng employees ────────────────────────────────────────────────
    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),

        # Mã số nhân viên — tự tăng trong service (không dùng SERIAL)
        sa.Column("employee_seq", sa.Integer(), nullable=False),

        # Họ tên
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("normalized_name", sa.String(length=200), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),

        # Cá nhân
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("gender", sa.String(length=10), nullable=False),
        sa.Column(
            "nationality_id",
            sa.Integer(),
            sa.ForeignKey("nationalities.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "ethnicity_id",
            sa.Integer(),
            sa.ForeignKey("ethnicities.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "religion_id",
            sa.Integer(),
            sa.ForeignKey("religions.id", ondelete="SET NULL"),
            nullable=True,
        ),

        # Giấy tờ nhận dạng
        sa.Column("id_number", sa.String(length=20), nullable=False),
        sa.Column("id_issued_on", sa.Date(), nullable=False),
        sa.Column("id_issued_by", sa.String(length=200), nullable=False),
        sa.Column("id_expires_on", sa.Date(), nullable=True),

        # Hộ chiếu
        sa.Column("passport_number", sa.String(length=50), nullable=True),
        sa.Column("passport_issued_on", sa.Date(), nullable=True),
        sa.Column("passport_expires_on", sa.Date(), nullable=True),

        # Giấy phép lao động
        sa.Column("work_permit_number", sa.String(length=50), nullable=True),
        sa.Column("work_permit_issued_on", sa.Date(), nullable=True),
        sa.Column("work_permit_expires_on", sa.Date(), nullable=True),

        # Liên lạc & thuế
        sa.Column("phone_number", sa.String(length=20), nullable=True),
        sa.Column("personal_email", sa.String(length=200), nullable=True),
        sa.Column("personal_tax_code", sa.String(length=20), nullable=True),
        sa.Column("bhxh_code", sa.String(length=20), nullable=True),

        # Ảnh thẻ
        sa.Column("avatar_path", sa.String(length=500), nullable=True),

        # Trạng thái
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="probation",
        ),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("resigned_date", sa.Date(), nullable=True),

        # Liên kết tài khoản hệ thống (1-1, nullable)
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            unique=True,
        ),

        # Audit
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_employees_employee_seq", "employees", ["employee_seq"], unique=True)
    op.create_index("ix_employees_normalized_name", "employees", ["normalized_name"], unique=False)
    op.create_index("ix_employees_id_number", "employees", ["id_number"], unique=False)
    op.create_index("ix_employees_status", "employees", ["status"], unique=False)
    op.create_index("ix_employees_is_active", "employees", ["is_active"], unique=False)

    # ── 3. Bảng employee_addresses ───────────────────────────────────────
    op.create_table(
        "employee_addresses",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "employee_id",
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("address_type", sa.String(length=20), nullable=False),

        # Hệ mới
        sa.Column(
            "new_province_unit_id",
            sa.Integer(),
            sa.ForeignKey("administrative_units.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "new_district_unit_id",
            sa.Integer(),
            sa.ForeignKey("administrative_units.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "new_ward_unit_id",
            sa.Integer(),
            sa.ForeignKey("administrative_units.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("new_address_line", sa.String(length=500), nullable=True),

        # Hệ cũ
        sa.Column(
            "old_province_unit_id",
            sa.Integer(),
            sa.ForeignKey("administrative_units.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "old_district_unit_id",
            sa.Integer(),
            sa.ForeignKey("administrative_units.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "old_ward_unit_id",
            sa.Integer(),
            sa.ForeignKey("administrative_units.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("old_address_line", sa.String(length=500), nullable=True),

        sa.Column("full_address_text", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),

        sa.UniqueConstraint("employee_id", "address_type", name="uq_employee_address_type"),
    )
    op.create_index("ix_employee_addresses_employee_id", "employee_addresses", ["employee_id"], unique=False)

    # ── 4. Bảng employee_bank_accounts ───────────────────────────────────
    op.create_table(
        "employee_bank_accounts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "employee_id",
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "bank_id",
            sa.Integer(),
            sa.ForeignKey("banks.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("account_number", sa.String(length=50), nullable=False),
        sa.Column("account_name", sa.String(length=200), nullable=False),
        sa.Column("branch_name", sa.String(length=200), nullable=True),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_employee_bank_accounts_employee_id",
        "employee_bank_accounts",
        ["employee_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_employee_bank_accounts_employee_id", table_name="employee_bank_accounts")
    op.drop_table("employee_bank_accounts")

    op.drop_index("ix_employee_addresses_employee_id", table_name="employee_addresses")
    op.drop_table("employee_addresses")

    op.drop_index("ix_employees_is_active", table_name="employees")
    op.drop_index("ix_employees_status", table_name="employees")
    op.drop_index("ix_employees_id_number", table_name="employees")
    op.drop_index("ix_employees_normalized_name", table_name="employees")
    op.drop_index("ix_employees_employee_seq", table_name="employees")
    op.drop_table("employees")

    op.drop_column("departments", "display_prefix")
