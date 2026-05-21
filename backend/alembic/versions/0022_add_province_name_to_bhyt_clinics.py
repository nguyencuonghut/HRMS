"""add province_name to bhyt_clinics

Revision ID: 0022
Revises: 0021
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa

revision = '0022'
down_revision = '0021'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('bhyt_clinics', sa.Column('province_name', sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column('bhyt_clinics', 'province_name')
