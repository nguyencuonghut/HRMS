"""add recruitment_channels and job_postings tables.

Revision ID: 0034
Revises: 0033
Create Date: 2026-05-25
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Danh mục kênh tuyển dụng
    op.create_table(
        "recruitment_channels",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False, server_default="0"),
    )

    # Seed mặc định
    op.execute("""
        INSERT INTO recruitment_channels (code, name, sort_order) VALUES
        ('internal',     'Tuyển nội bộ',        1),
        ('referral',     'Giới thiệu nội bộ',    2),
        ('zalo',         'Zalo',                  3),
        ('facebook',     'Facebook',              4),
        ('company_web',  'Website công ty',       5),
        ('topcv',        'TopCV',                 6),
        ('vietnamworks', 'VietnamWorks',           7),
        ('vietnamjobs',  'VietnamJobs',            8),
        ('linkedin',     'LinkedIn',               9),
        ('headhunter',   'Headhunter / Agency',    10),
        ('other',        'Khác',                   11)
    """)

    # 2. Tin tuyển dụng
    op.create_table(
        "job_postings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "job_requisition_id", sa.Integer(),
            sa.ForeignKey("job_requisitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("requirements", sa.Text(), nullable=True),
        sa.Column("benefits", sa.Text(), nullable=True),
        sa.Column("work_location", sa.String(300), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("salary_display", sa.String(100), nullable=True),
        sa.Column("posting_type", sa.String(20), nullable=False, server_default="external"),
        sa.Column("channels", sa.ARRAY(sa.Integer()), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("opened_at", sa.DateTime(), nullable=True),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_by_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_job_postings_jr", "job_postings", ["job_requisition_id"])
    op.create_index("ix_job_postings_status", "job_postings", ["status"])


def downgrade() -> None:
    op.drop_index("ix_job_postings_status", "job_postings")
    op.drop_index("ix_job_postings_jr", "job_postings")
    op.drop_table("job_postings")
    op.drop_table("recruitment_channels")
