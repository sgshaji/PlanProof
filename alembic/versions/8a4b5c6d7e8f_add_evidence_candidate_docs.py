"""add evidence_details and candidate_documents to validation_checks

Revision ID: 8a4b5c6d7e8f
Revises: 7f3c0b4a1e2d
Create Date: 2026-01-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision = "8a4b5c6d7e8f"
down_revision = "7f3c0b4a1e2d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add evidence_details and candidate_documents JSON columns to validation_checks."""
    op.add_column(
        "validation_checks",
        sa.Column("evidence_details", JSON, nullable=True)
    )
    op.add_column(
        "validation_checks",
        sa.Column("candidate_documents", JSON, nullable=True)
    )


def downgrade() -> None:
    """Remove evidence_details and candidate_documents columns from validation_checks."""
    op.drop_column("validation_checks", "candidate_documents")
    op.drop_column("validation_checks", "evidence_details")
