"""Create leave_entitlements table

Revision ID: 0014
Revises: 0013
Create Date: 2026-05-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "leave_entitlements",
        sa.Column("id",                sa.Integer(),                            nullable=False),
        sa.Column("employee_id",       sa.Integer(),                            nullable=False),
        sa.Column("leave_type_id",     sa.Integer(),                            nullable=False),
        sa.Column("year",              sa.Integer(),                            nullable=False),
        sa.Column("allocated_days",    sa.Numeric(precision=5, scale=1),        nullable=False, server_default="0"),
        sa.Column("carryover_days",    sa.Numeric(precision=5, scale=1),        nullable=False, server_default="0"),
        sa.Column("carryover_expires", sa.Date(),                               nullable=True),
        sa.Column("used_days",         sa.Numeric(precision=5, scale=1),        nullable=False, server_default="0"),
        sa.Column("note",              sa.Text(),                               nullable=True),
        sa.Column("created_by_id",     sa.Integer(),                            nullable=True),
        sa.Column("created_at",        sa.TIMESTAMP(timezone=True),             nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at",        sa.TIMESTAMP(timezone=True),             nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["employee_id"],   ["employees.id"],   ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["leave_type_id"], ["leave_types.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"],       ondelete="SET NULL"),
        sa.UniqueConstraint("employee_id", "leave_type_id", "year", name="uq_leave_entitlement"),
    )
    op.create_index("ix_leave_entitlements_employee_year",      "leave_entitlements", ["employee_id", "year"])
    op.create_index("ix_leave_entitlements_carryover_expires",  "leave_entitlements", ["carryover_expires"])


def downgrade() -> None:
    op.drop_index("ix_leave_entitlements_carryover_expires", table_name="leave_entitlements")
    op.drop_index("ix_leave_entitlements_employee_year",     table_name="leave_entitlements")
    op.drop_table("leave_entitlements")
