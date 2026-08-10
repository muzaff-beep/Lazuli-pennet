from __future__ import annotations

import queue
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from lazulinet.domain.models import TaskEvent, TaskState

Worker = Callable[[threading.Event, Callable[[str, str, float | None, dict | None], None]], Any]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(slots=True)
class TaskSnapshot:
    id: str
    kind: str
    state: TaskState
    started_at: str = ""
    ended_at: str = ""
    error: str = ""
    result: Any = None


class TaskHandle:
    def __init__(self, task_id: str, kind: str):
        self.id = task_id
        self.kind = kind
        self._state = TaskState.QUEUED
        self._started_at = ""
        self._ended_at = ""
        self._error = ""
        self._result: Any = None
        self._cancel = threading.Event()
        self._lock = threading.RLock()

    @property
    def cancel_event(self) -> threading.Event:
        return self._cancel

    def cancel(self) -> None:
        with self._lock:
            if self._state in (TaskState.QUEUED, TaskState.RUNNING):
                self._state = TaskState.CANCELLING
                self._cancel.set()

    def snapshot(self) -> TaskSnapshot:
        with self._lock:
            return TaskSnapshot(
                id=self.id,
                kind=self.kind,
                state=self._state,
                started_at=self._started_at,
                ended_at=self._ended_at,
                error=self._error,
                result=self._result,
            )

    def _set_running(self) -> None:
        with self._lock:
            self._state = TaskState.RUNNING
            self._started_at = _now()

    def _set_result(self, result: Any) -> None:
        with self._lock:
            self._result = result
            self._state = TaskState.CANCELLED if self._cancel.is_set() else TaskState.COMPLETED
            self._ended_at = _now()

    def _set_error(self, exc: BaseException) -> None:
        with self._lock:
            self._error = f"{type(exc).__name__}: {exc}"
            self._state = TaskState.CANCELLED if self._cancel.is_set() else TaskState.FAILED
            self._ended_at = _now()


class TaskRunner:
    """Small cancellable background runner with pollable structured events."""

    def __init__(self):
        self._handles: dict[str, TaskHandle] = {}
        self._events: "queue.Queue[TaskEvent]" = queue.Queue()
        self._lock = threading.RLock()

    def submit(self, kind: str, worker: Worker) -> TaskHandle:
        task_id = uuid.uuid4().hex
        handle = TaskHandle(task_id, kind)
        with self._lock:
            self._handles[task_id] = handle

        def emit(event_kind: str, message: str, progress: float | None = None, payload: dict | None = None):
            self._events.put(TaskEvent(task_id, event_kind, message, progress=progress, payload=payload or {}))

        def target():
            handle._set_running()
            emit("TaskStarted", f"{kind} started", 0.0)
            try:
                result = worker(handle.cancel_event, emit)
                handle._set_result(result)
                snap = handle.snapshot()
                final_kind = "TaskCancelled" if snap.state == TaskState.CANCELLED else "TaskCompleted"
                emit(final_kind, f"{kind} {snap.state.value}", 1.0, {"result": result})
            except BaseException as exc:
                handle._set_error(exc)
                snap = handle.snapshot()
                final_kind = "TaskCancelled" if snap.state == TaskState.CANCELLED else "TaskFailed"
                emit(final_kind, snap.error, None)

        thread = threading.Thread(target=target, name=f"lazulinet-{kind}-{task_id[:8]}", daemon=True)
        thread.start()
        return handle

    def get(self, task_id: str) -> TaskHandle | None:
        with self._lock:
            return self._handles.get(task_id)

    def poll_events(self, limit: int = 100) -> list[TaskEvent]:
        events: list[TaskEvent] = []
        for _ in range(max(0, limit)):
            try:
                events.append(self._events.get_nowait())
            except queue.Empty:
                break
        return events
