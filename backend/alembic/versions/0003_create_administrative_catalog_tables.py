"""Tạo bảng danh mục hành chính

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-13

Bảng được tạo (4 bảng):
  Danh mục hành chính:
    - administrative_units          Đơn vị hành chính (tỉnh/quận/xã)
    - administrative_hierarchies    Quan hệ phân cấp theo hệ cũ/mới
    - administrative_import_batches Lịch sử import dữ liệu
    - administrative_import_errors  Chi tiết lỗi từng dòng trong batch import
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ── 1. administrative_units ────────────────────────────────────────────────
    op.create_table(
        "administrative_units",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("normalized_name", sa.String(255), nullable=False),
        # province | district | ward
        sa.Column("unit_type", sa.String(20), nullable=False),
        sa.Column("official_name", sa.String(255), nullable=True),
        # denormalized để filter nhanh toàn bộ đơn vị thuộc tỉnh X
        sa.Column("province_code", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("source_name", sa.String(100), nullable=True),
        sa.Column("source_version", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("code", name="uq_administrative_units_code"),
    )
    op.create_index("ix_admin_units_code",            "administrative_units", ["code"], unique=True)
    op.create_index("ix_admin_units_unit_type_active", "administrative_units", ["unit_type", "is_active"])
    op.create_index("ix_admin_units_normalized_name",  "administrative_units", ["normalized_name"])
    op.create_index("ix_admin_units_province_code",    "administrative_units", ["province_code"])

    # ── 2. administrative_hierarchies ──────────────────────────────────────────
    op.create_table(
        "administrative_hierarchies",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        # old | new
        sa.Column("system_type", sa.String(20), nullable=False),
        sa.Column("parent_unit_id", sa.Integer(), nullable=False),
        sa.Column("child_unit_id", sa.Integer(), nullable=False),
        # 1=tỉnh, 2=quận (hệ cũ)/xã (hệ mới), 3=xã (hệ cũ)
        sa.Column("level_depth", sa.SmallInteger(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(
            ["parent_unit_id"], ["administrative_units.id"],
            name="fk_admin_hier_parent",
        ),
        sa.ForeignKeyConstraint(
            ["child_unit_id"], ["administrative_units.id"],
            name="fk_admin_hier_child",
        ),
        sa.UniqueConstraint(
            "system_type", "parent_unit_id", "child_unit_id", "effective_from",
            name="uq_admin_hier_path",
        ),
    )
    op.create_index(
        "ix_admin_hier_parent",
        "administrative_hierarchies",
        ["system_type", "parent_unit_id", "is_active"],
    )
    op.create_index(
        "ix_admin_hier_child",
        "administrative_hierarchies",
        ["system_type", "child_unit_id", "is_active"],
    )

    # ── 3. administrative_import_batches ───────────────────────────────────────
    op.create_table(
        "administrative_import_batches",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_name", sa.String(100), nullable=False),
        sa.Column("source_version", sa.String(50), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("imported_by", sa.Integer(), nullable=True),
        sa.Column(
            "imported_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # draft | success | failed
        sa.Column("status", sa.String(20), nullable=False, server_default="'draft'"),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["imported_by"], ["users.id"],
            name="fk_import_batch_user",
            ondelete="SET NULL",
        ),
    )

    # ── 4. administrative_import_errors ────────────────────────────────────────
    op.create_table(
        "administrative_import_errors",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("row_no", sa.Integer(), nullable=True),
        sa.Column("raw_payload", JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["batch_id"], ["administrative_import_batches.id"],
            name="fk_import_error_batch",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_admin_import_errors_batch",
        "administrative_import_errors",
        ["batch_id"],
    )


def downgrade() -> None:
    op.drop_table("administrative_import_errors")
    op.drop_table("administrative_import_batches")
    op.drop_index("ix_admin_hier_child",  "administrative_hierarchies")
    op.drop_index("ix_admin_hier_parent", "administrative_hierarchies")
    op.drop_table("administrative_hierarchies")
    op.drop_index("ix_admin_units_province_code",    "administrative_units")
    op.drop_index("ix_admin_units_normalized_name",  "administrative_units")
    op.drop_index("ix_admin_units_unit_type_active", "administrative_units")
    op.drop_index("ix_admin_units_code",             "administrative_units")
    op.drop_table("administrative_units")
