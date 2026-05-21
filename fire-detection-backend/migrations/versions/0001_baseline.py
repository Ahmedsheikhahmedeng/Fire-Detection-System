"""baseline

Revision ID: 0001_baseline
Revises:
Create Date: 2026-05-09

"""

from alembic import op
import sqlalchemy as sa


revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fire_clusters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("center_latitude", sa.Float(), nullable=False),
        sa.Column("center_longitude", sa.Float(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("hotspot_count", sa.Integer(), nullable=True),
        sa.Column("max_fire_probability", sa.Float(), nullable=True),
        sa.Column("max_risk_level", sa.String(length=20), nullable=True),
        sa.Column("sources", sa.JSON(), nullable=True),
        sa.Column("satellites", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_fire_clusters_id"), "fire_clusters", ["id"], unique=False)
    op.create_index(
        "ix_fire_clusters_status_last_seen",
        "fire_clusters",
        ["status", sa.text("last_seen_at DESC")],
        unique=False,
    )

    op.create_table(
        "hotspots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cluster_id", sa.Integer(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("brightness", sa.Float(), nullable=True),
        sa.Column("bright_ti5", sa.Float(), nullable=True),
        sa.Column("frp", sa.Float(), nullable=True),
        sa.Column("scan", sa.Float(), nullable=True),
        sa.Column("track", sa.Float(), nullable=True),
        sa.Column("confidence", sa.String(length=50), nullable=True),
        sa.Column("daynight", sa.String(length=20), nullable=True),
        sa.Column("satellite", sa.String(length=50), nullable=True),
        sa.Column("instrument", sa.String(length=50), nullable=True),
        sa.Column("firms_source", sa.String(length=100), nullable=True),
        sa.Column("type", sa.Float(), nullable=True),
        sa.Column("version", sa.Float(), nullable=True),
        sa.Column("acq_date", sa.Date(), nullable=True),
        sa.Column("acq_time", sa.String(length=50), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["cluster_id"], ["fire_clusters.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_hotspots_id"), "hotspots", ["id"], unique=False)
    op.create_index("ix_hotspots_cluster_id", "hotspots", ["cluster_id"], unique=False)
    op.create_index(
        "ix_hotspots_firms_observation",
        "hotspots",
        ["latitude", "longitude", "acq_date", "acq_time", "satellite", "instrument", "firms_source"],
        unique=False,
    )
    op.create_index(
        "ux_hotspots_firms_observation",
        "hotspots",
        ["latitude", "longitude", "acq_date", "acq_time", "satellite", "instrument", "firms_source"],
        unique=True,
        postgresql_where=sa.text(
            "acq_date IS NOT NULL "
            "AND acq_time IS NOT NULL "
            "AND satellite IS NOT NULL "
            "AND instrument IS NOT NULL "
            "AND firms_source IS NOT NULL"
        ),
    )

    op.create_table(
        "weather_data",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hotspot_id", sa.Integer(), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("humidity", sa.Float(), nullable=True),
        sa.Column("wind_speed", sa.Float(), nullable=True),
        sa.Column("pressure", sa.Float(), nullable=True),
        sa.Column("rain_1h", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["hotspot_id"], ["hotspots.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_weather_data_id"), "weather_data", ["id"], unique=False)

    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hotspot_id", sa.Integer(), nullable=True),
        sa.Column("fire_probability", sa.Float(), nullable=True),
        sa.Column("risk_level", sa.String(length=20), nullable=True),
        sa.Column("decision_level", sa.Integer(), nullable=True),
        sa.Column("decision_name", sa.String(length=100), nullable=True),
        sa.Column("model_version", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["hotspot_id"], ["hotspots.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_predictions_id"), "predictions", ["id"], unique=False)
    op.create_index(
        "ix_predictions_hotspot_id_id",
        "predictions",
        ["hotspot_id", sa.text("id DESC")],
        unique=False,
    )

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hotspot_id", sa.Integer(), nullable=True),
        sa.Column("cluster_id", sa.Integer(), nullable=True),
        sa.Column("risk_level", sa.String(length=20), nullable=True),
        sa.Column("message", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["cluster_id"], ["fire_clusters.id"]),
        sa.ForeignKeyConstraint(["hotspot_id"], ["hotspots.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_alerts_id"), "alerts", ["id"], unique=False)
    op.create_index(
        "ix_alerts_hotspot_status",
        "alerts",
        ["hotspot_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_alerts_cluster_status",
        "alerts",
        ["cluster_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_alerts_status_created_at",
        "alerts",
        ["status", sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "ux_alerts_one_active_per_hotspot",
        "alerts",
        ["hotspot_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE' AND hotspot_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_alerts_cluster_status", table_name="alerts")
    op.drop_index("ux_alerts_one_active_per_hotspot", table_name="alerts")
    op.drop_index("ix_alerts_status_created_at", table_name="alerts")
    op.drop_index("ix_alerts_hotspot_status", table_name="alerts")
    op.drop_index(op.f("ix_alerts_id"), table_name="alerts")
    op.drop_table("alerts")

    op.drop_index("ix_predictions_hotspot_id_id", table_name="predictions")
    op.drop_index(op.f("ix_predictions_id"), table_name="predictions")
    op.drop_table("predictions")

    op.drop_index(op.f("ix_weather_data_id"), table_name="weather_data")
    op.drop_table("weather_data")

    op.drop_index("ux_hotspots_firms_observation", table_name="hotspots")
    op.drop_index("ix_hotspots_firms_observation", table_name="hotspots")
    op.drop_index("ix_hotspots_cluster_id", table_name="hotspots")
    op.drop_index(op.f("ix_hotspots_id"), table_name="hotspots")
    op.drop_table("hotspots")

    op.drop_index("ix_fire_clusters_status_last_seen", table_name="fire_clusters")
    op.drop_index(op.f("ix_fire_clusters_id"), table_name="fire_clusters")
    op.drop_table("fire_clusters")
