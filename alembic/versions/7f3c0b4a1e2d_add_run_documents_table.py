"""add run_documents table

Revision ID: 7f3c0b4a1e2d
Revises: e5f6a7b8c9d0
Create Date: 2025-01-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7f3c0b4a1e2d"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "run_documents",
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("runs.id"), primary_key=True, nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_run_documents_document_id", "run_documents", ["document_id"])

    op.execute(
        """
        INSERT INTO run_documents (run_id, document_id, created_at)
        SELECT id, document_id, NOW()
        FROM runs
        WHERE document_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_run_documents_document_id", table_name="run_documents")
    op.drop_table("run_documents")
