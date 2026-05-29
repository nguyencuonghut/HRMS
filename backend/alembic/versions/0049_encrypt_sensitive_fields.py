"""encrypt sensitive employee fields

Revision ID: 0049
Revises: 0048
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa

from app.core.encryption import decrypt, encrypt

revision = "0049"
down_revision = "0048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("employees", "passport_number", existing_type=sa.String(length=50), type_=sa.Text(), existing_nullable=True)
    op.alter_column("employees", "personal_tax_code", existing_type=sa.String(length=20), type_=sa.Text(), existing_nullable=True)
    op.alter_column("employee_bank_accounts", "account_number", existing_type=sa.String(length=50), type_=sa.Text(), existing_nullable=False)

    connection = op.get_bind()

    employee_rows = connection.execute(
            sa.text(
                """
                SELECT id, passport_number, personal_tax_code
                FROM employees
                """
            )
        ).mappings()
    for row in employee_rows:
        connection.execute(
            sa.text(
                """
                UPDATE employees
                SET passport_number = :passport_number,
                    personal_tax_code = :personal_tax_code
                WHERE id = :id
                """
            ),
            {
                "id": row["id"],
                "passport_number": encrypt(row["passport_number"]),
                "personal_tax_code": encrypt(row["personal_tax_code"]),
            },
        )

    bank_rows = connection.execute(
        sa.text(
            """
            SELECT id, account_number
            FROM employee_bank_accounts
            """
        )
    ).mappings()
    for row in bank_rows:
        connection.execute(
            sa.text(
                """
                UPDATE employee_bank_accounts
                SET account_number = :account_number
                WHERE id = :id
                """
            ),
            {
                "id": row["id"],
                "account_number": encrypt(row["account_number"]),
            },
        )


def downgrade() -> None:
    connection = op.get_bind()

    employee_rows = connection.execute(
        sa.text(
            """
            SELECT id, passport_number, personal_tax_code
            FROM employees
            """
        )
    ).mappings()
    for row in employee_rows:
        connection.execute(
            sa.text(
                """
                UPDATE employees
                SET passport_number = :passport_number,
                    personal_tax_code = :personal_tax_code
                WHERE id = :id
                """
            ),
            {
                "id": row["id"],
                "passport_number": decrypt(row["passport_number"]),
                "personal_tax_code": decrypt(row["personal_tax_code"]),
            },
        )

    bank_rows = connection.execute(
        sa.text(
            """
            SELECT id, account_number
            FROM employee_bank_accounts
            """
        )
    ).mappings()
    for row in bank_rows:
        connection.execute(
            sa.text(
                """
                UPDATE employee_bank_accounts
                SET account_number = :account_number
                WHERE id = :id
                """
            ),
            {
                "id": row["id"],
                "account_number": decrypt(row["account_number"]),
            },
        )

    op.alter_column("employee_bank_accounts", "account_number", existing_type=sa.Text(), type_=sa.String(length=50), existing_nullable=False)
    op.alter_column("employees", "personal_tax_code", existing_type=sa.Text(), type_=sa.String(length=20), existing_nullable=True)
    op.alter_column("employees", "passport_number", existing_type=sa.Text(), type_=sa.String(length=50), existing_nullable=True)
