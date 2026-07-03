"""Create employee_relatives table

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "employee_relatives",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),

        sa.Column(
            "employee_id",
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
        ),

        # ── Thông tin cơ bản ─────────────────────────────────────────
        sa.Column("full_name", sa.String(length=200), nullable=False),
        # vo | chong | cha | me | con | anh | chi | em | khac
        sa.Column("relationship_type", sa.String(length=20), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("occupation", sa.String(length=200), nullable=True),
        sa.Column("phone_number", sa.String(length=20), nullable=True),
        sa.Column(
            "participates_in_health_care_insurance",
            sa.Boolean(),
            nullable=False,
            server_default="FALSE",
        ),

        # ── Liên hệ khẩn cấp ─────────────────────────────────────────
        sa.Column(
            "is_emergency_contact",
            sa.Boolean(),
            nullable=False,
            server_default="FALSE",
        ),

        # ── Ghi chú & Audit ──────────────────────────────────────────
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    op.create_index("ix_employee_relatives_employee_id", "employee_relatives", ["employee_id"])


def downgrade() -> None:
    op.drop_index("ix_employee_relatives_employee_id", table_name="employee_relatives")
    op.drop_table("employee_relatives")
