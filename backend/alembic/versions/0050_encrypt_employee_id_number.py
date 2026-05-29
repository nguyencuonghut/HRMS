"""encrypt employee id_number and add hash lookup

Revision ID: 0050
Revises: 0049
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa

from app.core.encryption import encrypt, hash_sensitive, decrypt

revision = "0050"
down_revision = "0049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("employees", sa.Column("id_number_hash", sa.String(length=64), nullable=True))
    op.create_index("ix_employees_id_number_hash", "employees", ["id_number_hash"], unique=True)
    op.alter_column("employees", "id_number", existing_type=sa.String(length=20), type_=sa.Text(), existing_nullable=False)

    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, id_number FROM employees")).mappings()
    for row in rows:
        connection.execute(
            sa.text(
                """
                UPDATE employees
                SET id_number = :id_number,
                    id_number_hash = :id_number_hash
                WHERE id = :id
                """
            ),
            {
                "id": row["id"],
                "id_number": encrypt(row["id_number"]),
                "id_number_hash": hash_sensitive(row["id_number"]),
            },
        )

    op.alter_column("employees", "id_number_hash", existing_type=sa.String(length=64), nullable=False)


def downgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, id_number FROM employees")).mappings()
    for row in rows:
        connection.execute(
            sa.text(
                """
                UPDATE employees
                SET id_number = :id_number
                WHERE id = :id
                """
            ),
            {
                "id": row["id"],
                "id_number": decrypt(row["id_number"]),
            },
        )

    op.alter_column("employees", "id_number", existing_type=sa.Text(), type_=sa.String(length=20), existing_nullable=False)
    op.drop_index("ix_employees_id_number_hash", table_name="employees")
    op.drop_column("employees", "id_number_hash")
