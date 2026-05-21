"""nasa fetch runs

Revision ID: 0004_nasa_fetch_runs
Revises: 0003_fire_clusters
Create Date: 2026-05-19

"""

from alembic import op


revision = "0004_nasa_fetch_runs"
down_revision = "0003_fire_clusters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS nasa_fetch_runs (
            id SERIAL PRIMARY KEY,
            started_at TIMESTAMP NOT NULL,
            finished_at TIMESTAMP NOT NULL,
            duration_seconds DOUBLE PRECISION,
            status VARCHAR(20) NOT NULL,
            received_count INTEGER DEFAULT 0,
            inserted_count INTEGER DEFAULT 0,
            duplicate_count INTEGER DEFAULT 0,
            source_error_count INTEGER DEFAULT 0,
            row_error_count INTEGER DEFAULT 0,
            v3_prediction_count INTEGER DEFAULT 0,
            prediction_limit_per_fetch INTEGER,
            prediction_limit_applied BOOLEAN DEFAULT FALSE,
            prediction_limit_note TEXT,
            received_by_source JSON DEFAULT '{}'::json,
            inserted_by_source JSON DEFAULT '{}'::json,
            duplicates_by_source JSON DEFAULT '{}'::json,
            row_errors_by_source JSON DEFAULT '{}'::json,
            predictions_by_source JSON DEFAULT '{}'::json,
            source_errors JSON DEFAULT '[]'::json,
            weather_timeout_count INTEGER DEFAULT 0,
            weather_fallback_count INTEGER DEFAULT 0,
            weather_error_count INTEGER DEFAULT 0,
            error_message TEXT,
            created_at TIMESTAMP
        )
        """
    )
    op.execute('CREATE INDEX IF NOT EXISTS ix_nasa_fetch_runs_finished_at ON nasa_fetch_runs (finished_at DESC)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_nasa_fetch_runs_status ON nasa_fetch_runs (status)')


def downgrade() -> None:
    op.drop_index("ix_nasa_fetch_runs_status", table_name="nasa_fetch_runs")
    op.drop_index("ix_nasa_fetch_runs_finished_at", table_name="nasa_fetch_runs")
    op.drop_table("nasa_fetch_runs")
