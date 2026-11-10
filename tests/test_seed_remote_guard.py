from types import SimpleNamespace

import pytest

from backend.app.core.config import settings
from seed.seed_data import seed_database


def test_remote_seed_requires_explicit_cli_flag_and_demo_environment(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "demo")
    monkeypatch.setenv("ALLOW_REMOTE_DEMO_SEED", "true")
    remote_engine = SimpleNamespace(url="postgresql+psycopg://user:secret@ep-example.neon.tech/township")

    with pytest.raises(RuntimeError, match="--allow-remote-demo-seed"):
        seed_database(target_engine=remote_engine, mode="safe", allow_remote_demo_seed=False)


def test_remote_seed_requires_explicit_environment_opt_in(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "demo")
    monkeypatch.delenv("ALLOW_REMOTE_DEMO_SEED", raising=False)
    remote_engine = SimpleNamespace(url="postgresql+psycopg://user:secret@ep-example.neon.tech/township")

    with pytest.raises(RuntimeError, match="ALLOW_REMOTE_DEMO_SEED=true"):
        seed_database(target_engine=remote_engine, mode="safe", allow_remote_demo_seed=True)


def test_remote_destructive_reset_is_rejected_even_with_both_opt_ins(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "demo")
    monkeypatch.setenv("ALLOW_REMOTE_DEMO_SEED", "true")
    remote_engine = SimpleNamespace(url="postgresql+psycopg://user:secret@ep-example.neon.tech/township")

    with pytest.raises(RuntimeError, match="remote database"):
        seed_database(
            target_engine=remote_engine,
            mode="reset-demo",
            confirm_local_demo=True,
            allow_remote_demo_seed=True,
        )
