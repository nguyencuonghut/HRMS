"""Create reward_types and employee_rewards tables

Revision ID: 0025
Revises: 0024
Create Date: 2026-05-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0025"
down_revision: Union[str, None] = "0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── reward_types ─────────────────────────────────────────────────────────
    op.create_table(
        "reward_types",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("is_monetary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_reward_type_code"),
    )
    op.create_index("ix_reward_types_is_active", "reward_types", ["is_active"])

    # Seed 4 default types
    op.execute("""
        INSERT INTO reward_types (code, name, is_monetary, sort_order) VALUES
        ('bang_khen',       N'Bằng khen',        false, 1),
        ('giai_khen',       N'Giấy khen',         false, 2),
        ('thuong_tien',     N'Thưởng tiền',       true,  3),
        ('thuong_hien_vat', N'Thưởng hiện vật',   false, 4)
    """)

    # ── employee_rewards ──────────────────────────────────────────────────────
    op.create_table(
        "employee_rewards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("reward_type_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reward_date", sa.Date(), nullable=False),
        sa.Column("decision_number", sa.String(length=100), nullable=True),
        sa.Column("issued_by", sa.String(length=200), nullable=True),
        sa.Column("value", sa.Numeric(18, 2), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("file_path", sa.String(length=500), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reward_type_id"], ["reward_types.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_er_employee_id", "employee_rewards", ["employee_id"])
    op.create_index("ix_er_reward_date", "employee_rewards", ["reward_date"])
    op.create_index("ix_er_reward_type_id", "employee_rewards", ["reward_type_id"])


def downgrade() -> None:
    op.drop_index("ix_er_reward_type_id", table_name="employee_rewards")
    op.drop_index("ix_er_reward_date", table_name="employee_rewards")
    op.drop_index("ix_er_employee_id", table_name="employee_rewards")
    op.drop_table("employee_rewards")
    op.drop_index("ix_reward_types_is_active", table_name="reward_types")
    op.drop_table("reward_types")
