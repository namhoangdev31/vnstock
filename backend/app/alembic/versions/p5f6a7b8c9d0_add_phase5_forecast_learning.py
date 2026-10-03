"""Add Phase 5 forecast metrics, model snapshots, and immutable audit guard."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "p5f6a7b8c9d0"
down_revision = "1b271c617c0c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {column["name"] for column in inspector.get_columns("forecast_journal")}
    additions = {
        "predicted_probability": sa.Column(
            "predicted_probability", sa.Float(), nullable=True
        ),
        "predicted_price_low": sa.Column(
            "predicted_price_low", sa.Float(), nullable=True
        ),
        "predicted_price_high": sa.Column(
            "predicted_price_high", sa.Float(), nullable=True
        ),
        "directional_correct": sa.Column(
            "directional_correct", sa.Boolean(), nullable=True
        ),
        "brier_score": sa.Column("brier_score", sa.Float(), nullable=True),
        "absolute_error": sa.Column("absolute_error", sa.Float(), nullable=True),
    }
    for name, column in additions.items():
        if name not in existing:
            op.add_column("forecast_journal", column)

    if "model_version_snapshot" not in inspector.get_table_names():
        op.create_table(
            "model_version_snapshot",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("version_tag", sa.String(length=40), nullable=False),
            sa.Column("parameter_snapshot", JSONB(), nullable=False),
            sa.Column("w1", sa.Float(), nullable=False),
            sa.Column("w2", sa.Float(), nullable=False),
            sa.Column("w3", sa.Float(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("auto_promoted", sa.Boolean(), nullable=False),
            sa.Column("circuit_breaker_triggered", sa.Boolean(), nullable=False),
            sa.Column("auto_promotion_enabled", sa.Boolean(), nullable=False),
            sa.Column("baseline_version_tag", sa.String(length=40), nullable=True),
            sa.Column("rolling_da", sa.Float(), nullable=True),
            sa.Column("rolling_brier", sa.Float(), nullable=True),
            sa.Column("rolling_mae", sa.Float(), nullable=True),
            sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("rolled_back_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("rollback_reason", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("version_tag", name="uq_model_version_snapshot_tag"),
        )
    indexes = {
        index["name"]
        for index in sa.inspect(bind).get_indexes("model_version_snapshot")
    }
    if "uq_model_version_snapshot_active" not in indexes:
        op.create_index(
            "uq_model_version_snapshot_active",
            "model_version_snapshot",
            ["is_active"],
            unique=True,
            postgresql_where=sa.text("is_active = true"),
        )
    if bind.dialect.name == "postgresql":
        op.execute("""
        CREATE OR REPLACE FUNCTION reject_forecast_prediction_mutation() RETURNS trigger AS $$
        BEGIN
          IF NEW.predicted_at IS DISTINCT FROM OLD.predicted_at
             OR NEW.symbol IS DISTINCT FROM OLD.symbol
             OR NEW.horizon IS DISTINCT FROM OLD.horizon
             OR NEW.predicted_value IS DISTINCT FROM OLD.predicted_value
             OR NEW.predicted_direction IS DISTINCT FROM OLD.predicted_direction
             OR NEW.predicted_probability IS DISTINCT FROM OLD.predicted_probability
             OR NEW.predicted_price_low IS DISTINCT FROM OLD.predicted_price_low
             OR NEW.predicted_price_high IS DISTINCT FROM OLD.predicted_price_high
             OR NEW.engine_weights IS DISTINCT FROM OLD.engine_weights
             OR NEW.model_version IS DISTINCT FROM OLD.model_version
             OR NEW.parameter_snapshot IS DISTINCT FROM OLD.parameter_snapshot THEN
            RAISE EXCEPTION 'forecast prediction fields are immutable';
          END IF;
          RETURN NEW;
        END; $$ LANGUAGE plpgsql;
        """)
        op.execute(
            "DROP TRIGGER IF EXISTS forecast_prediction_immutable ON forecast_journal"
        )
        op.execute(
            "CREATE TRIGGER forecast_prediction_immutable BEFORE UPDATE ON forecast_journal FOR EACH ROW EXECUTE FUNCTION reject_forecast_prediction_mutation()"
        )
    count = bind.execute(
        sa.text("SELECT count(*) FROM model_version_snapshot")
    ).scalar_one()
    if count == 0:
        bind.execute(
            sa.text(
                "INSERT INTO model_version_snapshot (id, version_tag, parameter_snapshot, w1, w2, w3, is_active, auto_promoted, circuit_breaker_triggered, auto_promotion_enabled, created_at, updated_at) VALUES (:id, 'v2.0.0', :snapshot, 0.33, 0.33, 0.34, true, false, false, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"id": "00000000-0000-0000-0000-000000000005", "snapshot": "{}"},
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS forecast_prediction_immutable ON forecast_journal"
        )
        op.execute("DROP FUNCTION IF EXISTS reject_forecast_prediction_mutation()")
    op.drop_index(
        "uq_model_version_snapshot_active", table_name="model_version_snapshot"
    )
    op.drop_table("model_version_snapshot")
    for name in (
        "absolute_error",
        "brier_score",
        "directional_correct",
        "predicted_price_high",
        "predicted_price_low",
        "predicted_probability",
    ):
        op.drop_column("forecast_journal", name)
