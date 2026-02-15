from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from app.core.config import settings

OLD_REVISION = "9c1a2f7e4b11"
NEW_REVISION = "a7c1f2d4e9b3"


def _alembic_config(db_url: str) -> Config:
    backend_dir = Path(__file__).resolve().parents[1]
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def test_tenant_visibility_migration_backfills_and_adds_constraints(tmp_path: Path):
    db_path = tmp_path / "migration_test.db"
    db_url = f"sqlite:///{db_path}"
    cfg = _alembic_config(db_url)
    original_db_url = settings.database_url
    settings.database_url = db_url
    try:
        command.upgrade(cfg, OLD_REVISION)

        engine = create_engine(db_url)
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO projects (id, name, description)
                    VALUES ('proj-legacy-1', 'Legacy Project', 'migrated row')
                    """
                )
            )

        command.upgrade(cfg, NEW_REVISION)

        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("projects")}
        assert "owner_user_id" in columns
        assert "visibility" in columns
        assert "forked_from_project_id" in columns

        indexes = {idx["name"] for idx in inspector.get_indexes("projects")}
        assert "ix_projects_owner_user_id" in indexes
        assert "ix_projects_visibility" in indexes
        assert "ix_projects_forked_from_project_id" in indexes

        with engine.begin() as conn:
            row = conn.execute(
                text("SELECT owner_user_id, visibility FROM projects WHERE id = 'proj-legacy-1'")
            ).one()
            assert row.owner_user_id == "legacy"
            assert row.visibility == "private"

        with pytest.raises(IntegrityError):
            with engine.begin() as conn:
                conn.execute(text("UPDATE projects SET visibility = 'invalid' WHERE id = 'proj-legacy-1'"))

        engine.dispose()
    finally:
        settings.database_url = original_db_url
