"""fire clusters

Revision ID: 0003_fire_clusters
Revises: 0002_scheduler_state
Create Date: 2026-05-19

"""

from alembic import op
import sqlalchemy as sa


revision = "0003_fire_clusters"
down_revision = "0002_scheduler_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS fire_clusters (
            id SERIAL PRIMARY KEY,
            center_latitude DOUBLE PRECISION NOT NULL,
            center_longitude DOUBLE PRECISION NOT NULL,
            first_seen_at TIMESTAMP NOT NULL,
            last_seen_at TIMESTAMP NOT NULL,
            hotspot_count INTEGER DEFAULT 0,
            max_fire_probability DOUBLE PRECISION,
            max_risk_level VARCHAR(20),
            sources JSON DEFAULT '[]'::json,
            satellites JSON DEFAULT '[]'::json,
            status VARCHAR(20) DEFAULT 'active',
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
        """
    )
    op.execute('ALTER TABLE hotspots ADD COLUMN IF NOT EXISTS cluster_id INTEGER')
    op.execute('ALTER TABLE alerts ADD COLUMN IF NOT EXISTS cluster_id INTEGER')
    op.execute('CREATE INDEX IF NOT EXISTS ix_fire_clusters_id ON fire_clusters (id)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_fire_clusters_status ON fire_clusters (status)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_fire_clusters_last_seen_at ON fire_clusters (last_seen_at DESC)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_fire_clusters_status_last_seen ON fire_clusters (status, last_seen_at DESC)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_fire_clusters_max_risk_level ON fire_clusters (max_risk_level)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_hotspots_cluster_id ON hotspots (cluster_id)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_alerts_cluster_status ON alerts (cluster_id, status)')
    op.execute("DROP INDEX IF EXISTS ux_alerts_one_active_per_cluster")


def downgrade() -> None:
    op.drop_index("ix_alerts_cluster_status", table_name="alerts")
    op.drop_constraint("fk_alerts_cluster_id_fire_clusters", "alerts", type_="foreignkey")
    op.drop_column("alerts", "cluster_id")

    op.drop_index("ix_hotspots_cluster_id", table_name="hotspots")
    op.drop_constraint("fk_hotspots_cluster_id_fire_clusters", "hotspots", type_="foreignkey")
    op.drop_column("hotspots", "cluster_id")

    op.drop_index("ix_fire_clusters_max_risk_level", table_name="fire_clusters")
    op.drop_index("ix_fire_clusters_status_last_seen", table_name="fire_clusters")
    op.drop_index("ix_fire_clusters_last_seen_at", table_name="fire_clusters")
    op.drop_index("ix_fire_clusters_status", table_name="fire_clusters")
    op.drop_index(op.f("ix_fire_clusters_id"), table_name="fire_clusters")
    op.drop_table("fire_clusters")
