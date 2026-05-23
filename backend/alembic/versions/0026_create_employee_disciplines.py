"""Create employee_disciplines table

Revision ID: 0026
Revises: 0025
Create Date: 2026-05-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0026"
down_revision: Union[str, None] = "0025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "employee_disciplines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("discipline_form", sa.String(length=50), nullable=False),
        sa.Column("violation_date", sa.Date(), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("extended_months", sa.SmallInteger(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("decision_number", sa.String(length=100), nullable=True),
        sa.Column("issued_by", sa.String(length=200), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("file_path", sa.String(length=500), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "discipline_form IN ('khien_trach','keo_dai_nang_luong','cach_chuc','sa_thai')",
            name="chk_discipline_form",
        ),
        sa.CheckConstraint(
            "(discipline_form = 'keo_dai_nang_luong' AND extended_months IS NOT NULL)"
            " OR (discipline_form != 'keo_dai_nang_luong' AND extended_months IS NULL)",
            name="chk_discipline_extended_months",
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_discipline_employee_date", "employee_disciplines",
                    ["employee_id", sa.text("effective_date DESC")])
    op.create_index("ix_discipline_form_date", "employee_disciplines",
                    ["discipline_form", "effective_date"])
    op.create_index("ix_discipline_decision_number", "employee_disciplines",
                    ["decision_number"],
                    postgresql_where=sa.text("decision_number IS NOT NULL"))


def downgrade() -> None:
    op.drop_index("ix_discipline_decision_number", table_name="employee_disciplines")
    op.drop_index("ix_discipline_form_date", table_name="employee_disciplines")
    op.drop_index("ix_discipline_employee_date", table_name="employee_disciplines")
    op.drop_table("employee_disciplines")
