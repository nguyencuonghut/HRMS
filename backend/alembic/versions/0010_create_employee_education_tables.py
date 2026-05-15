"""Create employee education, work experience, skills, certificates, languages tables

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. employee_education_histories ─────────────────────────────────
    op.create_table(
        "employee_education_histories",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "employee_id",
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Dual-field institution
        sa.Column(
            "institution_id",
            sa.Integer(),
            sa.ForeignKey("educational_institutions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("institution_name", sa.String(255), nullable=True),
        sa.Column(
            "major_id",
            sa.Integer(),
            sa.ForeignKey("education_majors.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("major_name", sa.String(255), nullable=True),
        sa.Column(
            "education_level_id",
            sa.Integer(),
            sa.ForeignKey("education_levels.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("graduation_year", sa.SmallInteger(), nullable=True),
        sa.Column("diploma_type", sa.String(100), nullable=True),
        sa.Column(
            "is_main_education",
            sa.Boolean(),
            nullable=False,
            server_default="FALSE",
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_emp_edu_histories_employee_id",
        "employee_education_histories",
        ["employee_id"],
    )

    # ── 2. employee_work_experiences ─────────────────────────────────────
    op.create_table(
        "employee_work_experiences",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "employee_id",
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("position_name", sa.String(255), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_emp_work_exp_employee_id",
        "employee_work_experiences",
        ["employee_id"],
    )

    # ── 3. employee_skills ───────────────────────────────────────────────
    op.create_table(
        "employee_skills",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "employee_id",
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "skill_id",
            sa.Integer(),
            sa.ForeignKey("skills.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        # beginner | intermediate | advanced | expert
        sa.Column("proficiency_level", sa.String(20), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("employee_id", "skill_id", name="uq_employee_skills"),
    )
    op.create_index(
        "ix_emp_skills_employee_id",
        "employee_skills",
        ["employee_id"],
    )

    # ── 4. employee_certificates ─────────────────────────────────────────
    op.create_table(
        "employee_certificates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "employee_id",
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "certificate_id",
            sa.Integer(),
            sa.ForeignKey("certificates.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("certificate_number", sa.String(100), nullable=True),
        sa.Column("issued_date", sa.Date(), nullable=True),
        sa.Column("expires_on", sa.Date(), nullable=True),
        sa.Column("issued_by", sa.String(255), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_emp_certificates_employee_id",
        "employee_certificates",
        ["employee_id"],
    )

    # ── 5. employee_languages ────────────────────────────────────────────
    op.create_table(
        "employee_languages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "employee_id",
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("language_name", sa.String(100), nullable=False),
        # native | A1 | A2 | B1 | B2 | C1 | C2
        sa.Column("proficiency_level", sa.String(10), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("employee_id", "language_name", name="uq_employee_languages"),
    )
    op.create_index(
        "ix_emp_languages_employee_id",
        "employee_languages",
        ["employee_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_emp_languages_employee_id", table_name="employee_languages")
    op.drop_table("employee_languages")

    op.drop_index("ix_emp_certificates_employee_id", table_name="employee_certificates")
    op.drop_table("employee_certificates")

    op.drop_index("ix_emp_skills_employee_id", table_name="employee_skills")
    op.drop_table("employee_skills")

    op.drop_index("ix_emp_work_exp_employee_id", table_name="employee_work_experiences")
    op.drop_table("employee_work_experiences")

    op.drop_index("ix_emp_edu_histories_employee_id", table_name="employee_education_histories")
    op.drop_table("employee_education_histories")
