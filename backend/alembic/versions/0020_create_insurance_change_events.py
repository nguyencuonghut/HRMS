"""Create insurance_change_events + add bhyt_initial_clinic_code to profiles

Revision ID: 0020
Revises: 0019
Create Date: 2026-05-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0020"
down_revision: Union[str, None] = "0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Thêm mã KCB ban đầu vào hồ sơ bảo hiểm nhân viên ─────────────────
    op.add_column(
        "employee_insurance_profiles",
        sa.Column("bhyt_initial_clinic_code", sa.String(length=20), nullable=True),
    )

    # ── Bảng sổ cái biến động tăng/giảm BHXH ─────────────────────────────
    op.create_table(
        "insurance_change_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),

        # Thông tin biến động
        sa.Column("change_type", sa.String(length=10), nullable=False),
        sa.Column("change_reason", sa.String(length=50), nullable=False),
        sa.Column("ibhxh_reason_code", sa.String(length=5), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("period_year", sa.SmallInteger(), nullable=False),
        sa.Column("period_month", sa.SmallInteger(), nullable=False),

        # Snapshot nhân viên
        sa.Column("employee_name_snapshot", sa.String(length=255), nullable=False),
        sa.Column("date_of_birth_snapshot", sa.Date(), nullable=False),
        sa.Column("gender_snapshot", sa.String(length=10), nullable=False),
        sa.Column("nationality_code_snapshot", sa.String(length=10), nullable=False,
                  server_default="VN"),
        sa.Column("identity_number_snapshot", sa.String(length=25), nullable=True),

        # Snapshot hợp đồng
        sa.Column("contract_number_snapshot", sa.String(length=100), nullable=True),
        sa.Column("contract_type_code_snapshot", sa.String(length=5), nullable=True),
        sa.Column("contract_signed_date_snapshot", sa.Date(), nullable=True),
        sa.Column("contract_from_snapshot", sa.Date(), nullable=True),
        sa.Column("contract_to_snapshot", sa.Date(), nullable=True),

        # Snapshot bảo hiểm
        sa.Column("bhxh_code_snapshot", sa.String(length=20), nullable=True),
        sa.Column("basis_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("allowances_amount", sa.Numeric(18, 2), nullable=False,
                  server_default="0"),
        sa.Column("bhyt_clinic_name_snapshot", sa.String(length=255), nullable=True),
        sa.Column("bhyt_clinic_code_snapshot", sa.String(length=20), nullable=True),
        sa.Column("policy_version_code_snapshot", sa.String(length=50), nullable=True),
        sa.Column("employee_rate_total_snapshot", sa.Numeric(8, 4), nullable=False,
                  server_default="0"),
        sa.Column("employer_rate_total_snapshot", sa.Numeric(8, 4), nullable=False,
                  server_default="0"),

        # Trạng thái cũ/mới
        sa.Column("old_status", sa.String(length=20), nullable=True),
        sa.Column("new_status", sa.String(length=20), nullable=False),

        # Tháng kê khai gợi ý (dùng bởi 6.4)
        sa.Column("suggested_declaration_year", sa.SmallInteger(), nullable=False),
        sa.Column("suggested_declaration_month", sa.SmallInteger(), nullable=False),

        # Metadata
        sa.Column("is_manual", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False,
                  server_default=sa.text("now()")),

        # PK
        sa.PrimaryKeyConstraint("id"),

        # FK
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),

        # Constraints
        sa.CheckConstraint(
            "change_type IN ('increase', 'decrease')",
            name="ck_ice_change_type",
        ),
        sa.CheckConstraint(
            "change_reason IN ("
            "'new_hire', 'return_from_leave', 'transfer_in', 'contract_renewal', "
            "'resignation', 'contract_end', 'dismissal', "
            "'unpaid_leave', 'maternity_no_contribution', 'long_term_sick', 'transfer_out', "
            "'manual_correction'"
            ")",
            name="ck_ice_change_reason",
        ),
        sa.CheckConstraint("period_month BETWEEN 1 AND 12", name="ck_ice_period_month"),
        sa.CheckConstraint(
            "suggested_declaration_month BETWEEN 1 AND 12",
            name="ck_ice_suggested_month",
        ),
        sa.CheckConstraint("basis_amount > 0", name="ck_ice_basis_positive"),
        sa.CheckConstraint("allowances_amount >= 0", name="ck_ice_allowances_non_negative"),
    )

    op.create_index("ix_ice_employee_id", "insurance_change_events", ["employee_id"])
    op.create_index(
        "ix_ice_period",
        "insurance_change_events",
        ["period_year", "period_month"],
    )
    op.create_index(
        "ix_ice_suggested_declaration",
        "insurance_change_events",
        ["suggested_declaration_year", "suggested_declaration_month"],
    )
    op.create_index(
        "ix_ice_effective_date", "insurance_change_events", ["effective_date"]
    )
    op.create_index("ix_ice_change_type", "insurance_change_events", ["change_type"])
    op.create_index(
        "ix_ice_ibhxh_code", "insurance_change_events", ["ibhxh_reason_code"]
    )


def downgrade() -> None:
    op.drop_index("ix_ice_ibhxh_code", table_name="insurance_change_events")
    op.drop_index("ix_ice_change_type", table_name="insurance_change_events")
    op.drop_index("ix_ice_effective_date", table_name="insurance_change_events")
    op.drop_index("ix_ice_suggested_declaration", table_name="insurance_change_events")
    op.drop_index("ix_ice_period", table_name="insurance_change_events")
    op.drop_index("ix_ice_employee_id", table_name="insurance_change_events")
    op.drop_table("insurance_change_events")

    op.drop_column("employee_insurance_profiles", "bhyt_initial_clinic_code")
