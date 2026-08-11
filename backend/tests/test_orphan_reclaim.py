"""Orphan run reclaim — fail stuck BackgroundTasks runs + refund usage."""

from datetime import datetime, timedelta, timezone

import pytest

from app.config import settings
from app.models.domain.pipeline import PlannedStep
from app.models.domain.run import RunResult, StepRunRecord
from app.persistence.memory_repository import MemoryRepository
from app.services.pipeline import orphan_reclaim
from app.services.usage import metering
from app.services.usage.metering import record_usage


def _running_run(
    *,
    run_id: str = "run-1",
    created_at: str | None = None,
) -> RunResult:
    return RunResult(
        run_id=run_id,
        upload_id="up-1",
        task_description="extract",
        status="running",
        steps=[
            StepRunRecord(
                step_order=1,
                agent_type="transform.field_extractor",
                status="running",
            ),
            StepRunRecord(
                step_order=2,
                agent_type="output.formatter",
                status="queued",
            ),
        ],
        planned_steps=[
            PlannedStep(
                step_order=1,
                agent_type="transform.field_extractor",
                config={"fields": ["vendor"]},
                reason="extract",
            )
        ],
        user_id="user-1",
        created_at=created_at or datetime.now(timezone.utc).isoformat(),
    )


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    metering.reset_memory_usage()
    monkeypatch.setattr(
        "app.persistence.supabase_repository.is_supabase_configured",
        lambda: False,
    )
    monkeypatch.setattr(settings, "orphan_run_stale_minutes", 30)
    yield
    metering.reset_memory_usage()


@pytest.mark.asyncio
async def test_fail_orphan_run_marks_failed_and_refunds(monkeypatch):
    repo = MemoryRepository()
    run = _running_run()
    repo.save_run(run)
    monkeypatch.setattr("app.persistence.get_repository", lambda: repo)
    monkeypatch.setattr(
        "app.services.pipeline.orphan_reclaim.get_repository",
        lambda: repo,
    )
    monkeypatch.setattr(
        "app.services.pipeline.orphan_reclaim.save_run",
        repo.save_run,
    )
    monkeypatch.setattr("app.persistence.get_run", repo.get_run)

    await record_usage("user-1", 3, run_id=run.run_id, event_type="extraction")

    failed = await orphan_reclaim.fail_orphan_run(run, "test reclaim")
    assert failed.status == "failed"
    assert failed.error_message == "test reclaim"
    assert all(s.status == "failed" for s in failed.steps)

    stored = repo.get_run(run.run_id)
    assert stored is not None
    assert stored.status == "failed"

    charged = await metering._pages_charged_for_run(run.run_id)
    assert charged == 0


@pytest.mark.asyncio
async def test_reclaim_all_running(monkeypatch):
    repo = MemoryRepository()
    repo.save_run(_running_run(run_id="a"))
    repo.save_run(_running_run(run_id="b"))
    repo.save_run(
        RunResult(
            run_id="c",
            upload_id="up",
            task_description="",
            status="completed",
            steps=[],
            created_at=datetime.now(timezone.utc).isoformat(),
        )
    )
    monkeypatch.setattr(
        "app.services.pipeline.orphan_reclaim.get_repository",
        lambda: repo,
    )
    monkeypatch.setattr(
        "app.services.pipeline.orphan_reclaim.save_run",
        repo.save_run,
    )

    count = await orphan_reclaim.reclaim_all_running()
    assert count == 2
    assert repo.get_run("a").status == "failed"
    assert repo.get_run("b").status == "failed"
    assert repo.get_run("c").status == "completed"


@pytest.mark.asyncio
async def test_maybe_reclaim_run_noops_when_fresh(monkeypatch):
    repo = MemoryRepository()
    run = _running_run(
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    repo.save_run(run)
    monkeypatch.setattr(
        "app.services.pipeline.orphan_reclaim.save_run",
        repo.save_run,
    )

    result = await orphan_reclaim.maybe_reclaim_run(run)
    assert result.status == "running"


@pytest.mark.asyncio
async def test_maybe_reclaim_run_fails_when_stale(monkeypatch):
    repo = MemoryRepository()
    old = (datetime.now(timezone.utc) - timedelta(minutes=45)).isoformat()
    run = _running_run(created_at=old)
    repo.save_run(run)
    monkeypatch.setattr(
        "app.services.pipeline.orphan_reclaim.save_run",
        repo.save_run,
    )

    result = await orphan_reclaim.maybe_reclaim_run(run)
    assert result.status == "failed"
    assert repo.get_run(run.run_id).status == "failed"


@pytest.mark.asyncio
async def test_reclaim_stale_running_only_old(monkeypatch):
    repo = MemoryRepository()
    now = datetime.now(timezone.utc)
    repo.save_run(
        _running_run(
            run_id="fresh",
            created_at=now.isoformat(),
        )
    )
    repo.save_run(
        _running_run(
            run_id="stale",
            created_at=(now - timedelta(minutes=60)).isoformat(),
        )
    )
    monkeypatch.setattr(
        "app.services.pipeline.orphan_reclaim.get_repository",
        lambda: repo,
    )
    monkeypatch.setattr(
        "app.services.pipeline.orphan_reclaim.save_run",
        repo.save_run,
    )

    count = await orphan_reclaim.reclaim_stale_running(max_age_minutes=30)
    assert count == 1
    assert repo.get_run("fresh").status == "running"
    assert repo.get_run("stale").status == "failed"
