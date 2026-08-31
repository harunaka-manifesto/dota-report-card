import asyncio

from app.workers import tasks


class _LoopBoundAsyncClient:
    def __init__(self) -> None:
        self.loop: asyncio.AbstractEventLoop | None = None

    async def request(self) -> None:
        loop = asyncio.get_running_loop()
        if self.loop is None:
            self.loop = loop
        elif self.loop is not loop:
            raise RuntimeError("Event loop is closed")


class _Repository:
    def get_job(self, job_id: str) -> object:
        return job_id


class _Service:
    def __init__(self) -> None:
        self.repository = _Repository()
        self.client = _LoopBoundAsyncClient()
        self.loops: list[asyncio.AbstractEventLoop] = []

    async def run_job(self, _job: object, _identifier: object) -> None:
        self.loops.append(asyncio.get_running_loop())
        await self.client.request()


def test_analysis_tasks_keep_persistent_async_clients_on_one_worker_loop(monkeypatch) -> None:
    service = _Service()
    monkeypatch.setattr(tasks, "_service", service)
    monkeypatch.setattr(tasks, "_runner", None)

    try:
        tasks.run_analysis_task.run("job-1", 1, "player-1")
        tasks.run_analysis_task.run("job-2", 2, "player-2")
    finally:
        tasks._close_runner()

    assert len(service.loops) == 2
    assert service.loops[0] is service.loops[1]
