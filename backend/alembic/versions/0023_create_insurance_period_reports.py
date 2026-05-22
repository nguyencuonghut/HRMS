"""Create insurance_period_reports and insurance_report_line_items

Revision ID: 0023
Revises: 0022
Create Date: 2026-05-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0023"
down_revision: Union[str, None] = "0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Bảng báo cáo biến động theo kỳ ───────────────────────────────────────
    op.create_table(
        "insurance_period_reports",
        sa.Column("id", sa.Integer(), nullable=False),

        # Kỳ báo cáo
        sa.Column("period_year", sa.SmallInteger(), nullable=False),
        sa.Column("period_month", sa.SmallInteger(), nullable=False),
        sa.Column("submission_type", sa.String(length=20), nullable=False,
                  server_default="initial"),

        # Trạng thái workflow
        sa.Column("status", sa.String(length=20), nullable=False,
                  server_default="draft"),

        # Người chuẩn bị
        sa.Column("prepared_by_id", sa.Integer(), nullable=True),
        sa.Column("prepared_at", sa.DateTime(), nullable=True),

        # Người duyệt
        sa.Column("reviewed_by_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),

        # Metadata
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),

        # PK
        sa.PrimaryKeyConstraint("id"),

        # FK
        sa.ForeignKeyConstraint(["prepared_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),

        # Constraints
        sa.CheckConstraint("period_month BETWEEN 1 AND 12", name="ck_ipr_period_month"),
        sa.CheckConstraint(
            "status IN ('draft', 'pending_review', 'approved', 'rejected')",
            name="ck_ipr_status",
        ),
        sa.CheckConstraint(
            "submission_type IN ('initial', 'supplement', 'correction')",
            name="ck_ipr_submission_type",
        ),
        sa.UniqueConstraint(
            "period_year", "period_month", "submission_type",
            name="uq_ipr_period_type",
        ),
    )

    op.create_index("ix_ipr_period", "insurance_period_reports",
                    ["period_year", "period_month"])
    op.create_index("ix_ipr_status", "insurance_period_reports", ["status"])

    # ── Bảng dòng báo cáo ─────────────────────────────────────────────────────
    op.create_table(
        "insurance_report_line_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),

        # Tháng kê khai
        sa.Column("suggested_year", sa.SmallInteger(), nullable=False),
        sa.Column("suggested_month", sa.SmallInteger(), nullable=False),
        sa.Column("declared_year", sa.SmallInteger(), nullable=False),
        sa.Column("declared_month", sa.SmallInteger(), nullable=False),

        # Audit điều chỉnh
        sa.Column("is_adjusted", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        sa.Column("adjustment_note", sa.Text(), nullable=True),
        sa.Column("adjusted_by_id", sa.Integer(), nullable=True),
        sa.Column("adjusted_at", sa.DateTime(), nullable=True),

        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),

        # PK
        sa.PrimaryKeyConstraint("id"),

        # FK
        sa.ForeignKeyConstraint(
            ["report_id"], ["insurance_period_reports.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["event_id"], ["insurance_change_events.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["adjusted_by_id"], ["users.id"], ondelete="SET NULL"),

        # Constraints
        sa.CheckConstraint(
            "suggested_month BETWEEN 1 AND 12", name="ck_irli_suggested_month"
        ),
        sa.CheckConstraint(
            "declared_month BETWEEN 1 AND 12", name="ck_irli_declared_month"
        ),
        sa.UniqueConstraint("report_id", "event_id", name="uq_irli_report_event"),
    )

    op.create_index("ix_irli_report_id", "insurance_report_line_items", ["report_id"])
    op.create_index("ix_irli_event_id", "insurance_report_line_items", ["event_id"])
    op.create_index("ix_irli_declared", "insurance_report_line_items",
                    ["declared_year", "declared_month"])


def downgrade() -> None:
    op.drop_index("ix_irli_declared", table_name="insurance_report_line_items")
    op.drop_index("ix_irli_event_id", table_name="insurance_report_line_items")
    op.drop_index("ix_irli_report_id", table_name="insurance_report_line_items")
    op.drop_table("insurance_report_line_items")

    op.drop_index("ix_ipr_status", table_name="insurance_period_reports")
    op.drop_index("ix_ipr_period", table_name="insurance_period_reports")
    op.drop_table("insurance_period_reports")
