import pytest

from utils.time_utils import seconds_to_hhmmss, hhmmss_to_seconds


def test_seconds_to_hhmmss_3661():
    assert seconds_to_hhmmss(3661) == "01:01:01"


def test_hhmmss_to_seconds_01_01_01():
    assert hhmmss_to_seconds("01:01:01") == 3661


def test_seconds_to_hhmmss_600():
    assert seconds_to_hhmmss(600) == "00:10:00"


def test_hhmmss_to_seconds_10_00():
    assert hhmmss_to_seconds("10:00") == 600
