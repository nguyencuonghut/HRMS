"""add department heads

Revision ID: 0059
Revises: 0058
Create Date: 2026-06-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0059"
down_revision: Union[str, None] = "0058"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "department_heads",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("head_role_label", sa.String(length=100), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("changed_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_department_heads_department_id", "department_heads", ["department_id"])
    op.create_index("ix_department_heads_employee_id", "department_heads", ["employee_id"])
    op.create_index(
        "uq_department_head_current",
        "department_heads",
        ["department_id"],
        unique=True,
        postgresql_where=sa.text("is_current = TRUE"),
    )


def downgrade() -> None:
    op.drop_index("uq_department_head_current", table_name="department_heads")
    op.drop_index("ix_department_heads_employee_id", table_name="department_heads")
    op.drop_index("ix_department_heads_department_id", table_name="department_heads")
    op.drop_table("department_heads")
