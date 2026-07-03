"""create analysis_results table

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analysis_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dataset_id", sa.Integer(), sa.ForeignKey("datasets.id"), nullable=False, index=True),
        sa.Column("pack_id", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("proxy_id", sa.String(100), nullable=False),
        sa.Column("proxy_label", sa.String(200), nullable=False),
        sa.Column("sample_id", sa.String(100), nullable=False),
        sa.Column("value", sa.Double(), nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_index(
        "ix_analysis_dataset_pack_version",
        "analysis_results",
        ["dataset_id", "pack_id", "version"],
    )


def downgrade() -> None:
    op.drop_index("ix_analysis_dataset_pack_version", table_name="analysis_results")
    op.drop_table("analysis_results")
