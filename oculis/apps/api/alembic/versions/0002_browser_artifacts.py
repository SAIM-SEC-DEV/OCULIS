"""add browser artifacts and network request tables

Revision ID: 0002_browser_artifacts
Revises: 0001_initial_schema
"""

import sqlalchemy as sa

from alembic import op

revision = "0002_browser_artifacts"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("analyses", sa.Column("browser_data", sa.JSON(), nullable=True))
    op.add_column("analyses", sa.Column("screenshot_path", sa.Text(), nullable=True))
    op.add_column("analyses", sa.Column("screenshot_mime", sa.String(length=64), nullable=True))

    op.create_table(
        "network_requests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "analysis_id",
            sa.String(length=36),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("resource_type", sa.String(length=32), nullable=True),
        sa.Column("blocked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reason", sa.Text(), nullable=True),
    )
    op.create_index("ix_network_requests_analysis_id", "network_requests", ["analysis_id"])

    op.create_table(
        "screenshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "analysis_id",
            sa.String(length=36),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_screenshots_analysis_id", "screenshots", ["analysis_id"])


def downgrade() -> None:
    op.drop_index("ix_screenshots_analysis_id", table_name="screenshots")
    op.drop_table("screenshots")
    op.drop_index("ix_network_requests_analysis_id", table_name="network_requests")
    op.drop_table("network_requests")
    op.drop_column("analyses", "screenshot_mime")
    op.drop_column("analyses", "screenshot_path")
    op.drop_column("analyses", "browser_data")
