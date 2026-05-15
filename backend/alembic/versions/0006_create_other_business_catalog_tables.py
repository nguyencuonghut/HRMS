"""Create other business catalog tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contract_categories",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("document_kind", sa.String(length=30), nullable=False),
        sa.Column("legal_contract_type", sa.String(length=30), nullable=True),
        sa.Column("business_group", sa.String(length=50), nullable=True),
        sa.Column("default_term_months", sa.Integer(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_contract_categories_code", "contract_categories", ["code"], unique=True)
    op.create_index("ix_contract_categories_normalized_name", "contract_categories", ["normalized_name"], unique=False)
    op.create_index("ix_contract_categories_document_kind", "contract_categories", ["document_kind"], unique=False)
    op.create_index(
        "ix_contract_categories_legal_contract_type",
        "contract_categories",
        ["legal_contract_type"],
        unique=False,
    )
    op.create_index("ix_contract_categories_business_group", "contract_categories", ["business_group"], unique=False)
    op.create_index(
        "ix_contract_categories_kind_active",
        "contract_categories",
        ["document_kind", "is_active"],
        unique=False,
    )

    op.create_table(
        "nationalities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("iso2_code", sa.String(length=2), nullable=True),
        sa.Column("iso3_code", sa.String(length=3), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_nationalities_code", "nationalities", ["code"], unique=True)
    op.create_index("ix_nationalities_normalized_name", "nationalities", ["normalized_name"], unique=False)
    op.create_index("ix_nationalities_iso2_code", "nationalities", ["iso2_code"], unique=False)
    op.create_index("ix_nationalities_iso3_code", "nationalities", ["iso3_code"], unique=False)

    op.create_table(
        "ethnicities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ethnicities_code", "ethnicities", ["code"], unique=True)
    op.create_index("ix_ethnicities_normalized_name", "ethnicities", ["normalized_name"], unique=False)
    op.create_index("ix_ethnicities_active", "ethnicities", ["is_active"], unique=False)

    op.create_table(
        "religions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_religions_code", "religions", ["code"], unique=True)
    op.create_index("ix_religions_normalized_name", "religions", ["normalized_name"], unique=False)
    op.create_index("ix_religions_active", "religions", ["is_active"], unique=False)

    op.create_table(
        "banks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("short_name", sa.String(length=100), nullable=True),
        sa.Column("bin_code", sa.String(length=20), nullable=True),
        sa.Column("swift_code", sa.String(length=20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_banks_code", "banks", ["code"], unique=True)
    op.create_index("ix_banks_normalized_name", "banks", ["normalized_name"], unique=False)
    op.create_index("ix_banks_short_name", "banks", ["short_name"], unique=False)
    op.create_index("ix_banks_bin_code", "banks", ["bin_code"], unique=False)
    op.create_index("ix_banks_swift_code", "banks", ["swift_code"], unique=False)

    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("skill_group", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_skills_code", "skills", ["code"], unique=True)
    op.create_index("ix_skills_normalized_name", "skills", ["normalized_name"], unique=False)
    op.create_index("ix_skills_group_active", "skills", ["skill_group", "is_active"], unique=False)

    op.create_table(
        "certificates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("certificate_group", sa.String(length=100), nullable=True),
        sa.Column("issuer_name", sa.String(length=255), nullable=True),
        sa.Column("expiry_policy", sa.String(length=30), nullable=True),
        sa.Column("default_valid_months", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_certificates_code", "certificates", ["code"], unique=True)
    op.create_index("ix_certificates_normalized_name", "certificates", ["normalized_name"], unique=False)
    op.create_index(
        "ix_certificates_group_active",
        "certificates",
        ["certificate_group", "is_active"],
        unique=False,
    )
    op.create_index("ix_certificates_expiry_policy", "certificates", ["expiry_policy"], unique=False)

    op.create_table(
        "leave_types",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("is_paid_leave", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("affects_annual_leave", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("allow_half_day", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("requires_attachment", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("color_tag", sa.String(length=20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_leave_types_code", "leave_types", ["code"], unique=True)
    op.create_index("ix_leave_types_normalized_name", "leave_types", ["normalized_name"], unique=False)
    op.create_index("ix_leave_types_active", "leave_types", ["is_active"], unique=False)

    op.create_table(
        "contract_templates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("contract_category_id", sa.Integer(), nullable=False),
        sa.Column("document_kind", sa.String(length=30), nullable=False),
        sa.Column(
            "template_engine",
            sa.String(length=30),
            nullable=False,
            server_default="docx_placeholders",
        ),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=True),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("file_checksum", sa.String(length=128), nullable=True),
        sa.Column("version_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["contract_category_id"], ["contract_categories.id"], name="fk_contract_templates_category"),
        sa.UniqueConstraint("code", "version_no", name="uq_contract_templates_code_version"),
    )
    op.create_index("ix_contract_templates_code", "contract_templates", ["code"], unique=False)
    op.create_index("ix_contract_templates_normalized_name", "contract_templates", ["normalized_name"], unique=False)
    op.create_index(
        "ix_contract_templates_category_active",
        "contract_templates",
        ["contract_category_id", "is_active"],
        unique=False,
    )
    op.create_index(
        "ix_contract_templates_kind_active",
        "contract_templates",
        ["document_kind", "is_active"],
        unique=False,
    )
    op.create_index("ix_contract_templates_template_engine", "contract_templates", ["template_engine"], unique=False)

    op.create_table(
        "contract_template_placeholders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("placeholder_key", sa.String(length=100), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("source_scope", sa.String(length=50), nullable=False),
        sa.Column("source_path", sa.String(length=255), nullable=False),
        sa.Column("data_type", sa.String(length=30), nullable=False),
        sa.Column("formatter", sa.String(length=50), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("default_value", sa.String(length=255), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["contract_templates.id"],
            name="fk_contract_template_placeholders_template",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("template_id", "placeholder_key", name="uq_contract_template_placeholders_template_key"),
    )
    op.create_index(
        "ix_contract_template_placeholders_template_sort",
        "contract_template_placeholders",
        ["template_id", "sort_order"],
        unique=False,
    )
    op.create_index(
        "ix_contract_template_placeholders_source_scope",
        "contract_template_placeholders",
        ["source_scope"],
        unique=False,
    )
    op.create_index(
        "ix_contract_template_placeholders_data_type",
        "contract_template_placeholders",
        ["data_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_contract_template_placeholders_data_type", table_name="contract_template_placeholders")
    op.drop_index("ix_contract_template_placeholders_source_scope", table_name="contract_template_placeholders")
    op.drop_index("ix_contract_template_placeholders_template_sort", table_name="contract_template_placeholders")
    op.drop_table("contract_template_placeholders")

    op.drop_index("ix_contract_templates_template_engine", table_name="contract_templates")
    op.drop_index("ix_contract_templates_kind_active", table_name="contract_templates")
    op.drop_index("ix_contract_templates_category_active", table_name="contract_templates")
    op.drop_index("ix_contract_templates_normalized_name", table_name="contract_templates")
    op.drop_index("ix_contract_templates_code", table_name="contract_templates")
    op.drop_table("contract_templates")

    op.drop_index("ix_leave_types_active", table_name="leave_types")
    op.drop_index("ix_leave_types_normalized_name", table_name="leave_types")
    op.drop_index("ix_leave_types_code", table_name="leave_types")
    op.drop_table("leave_types")

    op.drop_index("ix_certificates_expiry_policy", table_name="certificates")
    op.drop_index("ix_certificates_group_active", table_name="certificates")
    op.drop_index("ix_certificates_normalized_name", table_name="certificates")
    op.drop_index("ix_certificates_code", table_name="certificates")
    op.drop_table("certificates")

    op.drop_index("ix_skills_group_active", table_name="skills")
    op.drop_index("ix_skills_normalized_name", table_name="skills")
    op.drop_index("ix_skills_code", table_name="skills")
    op.drop_table("skills")

    op.drop_index("ix_banks_swift_code", table_name="banks")
    op.drop_index("ix_banks_bin_code", table_name="banks")
    op.drop_index("ix_banks_short_name", table_name="banks")
    op.drop_index("ix_banks_normalized_name", table_name="banks")
    op.drop_index("ix_banks_code", table_name="banks")
    op.drop_table("banks")

    op.drop_index("ix_religions_active", table_name="religions")
    op.drop_index("ix_religions_normalized_name", table_name="religions")
    op.drop_index("ix_religions_code", table_name="religions")
    op.drop_table("religions")

    op.drop_index("ix_ethnicities_active", table_name="ethnicities")
    op.drop_index("ix_ethnicities_normalized_name", table_name="ethnicities")
    op.drop_index("ix_ethnicities_code", table_name="ethnicities")
    op.drop_table("ethnicities")

    op.drop_index("ix_nationalities_iso3_code", table_name="nationalities")
    op.drop_index("ix_nationalities_iso2_code", table_name="nationalities")
    op.drop_index("ix_nationalities_normalized_name", table_name="nationalities")
    op.drop_index("ix_nationalities_code", table_name="nationalities")
    op.drop_table("nationalities")

    op.drop_index("ix_contract_categories_kind_active", table_name="contract_categories")
    op.drop_index("ix_contract_categories_business_group", table_name="contract_categories")
    op.drop_index("ix_contract_categories_legal_contract_type", table_name="contract_categories")
    op.drop_index("ix_contract_categories_document_kind", table_name="contract_categories")
    op.drop_index("ix_contract_categories_normalized_name", table_name="contract_categories")
    op.drop_index("ix_contract_categories_code", table_name="contract_categories")
    op.drop_table("contract_categories")
