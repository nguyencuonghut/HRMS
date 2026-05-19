"""Create leave_records table

Revision ID: 0015
Revises: 0014
Create Date: 2026-05-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "leave_records",
        sa.Column("id",              sa.Integer(),                     nullable=False),
        sa.Column("employee_id",     sa.Integer(),                     nullable=False),
        sa.Column("leave_type_id",   sa.Integer(),                     nullable=False),
        sa.Column("entitlement_id",  sa.Integer(),                     nullable=True),
        sa.Column("start_date",      sa.Date(),                        nullable=False),
        sa.Column("end_date",        sa.Date(),                        nullable=False),
        sa.Column("start_half",      sa.String(2),                     nullable=True),
        sa.Column("end_half",        sa.String(2),                     nullable=True),
        sa.Column("total_days",      sa.Numeric(precision=5, scale=1), nullable=False),
        sa.Column("reason",          sa.Text(),                        nullable=True),
        sa.Column("status",          sa.String(20),                    nullable=False, server_default="active"),
        sa.Column("cancel_reason",   sa.Text(),                        nullable=True),
        sa.Column("note",            sa.Text(),                        nullable=True),
        sa.Column("created_by_id",   sa.Integer(),                     nullable=True),
        sa.Column("created_at",      sa.TIMESTAMP(timezone=True),      nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at",      sa.TIMESTAMP(timezone=True),      nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["employee_id"],    ["employees.id"],          ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["leave_type_id"],  ["leave_types.id"],        ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["entitlement_id"], ["leave_entitlements.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"],  ["users.id"],              ondelete="SET NULL"),
    )
    op.create_index("ix_leave_records_employee_dates", "leave_records", ["employee_id", "start_date", "end_date"])
    op.create_index("ix_leave_records_leave_type_date", "leave_records", ["leave_type_id", "start_date"])
    op.create_index("ix_leave_records_entitlement",    "leave_records", ["entitlement_id"])


def downgrade() -> None:
    op.drop_index("ix_leave_records_entitlement",     table_name="leave_records")
    op.drop_index("ix_leave_records_leave_type_date", table_name="leave_records")
    op.drop_index("ix_leave_records_employee_dates",  table_name="leave_records")
    op.drop_table("leave_records")
