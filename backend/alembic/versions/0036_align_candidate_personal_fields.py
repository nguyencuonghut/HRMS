"""align candidate personal fields with employee schema.

Revision ID: 0036
Revises: 0035
Create Date: 2026-05-25
"""
from __future__ import annotations

import unicodedata

import sqlalchemy as sa
from alembic import op

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None


def _normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFC", value.strip())
    decomposed = unicodedata.normalize("NFD", value)
    without_marks = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    without_marks = without_marks.replace("Đ", "D").replace("đ", "d")
    return " ".join(without_marks.lower().split())


def _split_name(full_name: str) -> tuple[str | None, str | None]:
    parts = [part for part in full_name.strip().split() if part]
    if not parts:
        return None, None
    if len(parts) == 1:
        return None, parts[0]
    return " ".join(parts[:-1]), parts[-1]


def upgrade() -> None:
    op.add_column("candidates", sa.Column("last_name", sa.String(length=100), nullable=True))
    op.add_column("candidates", sa.Column("first_name", sa.String(length=100), nullable=True))
    op.add_column("candidates", sa.Column("nationality_id", sa.Integer(), nullable=True))
    op.add_column("candidates", sa.Column("ethnicity_id", sa.Integer(), nullable=True))
    op.add_column("candidates", sa.Column("religion_id", sa.Integer(), nullable=True))
    op.add_column("candidates", sa.Column("id_issued_on", sa.Date(), nullable=True))
    op.add_column("candidates", sa.Column("id_issued_by", sa.String(length=200), nullable=True))
    op.add_column("candidates", sa.Column("id_expires_on", sa.Date(), nullable=True))
    op.add_column("candidates", sa.Column("passport_number", sa.String(length=50), nullable=True))
    op.add_column("candidates", sa.Column("passport_issued_on", sa.Date(), nullable=True))
    op.add_column("candidates", sa.Column("passport_expires_on", sa.Date(), nullable=True))
    op.add_column("candidates", sa.Column("work_permit_number", sa.String(length=50), nullable=True))
    op.add_column("candidates", sa.Column("work_permit_issued_on", sa.Date(), nullable=True))
    op.add_column("candidates", sa.Column("work_permit_expires_on", sa.Date(), nullable=True))
    op.add_column("candidates", sa.Column("phone_number", sa.String(length=20), nullable=True))
    op.add_column("candidates", sa.Column("personal_email", sa.String(length=200), nullable=True))
    op.add_column("candidates", sa.Column("personal_tax_code", sa.String(length=20), nullable=True))
    op.add_column("candidates", sa.Column("bhxh_code", sa.String(length=20), nullable=True))

    op.create_foreign_key(
        "fk_candidates_nationality_id", "candidates", "nationalities", ["nationality_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_candidates_ethnicity_id", "candidates", "ethnicities", ["ethnicity_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_candidates_religion_id", "candidates", "religions", ["religion_id"], ["id"], ondelete="SET NULL"
    )
    op.create_index("ix_candidates_personal_email", "candidates", ["personal_email"])

    bind = op.get_bind()

    nationality_rows = bind.execute(
        sa.text("SELECT id, normalized_name, code, iso2_code, iso3_code FROM nationalities")
    ).mappings().all()
    nationality_map: dict[str, int] = {}
    for row in nationality_rows:
        for key in (row["normalized_name"], row["code"], row["iso2_code"], row["iso3_code"]):
            if key:
                nationality_map[_normalize_text(str(key))] = row["id"]

    candidate_rows = bind.execute(
        sa.text("SELECT id, full_name, nationality, phone, email FROM candidates")
    ).mappings().all()

    update_stmt = sa.text(
        """
        UPDATE candidates
        SET last_name = :last_name,
            first_name = :first_name,
            nationality_id = :nationality_id,
            phone_number = COALESCE(phone_number, :phone_number),
            personal_email = COALESCE(personal_email, :personal_email)
        WHERE id = :candidate_id
        """
    )

    for row in candidate_rows:
        last_name, first_name = _split_name(row["full_name"] or "")
        nationality_id = None
        raw_nationality = row["nationality"]
        if raw_nationality:
            nationality_id = nationality_map.get(_normalize_text(raw_nationality))
        bind.execute(
            update_stmt,
            {
                "candidate_id": row["id"],
                "last_name": last_name,
                "first_name": first_name,
                "nationality_id": nationality_id,
                "phone_number": row["phone"],
                "personal_email": row["email"],
            },
        )


def downgrade() -> None:
    op.drop_index("ix_candidates_personal_email", table_name="candidates")
    op.drop_constraint("fk_candidates_religion_id", "candidates", type_="foreignkey")
    op.drop_constraint("fk_candidates_ethnicity_id", "candidates", type_="foreignkey")
    op.drop_constraint("fk_candidates_nationality_id", "candidates", type_="foreignkey")

    op.drop_column("candidates", "bhxh_code")
    op.drop_column("candidates", "personal_tax_code")
    op.drop_column("candidates", "personal_email")
    op.drop_column("candidates", "phone_number")
    op.drop_column("candidates", "work_permit_expires_on")
    op.drop_column("candidates", "work_permit_issued_on")
    op.drop_column("candidates", "work_permit_number")
    op.drop_column("candidates", "passport_expires_on")
    op.drop_column("candidates", "passport_issued_on")
    op.drop_column("candidates", "passport_number")
    op.drop_column("candidates", "id_expires_on")
    op.drop_column("candidates", "id_issued_by")
    op.drop_column("candidates", "id_issued_on")
    op.drop_column("candidates", "religion_id")
    op.drop_column("candidates", "ethnicity_id")
    op.drop_column("candidates", "nationality_id")
    op.drop_column("candidates", "first_name")
    op.drop_column("candidates", "last_name")
