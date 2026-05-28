import asyncio

from fastapi.responses import JSONResponse

import src.app as app_module


class _FakeTaskService:
    def __init__(self, _repo):
        self.updated = []

    async def get_all_tasks(self):
        return []

    async def update_task_status(self, task_id, is_running):
        self.updated.append((task_id, is_running))


class _FakeSchedulerService:
    def __init__(self):
        self.started = False
        self.stopped = False
        self.reload_payload = None

    async def reload_jobs(self, tasks):
        self.reload_payload = list(tasks)

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


class _FakeProcessService:
    def __init__(self):
        self.stop_all_called = False

    async def stop_all(self):
        self.stop_all_called = True


def test_lifespan_cleans_task_logs_on_startup(monkeypatch):
    called = {}
    fake_scheduler = _FakeSchedulerService()
    fake_process = _FakeProcessService()

    monkeypatch.setattr(app_module, "scheduler_service", fake_scheduler)
    monkeypatch.setattr(app_module, "process_service", fake_process)
    monkeypatch.setattr(app_module, "TaskService", _FakeTaskService)
    monkeypatch.setattr(app_module, "SqliteTaskRepository", lambda: object())
    monkeypatch.setattr(app_module, "bootstrap_sqlite_storage", lambda: called.setdefault("bootstrapped", True))
    monkeypatch.setattr(
        app_module,
        "cleanup_task_logs",
        lambda *args, **kwargs: called.setdefault("keep_days", kwargs.get("keep_days")),
    )
    monkeypatch.setattr(app_module.app_settings, "task_log_retention_days", 9)

    async def _run():
        async with app_module.lifespan(None):
            assert fake_scheduler.started is True
            assert fake_scheduler.reload_payload == []

    asyncio.run(_run())

    assert called["bootstrapped"] is True
    assert called["keep_days"] == 9
    assert fake_scheduler.stopped is True
    assert fake_process.stop_all_called is True


class _FakeUrl:
    def __init__(self, path):
        self.path = path


class _FakeRequest:
    def __init__(self, path):
        self.url = _FakeUrl(path)


class _FakeLicenseStatus:
    authorized = False
    code = "LICENSE_DISABLED"
    message = "授权码已被禁用"


class _FakeLicenseManager:
    def __init__(self):
        self.refresh_calls = []

    def is_enabled(self):
        return True

    def refresh_authorization(self, *, force=False):
        self.refresh_calls.append(force)
        return _FakeLicenseStatus()

    def get_status(self):
        return _FakeLicenseStatus()


def test_enforce_license_force_refreshes_protected_api(monkeypatch):
    fake_license = _FakeLicenseManager()
    monkeypatch.setattr(app_module, "license_manager", fake_license)

    async def call_next(_request):
        return JSONResponse({"ok": True})

    response = asyncio.run(app_module.enforce_license(_FakeRequest("/api/tasks"), call_next))

    assert fake_license.refresh_calls == [True]
    assert response.status_code == 403
