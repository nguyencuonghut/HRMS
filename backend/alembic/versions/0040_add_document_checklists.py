"""add document checklists

Revision ID: 0040
Revises: 0039
Create Date: 2026-05-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_checklist_types",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("has_expiry", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("applies_to", sa.String(30), nullable=False, server_default="all"),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_document_checklist_type_code"),
    )

    op.create_table(
        "employee_document_checklists",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("document_type_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="not_submitted"),
        sa.Column("submitted_at", sa.Date(), nullable=True),
        sa.Column("expires_at", sa.Date(), nullable=True),
        sa.Column("waived_reason", sa.Text(), nullable=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_name", sa.String(300), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_type_id"], ["document_checklist_types.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_id", "document_type_id", name="uq_emp_doc_type"),
    )
    op.create_index("ix_emp_doc_checklist_employee", "employee_document_checklists", ["employee_id"])
    op.create_index("ix_emp_doc_checklist_status", "employee_document_checklists", ["status"])
    op.create_index(
        "ix_emp_doc_checklist_expiry",
        "employee_document_checklists",
        ["expires_at"],
        postgresql_where=sa.text("expires_at IS NOT NULL"),
    )

    # Seed default document types
    op.bulk_insert(
        sa.table(
            "document_checklist_types",
            sa.column("code", sa.String),
            sa.column("name", sa.String),
            sa.column("is_required", sa.Boolean),
            sa.column("has_expiry", sa.Boolean),
            sa.column("applies_to", sa.String),
            sa.column("sort_order", sa.SmallInteger),
        ),
        [
            {"code": "cccd",          "name": "CCCD/CMND (bản sao công chứng)",            "is_required": True,  "has_expiry": False, "applies_to": "all",                "sort_order": 1},
            {"code": "ho_khau",       "name": "Sổ hộ khẩu / KT3 (bản sao)",               "is_required": True,  "has_expiry": False, "applies_to": "all",                "sort_order": 2},
            {"code": "giay_khai_sinh","name": "Giấy khai sinh (bản sao)",                  "is_required": True,  "has_expiry": False, "applies_to": "all",                "sort_order": 3},
            {"code": "bang_cap",      "name": "Bằng cấp / Chứng chỉ (bản sao công chứng)","is_required": True,  "has_expiry": True,  "applies_to": "all",                "sort_order": 4},
            {"code": "suc_khoe",      "name": "Giấy chứng nhận sức khỏe",                  "is_required": True,  "has_expiry": True,  "applies_to": "all",                "sort_order": 5},
            {"code": "mst",           "name": "Mã số thuế cá nhân",                         "is_required": True,  "has_expiry": False, "applies_to": "all",                "sort_order": 6},
            {"code": "tk_ngan_hang",  "name": "Thông tin tài khoản ngân hàng",              "is_required": True,  "has_expiry": False, "applies_to": "all",                "sort_order": 7},
            {"code": "anh_the",       "name": "Ảnh thẻ 3×4",                                "is_required": True,  "has_expiry": False, "applies_to": "all",                "sort_order": 8},
            {"code": "so_bhxh",       "name": "Sổ BHXH",                                    "is_required": False, "has_expiry": False, "applies_to": "all",                "sort_order": 9},
            {"code": "ly_lich_tu_phap","name": "Lý lịch tư pháp số 1",                     "is_required": False, "has_expiry": True,  "applies_to": "sensitive_position", "sort_order": 10},
            {"code": "giay_phep_ld",  "name": "Giấy phép lao động",                         "is_required": True,  "has_expiry": True,  "applies_to": "foreign_worker",     "sort_order": 11},
        ],
    )


def downgrade() -> None:
    op.drop_table("employee_document_checklists")
    op.drop_table("document_checklist_types")
