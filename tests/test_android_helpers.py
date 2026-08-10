from lazulinet.platform.android.wifi import _frequency_to_channel


def test_frequency_to_channel_common_bands():
    assert _frequency_to_channel(2412) == 1
    assert _frequency_to_channel(2437) == 6
    assert _frequency_to_channel(2484) == 14
    assert _frequency_to_channel(5180) == 36
    assert _frequency_to_channel(5955) == 1
    assert _frequency_to_channel(9999) is None
