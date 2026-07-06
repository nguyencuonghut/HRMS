"""add bhxh position groups

Revision ID: 0055
Revises: 0054
Create Date: 2026-06-03 20:40:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0055"
down_revision = "0054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bhxh_position_groups",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("code", name="uq_bhxh_position_groups_code"),
    )
    op.create_index(
        "ix_bhxh_position_groups_code",
        "bhxh_position_groups",
        ["code"],
        unique=False,
    )

    op.create_table(
        "bhxh_position_group_members",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("bhxh_position_group_id", sa.Integer(), nullable=False),
        sa.Column("job_position_id", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["bhxh_position_group_id"],
            ["bhxh_position_groups.id"],
            name="fk_bhxh_position_group_members_group",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["job_position_id"],
            ["job_positions.id"],
            name="fk_bhxh_position_group_members_position",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("job_position_id", name="uq_bhxh_position_group_members_position"),
    )
    op.create_index(
        "ix_bhxh_position_group_members_group",
        "bhxh_position_group_members",
        ["bhxh_position_group_id"],
        unique=False,
    )

    op.add_column(
        "salary_scale_entries",
        sa.Column("bhxh_position_group_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_salary_scale_entries_bhxh_position_group",
        "salary_scale_entries",
        "bhxh_position_groups",
        ["bhxh_position_group_id"],
        ["id"],
    )
    op.alter_column("salary_scale_entries", "job_title_id", existing_type=sa.Integer(), nullable=True)

    op.drop_index("ix_salary_scale_entries_lookup", table_name="salary_scale_entries")
    op.drop_constraint("uq_salary_scale_entries", "salary_scale_entries", type_="unique")

    op.create_index(
        "uq_salary_scale_entries_group",
        "salary_scale_entries",
        ["salary_scale_id", "bhxh_position_group_id", "grade_no"],
        unique=True,
        postgresql_where=sa.text("bhxh_position_group_id IS NOT NULL"),
    )
    op.create_index(
        "uq_salary_scale_entries_job_title_legacy",
        "salary_scale_entries",
        ["salary_scale_id", "job_title_id", "grade_no"],
        unique=True,
        postgresql_where=sa.text("job_title_id IS NOT NULL"),
    )
    op.create_index(
        "ix_salary_scale_entries_group_lookup",
        "salary_scale_entries",
        ["salary_scale_id", "bhxh_position_group_id", "grade_no"],
        unique=False,
        postgresql_where=sa.text("bhxh_position_group_id IS NOT NULL"),
    )
    op.create_index(
        "ix_salary_scale_entries_title_lookup_legacy",
        "salary_scale_entries",
        ["salary_scale_id", "job_title_id", "grade_no"],
        unique=False,
        postgresql_where=sa.text("job_title_id IS NOT NULL"),
    )
    op.create_check_constraint(
        "ck_salary_scale_entries_scope",
        "salary_scale_entries",
        "(job_title_id IS NOT NULL AND bhxh_position_group_id IS NULL) OR "
        "(job_title_id IS NULL AND bhxh_position_group_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_salary_scale_entries_scope", "salary_scale_entries", type_="check")
    op.drop_index("ix_salary_scale_entries_title_lookup_legacy", table_name="salary_scale_entries")
    op.drop_index("ix_salary_scale_entries_group_lookup", table_name="salary_scale_entries")
    op.drop_index("uq_salary_scale_entries_job_title_legacy", table_name="salary_scale_entries")
    op.drop_index("uq_salary_scale_entries_group", table_name="salary_scale_entries")
    op.execute("DELETE FROM salary_scale_entries WHERE job_title_id IS NULL")
    op.alter_column("salary_scale_entries", "job_title_id", existing_type=sa.Integer(), nullable=False)
    op.drop_constraint(
        "fk_salary_scale_entries_bhxh_position_group",
        "salary_scale_entries",
        type_="foreignkey",
    )
    op.drop_column("salary_scale_entries", "bhxh_position_group_id")

    op.create_unique_constraint(
        "uq_salary_scale_entries",
        "salary_scale_entries",
        ["salary_scale_id", "job_title_id", "grade_no"],
    )
    op.create_index(
        "ix_salary_scale_entries_lookup",
        "salary_scale_entries",
        ["salary_scale_id", "job_title_id", "grade_no"],
        unique=False,
    )

    op.drop_index("ix_bhxh_position_group_members_group", table_name="bhxh_position_group_members")
    op.drop_table("bhxh_position_group_members")
    op.drop_index("ix_bhxh_position_groups_code", table_name="bhxh_position_groups")
    op.drop_table("bhxh_position_groups")
