from __future__ import annotations

import os

from lazulinet.application.services import DiscoveryService, InterfaceService, LazuliRuntime
from lazulinet.application.session_repository import SessionRepository
from lazulinet.application.task_runner import TaskRunner


def create_runtime(data_root=None) -> LazuliRuntime:
    repo = SessionRepository(data_root)
    runner = TaskRunner()

    if os.environ.get("ANDROID_ARGUMENT"):
        from lazulinet.platform.android.wifi import AndroidWifiAdapter
        adapter = AndroidWifiAdapter()
        interface_adapter = adapter
        discovery_adapter = adapter
    else:
        from lazulinet.platform.debian.interface import DebianInterfaceAdapter
        from lazulinet.platform.debian.discovery import DebianDiscoveryAdapter
        interface_adapter = DebianInterfaceAdapter()
        discovery_adapter = DebianDiscoveryAdapter()

    return LazuliRuntime(
        interface=InterfaceService(interface_adapter),
        discovery=DiscoveryService(discovery_adapter, repo, runner),
        sessions=repo,
        tasks=runner,
    )
