"""Initial schema - documents existing database structure.

This migration represents the current database schema as of 2025-12-25.
It should be stamped (not run) on existing databases using:
    alembic stamp 001

For new databases, run normally:
    alembic upgrade head

Revision ID: 001
Revises:
Create Date: 2025-12-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table - single source of truth for Telegram users
    op.create_table(
        'users',
        sa.Column('user_id', sa.String(), nullable=False, comment='Telegram user ID'),
        sa.Column('chat_id', sa.Integer(), nullable=False, comment='Telegram chat ID'),
        sa.Column('username', sa.String(), nullable=True, comment='Telegram username'),
        sa.Column('first_name', sa.String(), nullable=True, comment="User's first name"),
        sa.Column('last_name', sa.String(), nullable=True, comment="User's last name"),
        sa.Column('first_seen', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='First interaction'),
        sa.Column('last_seen', sa.DateTime(), nullable=True, comment='Last interaction'),
        sa.Column('is_active', sa.Integer(), server_default='1', comment='1 if active'),
        sa.Column('is_hidden_in_admin', sa.Integer(), server_default='0', comment='1 if hidden from admin'),
        sa.Column('referred_by', sa.String(), nullable=True, comment='Referrer user ID'),
        sa.Column('referral_code', sa.String(), nullable=True, comment='User referral code'),
        sa.PrimaryKeyConstraint('user_id')
    )
    op.create_index('idx_users_referral_code', 'users', ['referral_code'])

    # Actions table - stores user activity analytics
    op.create_table(
        'actions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(), nullable=False, comment='Telegram user ID'),
        sa.Column('action_type', sa.String(), nullable=False, comment='Type of action'),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='When action occurred'),
        sa.Column('details', sa.Text(), nullable=True, comment='Action details'),
        sa.Column('event_id', sa.String(), nullable=True, comment='Related calendar event'),
        sa.Column('success', sa.Integer(), server_default='1', comment='1 if succeeded'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='Error message if failed'),
        sa.Column('is_test', sa.Integer(), server_default='0', comment='1 if test user'),
        sa.Column('input_tokens', sa.Integer(), nullable=True, comment='LLM input tokens'),
        sa.Column('output_tokens', sa.Integer(), nullable=True, comment='LLM output tokens'),
        sa.Column('total_tokens', sa.Integer(), nullable=True, comment='Total LLM tokens'),
        sa.Column('cost_rub', sa.Float(), nullable=True, comment='LLM cost in RUB'),
        sa.Column('llm_model', sa.String(), nullable=True, comment='LLM model used'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_actions_user_timestamp', 'actions', ['user_id', 'timestamp'])
    op.create_index('idx_actions_timestamp', 'actions', ['timestamp'])
    op.create_index('idx_actions_type', 'actions', ['action_type'])
    op.create_index('idx_actions_success', 'actions', ['success'])

    # Referrals table - tracks user referrals
    op.create_table(
        'referrals',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('referrer_id', sa.String(), nullable=False, comment='User who made referral'),
        sa.Column('referred_id', sa.String(), nullable=False, comment='User who was referred'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='When referral was made'),
        sa.Column('notified', sa.Integer(), server_default='0', comment='1 if referrer notified'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('referred_id')
    )
    op.create_index('idx_referrals_referrer', 'referrals', ['referrer_id'])


def downgrade() -> None:
    op.drop_index('idx_referrals_referrer', 'referrals')
    op.drop_table('referrals')

    op.drop_index('idx_actions_success', 'actions')
    op.drop_index('idx_actions_type', 'actions')
    op.drop_index('idx_actions_timestamp', 'actions')
    op.drop_index('idx_actions_user_timestamp', 'actions')
    op.drop_table('actions')

    op.drop_index('idx_users_referral_code', 'users')
    op.drop_table('users')
