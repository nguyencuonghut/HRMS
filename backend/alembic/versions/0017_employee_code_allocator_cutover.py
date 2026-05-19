"""Cut over employee code allocation to per-sequence counters

Revision ID: 0017
Revises: 0016
Create Date: 2026-05-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE employee_code_sequences seq
            SET next_value = COALESCE((
                SELECT MAX(e.employee_seq) + 1
                FROM employees e
                WHERE e.employee_code_sequence_id = seq.id
            ), 1)
            """
        )
    )

    op.alter_column("employees", "employee_code_sequence_id", existing_type=sa.Integer(), nullable=False)

    op.drop_index("ix_employees_employee_seq", table_name="employees")
    op.create_index("ix_employees_employee_seq", "employees", ["employee_seq"], unique=False)

    op.create_unique_constraint(
        "uq_employees_sequence_seq",
        "employees",
        ["employee_code_sequence_id", "employee_seq"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_employees_sequence_seq", "employees", type_="unique")

    op.drop_index("ix_employees_employee_seq", table_name="employees")
    op.create_index("ix_employees_employee_seq", "employees", ["employee_seq"], unique=True)

    op.alter_column("employees", "employee_code_sequence_id", existing_type=sa.Integer(), nullable=True)
