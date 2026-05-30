"""add composite indexes for common query patterns

Revision ID: 0053
Revises: 0052
Create Date: 2026-05-30

HIGH priority indexes dựa trên EXPLAIN ANALYZE audit (M4):

1. audit_logs  — queries filter/sort by user+date, entity+date, action+date
2. email_logs  — notification dedup check: template+employee+status+date
3. employee_contracts — contract history per employee ordered by date
4. employee_job_records — current job lookup: employee+is_current
5. leave_records — status filter per employee
6. employees — status+is_active filter (list pages)

MEDIUM priority indexes cho reporting:
7. insurance_change_events — BHXH export: period+change_type
8. employee_training_records — training history per employee

Production note:
  Nếu cần zero-downtime, chạy thủ công sau migration:
    CREATE INDEX CONCURRENTLY IF NOT EXISTS <name> ON <table> (<cols>);
  Migration này dùng CREATE INDEX thường (cần brief lock).
"""

from alembic import op

revision = "0053"
down_revision = "0052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── HIGH PRIORITY ─────────────────────────────────────────────────────────

    # 1. audit_logs — paginated queries filter by user/entity/action + sort by created_at
    op.create_index(
        "ix_audit_logs_user_created",
        "audit_logs",
        ["user_id", "created_at"],
        postgresql_ops={"created_at": "DESC"},
    )
    op.create_index(
        "ix_audit_logs_entity_type_id_created",
        "audit_logs",
        ["entity_type", "entity_id", "created_at"],
        postgresql_ops={"created_at": "DESC"},
    )
    op.create_index(
        "ix_audit_logs_action_created",
        "audit_logs",
        ["action", "created_at"],
        postgresql_ops={"created_at": "DESC"},
    )

    # 2. email_logs — notification dedup: WHERE template_code=X AND employee_id=Y AND status='sent'
    op.create_index(
        "ix_email_logs_dedup",
        "email_logs",
        ["template_code", "employee_id", "status", "sent_at"],
        postgresql_ops={"sent_at": "DESC"},
        postgresql_where="status = 'sent'",
    )

    # 3. employee_contracts — contract list per employee ordered by effective_from DESC
    op.create_index(
        "ix_employee_contracts_emp_effective",
        "employee_contracts",
        ["employee_id", "effective_from"],
        postgresql_ops={"effective_from": "DESC"},
    )

    # 4. employee_job_records — "get current job": WHERE employee_id=X AND is_current=TRUE
    op.create_index(
        "ix_employee_job_records_emp_current",
        "employee_job_records",
        ["employee_id", "is_current", "effective_from"],
        postgresql_ops={"effective_from": "DESC"},
        postgresql_where="is_current = TRUE",
    )

    # 5. leave_records — status filter per employee (cancel/active)
    op.create_index(
        "ix_leave_records_emp_status_date",
        "leave_records",
        ["employee_id", "status", "start_date"],
        postgresql_ops={"start_date": "DESC"},
    )

    # 6. employees — list page: WHERE status IN (...) AND is_active=TRUE
    op.create_index(
        "ix_employees_status_active",
        "employees",
        ["status", "is_active"],
        postgresql_where="is_active = TRUE",
    )

    # ── MEDIUM PRIORITY ───────────────────────────────────────────────────────

    # 7. insurance_change_events — BHXH export: WHERE period_year=X AND period_month=Y
    op.create_index(
        "ix_insurance_change_events_period",
        "insurance_change_events",
        ["period_year", "period_month", "change_type"],
    )

    # 8. employee_training_records — list by employee ordered by date
    op.create_index(
        "ix_employee_training_records_emp_status",
        "employee_training_records",
        ["employee_id", "status", "start_date"],
        postgresql_ops={"start_date": "DESC"},
    )


def downgrade() -> None:
    op.drop_index("ix_employee_training_records_emp_status", "employee_training_records")
    op.drop_index("ix_insurance_change_events_period", "insurance_change_events")
    op.drop_index("ix_employees_status_active", "employees")
    op.drop_index("ix_leave_records_emp_status_date", "leave_records")
    op.drop_index("ix_employee_job_records_emp_current", "employee_job_records")
    op.drop_index("ix_employee_contracts_emp_effective", "employee_contracts")
    op.drop_index("ix_email_logs_dedup", "email_logs")
    op.drop_index("ix_audit_logs_action_created", "audit_logs")
    op.drop_index("ix_audit_logs_entity_type_id_created", "audit_logs")
    op.drop_index("ix_audit_logs_user_created", "audit_logs")
