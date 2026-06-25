"""add department job position mappings

Revision ID: 0062
Revises: 0061
Create Date: 2026-06-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0062"
down_revision: Union[str, None] = "0061"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "department_job_positions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("job_position_id", sa.Integer(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name="fk_department_job_positions_department",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["job_position_id"],
            ["job_positions.id"],
            name="fk_department_job_positions_job_position",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "department_id",
            "job_position_id",
            name="uq_department_job_positions",
        ),
    )
    op.create_index(
        "ix_department_job_positions_department_id",
        "department_job_positions",
        ["department_id"],
        unique=False,
    )
    op.create_index(
        "ix_department_job_positions_job_position_id",
        "department_job_positions",
        ["job_position_id"],
        unique=False,
    )

    op.execute(
        """
        INSERT INTO department_job_positions (
            department_id,
            job_position_id,
            is_active,
            created_at,
            updated_at
        )
        SELECT
            department_id,
            id,
            true,
            created_at,
            updated_at
        FROM job_positions
        WHERE deleted_at IS NULL
        ON CONFLICT (department_id, job_position_id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_department_job_positions_job_position_id",
        table_name="department_job_positions",
    )
    op.drop_index(
        "ix_department_job_positions_department_id",
        table_name="department_job_positions",
    )
    op.drop_table("department_job_positions")
