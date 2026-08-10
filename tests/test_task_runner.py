import time

from lazulinet.application.task_runner import TaskRunner
from lazulinet.domain.models import TaskState


def wait_terminal(handle, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        snap = handle.snapshot()
        if snap.state in (TaskState.COMPLETED, TaskState.CANCELLED, TaskState.FAILED):
            return snap
        time.sleep(0.01)
    raise AssertionError("task did not finish")


def test_runner_completes_and_emits_events():
    runner = TaskRunner()
    handle = runner.submit("unit", lambda cancel, emit: 7)
    snap = wait_terminal(handle)
    assert snap.state == TaskState.COMPLETED
    assert snap.result == 7
    kinds = [e.kind for e in runner.poll_events()]
    assert "TaskStarted" in kinds
    assert "TaskCompleted" in kinds


def test_runner_cancel_is_cooperative():
    runner = TaskRunner()

    def worker(cancel, emit):
        while not cancel.wait(0.01):
            pass
        return "stopped"

    handle = runner.submit("cancel", worker)
    time.sleep(0.03)
    handle.cancel()
    snap = wait_terminal(handle)
    assert snap.state == TaskState.CANCELLED
