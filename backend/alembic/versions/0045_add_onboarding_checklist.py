"""add onboarding checklist tables

Revision ID: 0045
Revises: 0044
Create Date: 2026-05-27
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone

revision = "0045"
down_revision = "0044"
branch_labels = None
depends_on = None

_NOW = datetime.now(timezone.utc).replace(tzinfo=None)


def upgrade() -> None:
    # ── onboarding_tasks ─────────────────────────────────────────────────────
    op.create_table(
        "onboarding_tasks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("group", sa.String(30), nullable=False, server_default="admin"),
        sa.Column("default_assignee_role", sa.String(100), nullable=True),
        sa.Column("due_offset_days", sa.SmallInteger(), nullable=False, server_default="3"),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_onboarding_tasks_group", "onboarding_tasks", ["group"])
    op.create_index("ix_onboarding_tasks_active", "onboarding_tasks", ["is_active"])

    # ── onboarding_checklists ────────────────────────────────────────────────
    op.create_table(
        "onboarding_checklists",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "employee_id",
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "hiring_decision_id",
            sa.Integer(),
            sa.ForeignKey("hiring_decisions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "buddy_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="in_progress"),
        sa.Column("completion_pct", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("employee_id", name="uq_onboarding_checklists_employee"),
    )
    op.create_index("ix_onboarding_checklists_status", "onboarding_checklists", ["status"])
    op.create_index("ix_onboarding_checklists_employee", "onboarding_checklists", ["employee_id"])

    # ── onboarding_checklist_items ───────────────────────────────────────────
    op.create_table(
        "onboarding_checklist_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "checklist_id",
            sa.Integer(),
            sa.ForeignKey("onboarding_checklists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "task_id",
            sa.Integer(),
            sa.ForeignKey("onboarding_tasks.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "assignee_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("checklist_id", "task_id", name="uq_onboarding_item_checklist_task"),
    )
    op.create_index("ix_onboarding_items_checklist", "onboarding_checklist_items", ["checklist_id"])
    op.create_index("ix_onboarding_items_assignee", "onboarding_checklist_items", ["assignee_user_id"])
    op.create_index("ix_onboarding_items_due_date", "onboarding_checklist_items", ["due_date"])
    op.create_index("ix_onboarding_items_status", "onboarding_checklist_items", ["status"])

    # ── Seed 8 default task templates ───────────────────────────────────────
    op.execute(
        f"""
        INSERT INTO onboarding_tasks (code, name, description, "group", due_offset_days, sort_order, is_active, created_at, updated_at)
        VALUES
            ('ADMIN_WELCOME',   'Gửi email chào mừng & thông tin cần biết',         NULL,   'admin',    0,  0, true, '{_NOW}', '{_NOW}'),
            ('ADMIN_BADGE',     'Làm thẻ nhân viên',                                 NULL,   'admin',    1,  1, true, '{_NOW}', '{_NOW}'),
            ('IT_ACCOUNT',      'Cấp tài khoản hệ thống (email, Slack, HRMS)',       NULL,   'it',       1,  2, true, '{_NOW}', '{_NOW}'),
            ('IT_EQUIPMENT',    'Bàn giao thiết bị làm việc',                        NULL,   'it',       1,  3, true, '{_NOW}', '{_NOW}'),
            ('TRAINING_POLICY', 'Đào tạo nội quy công ty & chính sách',             NULL,   'training', 3,  4, true, '{_NOW}', '{_NOW}'),
            ('TRAINING_SAFETY', 'Đào tạo an toàn lao động',                         NULL,   'training', 5,  5, true, '{_NOW}', '{_NOW}'),
            ('SPECIALTY_INTRO', 'Giới thiệu quy trình nghiệp vụ bộ phận',           NULL,   'specialty',5,  6, true, '{_NOW}', '{_NOW}'),
            ('BUDDY_INTRO',     'Buddy giới thiệu đồng nghiệp và môi trường',        NULL,   'specialty',0,  7, true, '{_NOW}', '{_NOW}')
        ON CONFLICT (code) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("onboarding_checklist_items")
    op.drop_table("onboarding_checklists")
    op.drop_table("onboarding_tasks")
