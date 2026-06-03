"""add contract bhxh mode metadata

Revision ID: 0056
Revises: 0055
Create Date: 2026-06-03 22:40:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0056"
down_revision: Union[str, None] = "0055"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "employee_contracts",
        sa.Column(
            "insurance_salary_mode",
            sa.String(length=40),
            nullable=False,
            server_default="fixed_manual",
        ),
    )
    op.add_column(
        "employee_contracts",
        sa.Column("bhxh_position_group_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "employee_contracts",
        sa.Column("insurance_salary_grade_no", sa.SmallInteger(), nullable=True),
    )
    op.add_column(
        "employee_contracts",
        sa.Column("insurance_salary_fixed_amount", sa.Numeric(18, 2), nullable=True),
    )
    op.create_foreign_key(
        "fk_employee_contracts_bhxh_position_group",
        "employee_contracts",
        "bhxh_position_groups",
        ["bhxh_position_group_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_employee_contracts_bhxh_position_group_id",
        "employee_contracts",
        ["bhxh_position_group_id"],
    )
    op.create_index(
        "ix_employee_contracts_insurance_salary_mode",
        "employee_contracts",
        ["insurance_salary_mode"],
    )

    op.execute(
        sa.text(
            """
            UPDATE employee_contracts
            SET insurance_salary_mode = 'fixed_manual',
                insurance_salary_fixed_amount = insurance_salary
            """
        )
    )

    op.alter_column(
        "employee_contracts",
        "insurance_salary_mode",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_index("ix_employee_contracts_insurance_salary_mode", table_name="employee_contracts")
    op.drop_index("ix_employee_contracts_bhxh_position_group_id", table_name="employee_contracts")
    op.drop_constraint(
        "fk_employee_contracts_bhxh_position_group",
        "employee_contracts",
        type_="foreignkey",
    )
    op.drop_column("employee_contracts", "insurance_salary_fixed_amount")
    op.drop_column("employee_contracts", "insurance_salary_grade_no")
    op.drop_column("employee_contracts", "bhxh_position_group_id")
    op.drop_column("employee_contracts", "insurance_salary_mode")
