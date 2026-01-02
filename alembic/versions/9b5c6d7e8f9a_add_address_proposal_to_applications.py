"""add site_address and proposal_description to applications

Revision ID: 9b5c6d7e8f9a
Revises: 8a4b5c6d7e8f
Create Date: 2026-01-02 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9b5c6d7e8f9a"
down_revision = "8a4b5c6d7e8f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add site_address and proposal_description columns to applications table."""
    op.add_column(
        "applications",
        sa.Column("site_address", sa.Text, nullable=True)
    )
    op.add_column(
        "applications",
        sa.Column("proposal_description", sa.Text, nullable=True)
    )
    
    # Optionally populate from latest extracted_fields (if data exists)
    # This query updates applications with the most recent extracted values
    op.execute("""
        UPDATE applications a
        SET site_address = (
            SELECT ef.field_value
            FROM extracted_fields ef
            JOIN submissions s ON ef.submission_id = s.id
            WHERE s.planning_case_id = a.id
            AND ef.field_name IN ('site_address', 'address')
            ORDER BY ef.confidence DESC NULLS LAST, ef.created_at DESC
            LIMIT 1
        )
        WHERE site_address IS NULL;
    """)
    
    op.execute("""
        UPDATE applications a
        SET proposal_description = (
            SELECT ef.field_value
            FROM extracted_fields ef
            JOIN submissions s ON ef.submission_id = s.id
            WHERE s.planning_case_id = a.id
            AND ef.field_name IN ('proposal_description', 'proposed_use')
            ORDER BY ef.confidence DESC NULLS LAST, ef.created_at DESC
            LIMIT 1
        )
        WHERE proposal_description IS NULL;
    """)


def downgrade() -> None:
    """Remove site_address and proposal_description columns from applications table."""
    op.drop_column("applications", "proposal_description")
    op.drop_column("applications", "site_address")
