"""Add employee code sequence scaffold tables and backfill SYS1

Revision ID: 0016
Revises: 0015
Create Date: 2026-05-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "employee_code_sequences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("next_value", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("min_digits", sa.SmallInteger(), nullable=False, server_default="4"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_employee_code_sequences_code", "employee_code_sequences", ["code"], unique=True)
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX uq_employee_code_sequences_default_active
            ON employee_code_sequences ((1))
            WHERE is_default = TRUE AND is_active = TRUE
            """
        )
    )

    op.create_table(
        "employee_code_sequence_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scope_type", sa.String(length=20), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=True),
        sa.Column("job_position_id", sa.Integer(), nullable=True),
        sa.Column("employee_code_sequence_id", sa.Integer(), nullable=False),
        sa.Column("apply_to_descendants", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_position_id"], ["job_positions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employee_code_sequence_id"], ["employee_code_sequences.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "scope_type IN ('department', 'job_position')",
            name="ck_employee_code_sequence_rules_scope_type",
        ),
        sa.CheckConstraint(
            "((scope_type = 'department' AND department_id IS NOT NULL AND job_position_id IS NULL) "
            "OR (scope_type = 'job_position' AND job_position_id IS NOT NULL AND department_id IS NULL))",
            name="ck_employee_code_sequence_rules_scope_target",
        ),
    )
    op.create_index(
        "uq_employee_code_sequence_rules_department_active",
        "employee_code_sequence_rules",
        ["department_id"],
        unique=True,
        postgresql_where=sa.text("scope_type = 'department' AND is_active = TRUE"),
    )
    op.create_index(
        "uq_employee_code_sequence_rules_job_position_active",
        "employee_code_sequence_rules",
        ["job_position_id"],
        unique=True,
        postgresql_where=sa.text("scope_type = 'job_position' AND is_active = TRUE"),
    )

    op.add_column(
        "employees",
        sa.Column("employee_code_sequence_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_employees_employee_code_sequence_id",
        "employees",
        "employee_code_sequences",
        ["employee_code_sequence_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_employees_employee_code_sequence_id",
        "employees",
        ["employee_code_sequence_id"],
        unique=False,
    )

    op.create_unique_constraint(
        "uq_employees_id_number",
        "employees",
        ["id_number"],
    )

    op.execute(
        sa.text(
            """
            INSERT INTO employee_code_sequences (code, name, description, next_value, min_digits, is_default, is_active)
            VALUES
              ('SYS1', 'Hệ 1', 'Hệ mặc định toàn công ty', 1, 4, TRUE, TRUE),
              ('SYS2', 'Hệ 2', 'Công nhân bốc xếp / ra cám / tạp vụ', 1, 4, FALSE, TRUE),
              ('SYS3', 'Hệ 3', 'Công nhân / bảo vệ thuộc Phòng trại', 1, 4, FALSE, TRUE)
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE employees
            SET employee_code_sequence_id = seq.id
            FROM employee_code_sequences seq
            WHERE seq.code = 'SYS1'
              AND employees.employee_code_sequence_id IS NULL
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE employee_code_sequences
            SET next_value = (
                SELECT COALESCE(MAX(employee_seq), 0) + 1
                FROM employees
            )
            WHERE code = 'SYS1'
            """
        )
    )


def downgrade() -> None:
    op.drop_constraint("uq_employees_id_number", "employees", type_="unique")
    op.drop_index("ix_employees_employee_code_sequence_id", table_name="employees")
    op.drop_constraint("fk_employees_employee_code_sequence_id", "employees", type_="foreignkey")
    op.drop_column("employees", "employee_code_sequence_id")

    op.drop_index("uq_employee_code_sequence_rules_job_position_active", table_name="employee_code_sequence_rules")
    op.drop_index("uq_employee_code_sequence_rules_department_active", table_name="employee_code_sequence_rules")
    op.drop_table("employee_code_sequence_rules")

    op.drop_index("uq_employee_code_sequences_default_active", table_name="employee_code_sequences")
    op.drop_index("ix_employee_code_sequences_code", table_name="employee_code_sequences")
    op.drop_table("employee_code_sequences")
