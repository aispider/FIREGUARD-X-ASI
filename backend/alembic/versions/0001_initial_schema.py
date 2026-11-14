"""initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-10-09 05:23:31.618476
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.create_table('audit_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ts', sa.DateTime(timezone=True), nullable=False),
    sa.Column('username', sa.String(length=64), nullable=False),
    sa.Column('action', sa.String(length=64), nullable=False),
    sa.Column('resource', sa.String(length=160), nullable=False),
    sa.Column('result', sa.String(length=64), nullable=False),
    sa.Column('details', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('prev_hash', sa.String(length=64), nullable=False),
    sa.Column('hash', sa.String(length=64), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_ts'), 'audit_logs', ['ts'], unique=False)
    op.create_table('experiments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('key', sa.String(length=32), nullable=False),
    sa.Column('program', sa.String(length=64), nullable=False),
    sa.Column('name', sa.String(length=160), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('source_url', sa.String(length=512), nullable=True),
    sa.Column('variables', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_experiments_key'), 'experiments', ['key'], unique=True)
    op.create_table('ingestion_jobs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('requested_by', sa.String(length=64), nullable=False),
    sa.Column('params', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('stats', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('log', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('risk_assessments',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('scenario', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('risk_score', sa.Integer(), nullable=False),
    sa.Column('risk_level', sa.String(length=16), nullable=False),
    sa.Column('crew_level', sa.String(length=16), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.Column('trust_score', sa.Integer(), nullable=False),
    sa.Column('trust_band', sa.String(length=24), nullable=False),
    sa.Column('guardian_status', sa.String(length=24), nullable=False),
    sa.Column('red_team_status', sa.String(length=24), nullable=False),
    sa.Column('evidence_count', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=24), nullable=False),
    sa.Column('result', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('created_by', sa.String(length=64), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_risk_assessments_created_at'), 'risk_assessments', ['created_at'], unique=False)
    op.create_table('roles',
    sa.Column('name', sa.String(length=32), nullable=False),
    sa.Column('permissions', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.PrimaryKeyConstraint('name')
    )
    op.create_table('scenarios',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('params', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('preset', sa.Boolean(), nullable=False),
    sa.Column('synthetic', sa.Boolean(), nullable=False),
    sa.Column('created_by', sa.String(length=64), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('security_events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('event_type', sa.String(length=48), nullable=False),
    sa.Column('severity', sa.String(length=12), nullable=False),
    sa.Column('source', sa.String(length=64), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('details', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_security_events_created_at'), 'security_events', ['created_at'], unique=False)
    op.create_index(op.f('ix_security_events_event_type'), 'security_events', ['event_type'], unique=False)
    op.create_table('agent_runs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('assessment_id', sa.String(length=36), nullable=True),
    sa.Column('agent_id', sa.String(length=64), nullable=False),
    sa.Column('role', sa.String(length=32), nullable=False),
    sa.Column('version', sa.String(length=16), nullable=False),
    sa.Column('model', sa.String(length=64), nullable=False),
    sa.Column('permissions', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('input_hash', sa.String(length=64), nullable=False),
    sa.Column('output_hash', sa.String(length=64), nullable=False),
    sa.Column('output', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['assessment_id'], ['risk_assessments.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_runs_agent_id'), 'agent_runs', ['agent_id'], unique=False)
    op.create_index(op.f('ix_agent_runs_assessment_id'), 'agent_runs', ['assessment_id'], unique=False)
    op.create_table('approvals',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('assessment_id', sa.String(length=36), nullable=False),
    sa.Column('username', sa.String(length=64), nullable=False),
    sa.Column('decision', sa.String(length=16), nullable=False),
    sa.Column('note', sa.String(length=500), nullable=True),
    sa.Column('policy', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('simulated_steps', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['assessment_id'], ['risk_assessments.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_approvals_assessment_id'), 'approvals', ['assessment_id'], unique=False)
    op.create_table('documents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('doc_key', sa.String(length=64), nullable=False),
    sa.Column('experiment_id', sa.Integer(), nullable=True),
    sa.Column('title', sa.String(length=512), nullable=False),
    sa.Column('source', sa.String(length=64), nullable=False),
    sa.Column('source_url', sa.String(length=1024), nullable=True),
    sa.Column('ntrs_id', sa.String(length=32), nullable=True),
    sa.Column('document_type', sa.String(length=64), nullable=True),
    sa.Column('publication_date', sa.String(length=32), nullable=True),
    sa.Column('center', sa.String(length=64), nullable=True),
    sa.Column('license', sa.String(length=128), nullable=True),
    sa.Column('distribution', sa.String(length=32), nullable=True),
    sa.Column('version', sa.String(length=16), nullable=False),
    sa.Column('retrieved_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('sha256', sa.String(length=64), nullable=False),
    sa.Column('source_bytes_sha256', sa.String(length=64), nullable=True),
    sa.Column('byte_length', sa.Integer(), nullable=False),
    sa.Column('content_text', sa.Text(), nullable=False),
    sa.Column('tamper_overlay', sa.Text(), nullable=True),
    sa.Column('processing_status', sa.String(length=24), nullable=False),
    sa.Column('quarantined', sa.Boolean(), nullable=False),
    sa.Column('synthetic', sa.Boolean(), nullable=False),
    sa.Column('meta', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('error', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['experiment_id'], ['experiments.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_documents_doc_key'), 'documents', ['doc_key'], unique=True)
    op.create_index(op.f('ix_documents_ntrs_id'), 'documents', ['ntrs_id'], unique=False)
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=64), nullable=False),
    sa.Column('password_hash', sa.String(length=256), nullable=False),
    sa.Column('role', sa.String(length=32), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['role'], ['roles.name'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_table('evidence_chunks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('chunk_key', sa.String(length=80), nullable=False),
    sa.Column('document_id', sa.Integer(), nullable=False),
    sa.Column('ordinal', sa.Integer(), nullable=False),
    sa.Column('page', sa.Integer(), nullable=True),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('content_hash', sa.String(length=64), nullable=False),
    sa.Column('embedding', Vector(384), nullable=True),
    sa.Column('variables', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('materials', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('topic', sa.String(length=32), nullable=False),
    sa.Column('gravity', sa.String(length=24), nullable=False),
    sa.Column('injection_flags', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('synthetic', sa.Boolean(), nullable=False),
    sa.Column('meta', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evidence_chunks_chunk_key'), 'evidence_chunks', ['chunk_key'], unique=True)
    op.create_index(op.f('ix_evidence_chunks_document_id'), 'evidence_chunks', ['document_id'], unique=False)
    op.create_index('ix_evidence_chunks_document_ord', 'evidence_chunks', ['document_id', 'ordinal'], unique=False)
    op.create_table('observations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('experiment_id', sa.Integer(), nullable=True),
    sa.Column('document_id', sa.Integer(), nullable=True),
    sa.Column('variable', sa.String(length=48), nullable=False),
    sa.Column('value', sa.Float(), nullable=False),
    sa.Column('unit', sa.String(length=32), nullable=False),
    sa.Column('condition', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('source_reference', sa.String(length=512), nullable=True),
    sa.Column('synthetic', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
    sa.ForeignKeyConstraint(['experiment_id'], ['experiments.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_observations_variable'), 'observations', ['variable'], unique=False)
    op.execute('CREATE INDEX ix_evidence_chunks_embedding_hnsw ON evidence_chunks USING hnsw (embedding vector_cosine_ops)')


def downgrade() -> None:
    op.execute('DROP INDEX IF EXISTS ix_evidence_chunks_embedding_hnsw')
    op.drop_index(op.f('ix_observations_variable'), table_name='observations')
    op.drop_table('observations')
    op.drop_index('ix_evidence_chunks_document_ord', table_name='evidence_chunks')
    op.drop_index(op.f('ix_evidence_chunks_document_id'), table_name='evidence_chunks')
    op.drop_index(op.f('ix_evidence_chunks_chunk_key'), table_name='evidence_chunks')
    op.drop_table('evidence_chunks')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_documents_ntrs_id'), table_name='documents')
    op.drop_index(op.f('ix_documents_doc_key'), table_name='documents')
    op.drop_table('documents')
    op.drop_index(op.f('ix_approvals_assessment_id'), table_name='approvals')
    op.drop_table('approvals')
    op.drop_index(op.f('ix_agent_runs_assessment_id'), table_name='agent_runs')
    op.drop_index(op.f('ix_agent_runs_agent_id'), table_name='agent_runs')
    op.drop_table('agent_runs')
    op.drop_index(op.f('ix_security_events_event_type'), table_name='security_events')
    op.drop_index(op.f('ix_security_events_created_at'), table_name='security_events')
    op.drop_table('security_events')
    op.drop_table('scenarios')
    op.drop_table('roles')
    op.drop_index(op.f('ix_risk_assessments_created_at'), table_name='risk_assessments')
    op.drop_table('risk_assessments')
    op.drop_table('ingestion_jobs')
    op.drop_index(op.f('ix_experiments_key'), table_name='experiments')
    op.drop_table('experiments')
    op.drop_index(op.f('ix_audit_logs_ts'), table_name='audit_logs')
    op.drop_table('audit_logs')
