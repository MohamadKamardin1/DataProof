"""create interpretation_results table

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "interpretation_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dataset_id", sa.Integer(), sa.ForeignKey("datasets.id"), nullable=False, index=True),
        sa.Column("pack_id", sa.String(100), nullable=False),
        sa.Column("analysis_version", sa.Integer(), nullable=False),
        sa.Column("per_sample_json", sa.Text(), nullable=False),
        sa.Column("overall_narrative", sa.Text(), nullable=False),
        sa.Column("citations_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("interpretation_results")
