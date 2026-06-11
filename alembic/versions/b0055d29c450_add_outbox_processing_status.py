"""add_outbox_processing_status

Revision ID: b0055d29c450
Revises: 248e40c26b84
Create Date: 2026-06-11 17:37:44.043685

Manual migration — Alembic does not detect enum value additions automatically.
Postgres requires ALTER TYPE to add values to an existing enum.
"""
from typing import Sequence, Union
from alembic import op

revision: str = 'b0055d29c450'
down_revision: Union[str, Sequence[str], None] = '248e40c26b84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add PROCESSING value to outboxstatus enum.

    ALTER TYPE ... ADD VALUE is irreversible in Postgres — there is no
    DROP VALUE. The downgrade therefore cannot truly undo this change.
    This is a known Postgres limitation with enum types.

    Production note: if removing an enum value is ever needed, the correct
    approach is to create a new enum type, migrate the column, and drop the old type.
    """
    op.execute("ALTER TYPE outboxstatus ADD VALUE IF NOT EXISTS 'PROCESSING'")


def downgrade() -> None:
    """
    Postgres does not support removing enum values via ALTER TYPE.
    Downgrade is a no-op — the PROCESSING value will remain in the enum type
    even after downgrading the migration.

    To fully revert: recreate the enum type without PROCESSING and migrate
    the column manually.
    """
    pass
