class LazuliNetError(RuntimeError):
    """Base typed application error."""


class ValidationError(LazuliNetError):
    pass


class DependencyMissing(LazuliNetError):
    pass


class PrivilegeUnavailable(LazuliNetError):
    pass


class InterfaceNotFound(LazuliNetError):
    pass


class UnsupportedMonitorMode(LazuliNetError):
    pass


class ProcessFailed(LazuliNetError):
    pass


class ProcessTimeout(LazuliNetError):
    pass


class ParseError(LazuliNetError):
    pass


class StorageError(LazuliNetError):
    pass
