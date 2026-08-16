"""create initial analysis schema

Revision ID: 0001_initial_schema
Revises:
"""

import sqlalchemy as sa

from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analyses",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("submitted_url", sa.Text(), nullable=False),
        sa.Column("normalized_url", sa.Text(), nullable=True),
        sa.Column("final_url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("risk_score", sa.Integer(), nullable=True),
        sa.Column("verdict", sa.String(length=32), nullable=True),
        sa.Column("signals", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_analyses_status", "analyses", ["status"])

    op.create_table(
        "findings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "analysis_id",
            sa.String(length=36),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("finding_id", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=True),
    )
    op.create_index("ix_findings_analysis_id", "findings", ["analysis_id"])

    op.create_table(
        "redirects",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "analysis_id",
            sa.String(length=36),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("hop", sa.Integer(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("location", sa.Text(), nullable=False),
    )
    op.create_index("ix_redirects_analysis_id", "redirects", ["analysis_id"])


def downgrade() -> None:
    op.drop_index("ix_redirects_analysis_id", table_name="redirects")
    op.drop_table("redirects")
    op.drop_index("ix_findings_analysis_id", table_name="findings")
    op.drop_table("findings")
    op.drop_index("ix_analyses_status", table_name="analyses")
    op.drop_table("analyses")
