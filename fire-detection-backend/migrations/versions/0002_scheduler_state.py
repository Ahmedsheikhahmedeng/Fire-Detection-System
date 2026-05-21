"""persist scheduler state

Revision ID: 0002_scheduler_state
Revises: 0001_baseline
Create Date: 2026-05-09

"""

from alembic import op
import sqlalchemy as sa


revision = "0002_scheduler_state"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scheduler_state",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("scheduler_state")
