import pytest

from lazulinet.domain.errors import ValidationError
from lazulinet.domain.validation import validate_channel, validate_interface_name


def test_interface_validation_rejects_shell_metacharacters():
    with pytest.raises(ValidationError):
        validate_interface_name("wlan0;id")


def test_channel_validation():
    assert validate_channel(6) == 6
    with pytest.raises(ValidationError):
        validate_channel(999)
