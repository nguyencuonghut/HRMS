"""Create employee_contracts table

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-18
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "employee_contracts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "employee_id",
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_contract_id",
            sa.Integer(),
            sa.ForeignKey("employee_contracts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "contract_category_id",
            sa.Integer(),
            sa.ForeignKey("contract_categories.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("document_kind",      sa.String(30),  nullable=False),
        sa.Column("contract_number",    sa.String(100), nullable=False),
        sa.Column("signed_date",        sa.Date(),      nullable=False),
        sa.Column("effective_from",     sa.Date(),      nullable=False),
        sa.Column("effective_to",       sa.Date(),      nullable=True),
        sa.Column("insurance_salary",   sa.Numeric(18, 2), nullable=True),
        sa.Column("status",             sa.String(20),  nullable=False, server_default="active"),
        sa.Column("file_path",          sa.String(500), nullable=True),
        sa.Column("file_name",          sa.String(255), nullable=True),
        sa.Column("file_size",          sa.Integer(),   nullable=True),
        sa.Column("mime_type",          sa.String(100), nullable=True),
        sa.Column("notes",              sa.Text(),      nullable=True),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("contract_number", name="uq_employee_contract_number"),
    )

    op.create_index("ix_employee_contracts_employee_id",           "employee_contracts", ["employee_id"])
    op.create_index("ix_employee_contracts_parent_contract_id",    "employee_contracts", ["parent_contract_id"])
    op.create_index("ix_employee_contracts_contract_category_id",  "employee_contracts", ["contract_category_id"])
    op.create_index("ix_employee_contracts_document_kind",         "employee_contracts", ["document_kind"])
    op.create_index("ix_employee_contracts_status",                "employee_contracts", ["status"])
    op.create_index("ix_employee_contracts_effective_to_status",   "employee_contracts", ["effective_to", "status"])


def downgrade() -> None:
    op.drop_index("ix_employee_contracts_effective_to_status",  "employee_contracts")
    op.drop_index("ix_employee_contracts_status",               "employee_contracts")
    op.drop_index("ix_employee_contracts_document_kind",        "employee_contracts")
    op.drop_index("ix_employee_contracts_contract_category_id", "employee_contracts")
    op.drop_index("ix_employee_contracts_parent_contract_id",   "employee_contracts")
    op.drop_index("ix_employee_contracts_employee_id",          "employee_contracts")
    op.drop_table("employee_contracts")
