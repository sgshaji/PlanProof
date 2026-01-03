"""
Database schema for issue resolution tracking.

Alembic migration to add tables for tracking:
- Issue resolutions
- Actions taken by users
- Auto-recheck history
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'e5f6a7b8c9d0'
down_revision = 'd0d81345f976'  # Previous migration
branch_labels = None
depends_on = None


def upgrade():
    """Add resolution tracking tables."""
    
    # Create issue_resolutions table
    op.create_table(
        'issue_resolutions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('run_id', sa.Integer(), sa.ForeignKey('runs.id'), nullable=False),
        sa.Column('issue_id', sa.String(255), nullable=False),
        sa.Column('rule_id', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),  # open, in_progress, awaiting_verification, resolved, dismissed
        sa.Column('severity', sa.String(50)),
        sa.Column('category', sa.String(100)),
        sa.Column('recheck_pending', sa.Boolean(), default=False),
        sa.Column('last_action_at', sa.DateTime(timezone=True)),
        sa.Column('last_recheck_at', sa.DateTime(timezone=True)),
        sa.Column('resolved_at', sa.DateTime(timezone=True)),
        sa.Column('dismissed_at', sa.DateTime(timezone=True)),
        sa.Column('dismissed_by', sa.String(255)),
        sa.Column('dismissal_reason', sa.Text()),
        sa.Column('metadata_json', postgresql.JSONB()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create index on run_id and issue_id
    op.create_index('ix_issue_resolutions_run_id', 'issue_resolutions', ['run_id'])
    op.create_index('ix_issue_resolutions_issue_id', 'issue_resolutions', ['issue_id'])
    op.create_index('ix_issue_resolutions_status', 'issue_resolutions', ['status'])
    
    # Create resolution_actions table
    op.create_table(
        'resolution_actions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('issue_resolution_id', sa.Integer(), sa.ForeignKey('issue_resolutions.id'), nullable=False),
        sa.Column('action_type', sa.String(50), nullable=False),  # document_upload, option_selection, explanation_provided, dismissed
        sa.Column('action_data', postgresql.JSONB()),  # Store action-specific data
        sa.Column('performed_by', sa.String(255)),  # User/officer ID
        sa.Column('performed_at', sa.DateTime(timezone=True), server_default=sa.func.now())
    )
    
    # Create index on issue_resolution_id
    op.create_index('ix_resolution_actions_issue_resolution_id', 'resolution_actions', ['issue_resolution_id'])
    
    # Create recheck_history table
    op.create_table(
        'recheck_history',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('run_id', sa.Integer(), sa.ForeignKey('runs.id'), nullable=False),
        sa.Column('issue_resolution_id', sa.Integer(), sa.ForeignKey('issue_resolutions.id'), nullable=False),
        sa.Column('rule_id', sa.String(255), nullable=False),
        sa.Column('previous_status', sa.String(50)),
        sa.Column('new_status', sa.String(50)),
        sa.Column('triggered_by', sa.String(50)),  # document_upload, manual, dependency_cascade
        sa.Column('recheck_result', postgresql.JSONB()),
        sa.Column('rechecked_at', sa.DateTime(timezone=True), server_default=sa.func.now())
    )
    
    # Create index on run_id and issue_resolution_id
    op.create_index('ix_recheck_history_run_id', 'recheck_history', ['run_id'])
    op.create_index('ix_recheck_history_issue_resolution_id', 'recheck_history', ['issue_resolution_id'])
    
    # Create dependency_graph table (for tracking issue dependencies)
    op.create_table(
        'issue_dependencies',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('run_id', sa.Integer(), sa.ForeignKey('runs.id'), nullable=False),
        sa.Column('issue_id', sa.String(255), nullable=False),
        sa.Column('depends_on_issue_id', sa.String(255), nullable=False),
        sa.Column('dependency_type', sa.String(50)),  # blocking, suggested, informational
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now())
    )
    
    # Create indexes
    op.create_index('ix_issue_dependencies_run_id', 'issue_dependencies', ['run_id'])
    op.create_index('ix_issue_dependencies_issue_id', 'issue_dependencies', ['issue_id'])


def downgrade():
    """Remove resolution tracking tables."""
    op.drop_index('ix_issue_dependencies_issue_id')
    op.drop_index('ix_issue_dependencies_run_id')
    op.drop_table('issue_dependencies')
    
    op.drop_index('ix_recheck_history_issue_resolution_id')
    op.drop_index('ix_recheck_history_run_id')
    op.drop_table('recheck_history')
    
    op.drop_index('ix_resolution_actions_issue_resolution_id')
    op.drop_table('resolution_actions')
    
    op.drop_index('ix_issue_resolutions_status')
    op.drop_index('ix_issue_resolutions_issue_id')
    op.drop_index('ix_issue_resolutions_run_id')
    op.drop_table('issue_resolutions')
