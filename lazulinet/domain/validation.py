from __future__ import annotations

import re

from .errors import ValidationError

_INTERFACE_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,32}$")


def validate_interface_name(value: str) -> str:
    value = (value or "").strip()
    if not _INTERFACE_RE.fullmatch(value):
        raise ValidationError("Invalid wireless interface name.")
    return value


def validate_channel(value: int | None) -> int | None:
    if value is None:
        return None
    try:
        channel = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Channel must be an integer.") from exc
    if not 1 <= channel <= 233:
        raise ValidationError("Channel must be between 1 and 233.")
    return channel


def validate_duration(value: int) -> int:
    try:
        duration = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Duration must be an integer.") from exc
    if not 1 <= duration <= 3600:
        raise ValidationError("Duration must be between 1 and 3600 seconds.")
    return duration
