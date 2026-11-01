"""Tests for the integration constants."""

import pytest

from custom_components.aquark_modbus.const import unique_id_for
from tests.conftest import serial_entry_data, tcp_entry_data


def test_unique_id_for_tcp() -> None:
    """The TCP unique id matches the format used by the conftest."""
    assert unique_id_for(tcp_entry_data()) == "tcp:192.168.1.50:502:8"


def test_unique_id_for_tcp_custom_values() -> None:
    """Host, port, and unit all appear in the id, in order."""
    data = tcp_entry_data(host="10.0.0.1", port=1502, unit=12)
    assert unique_id_for(data) == "tcp:10.0.0.1:1502:12"


def test_unique_id_for_serial() -> None:
    """The serial unique id matches the format used by the conftest."""
    assert unique_id_for(serial_entry_data()) == "serial:/dev/ttyUSB0:8"


def test_unique_id_for_unknown_connection() -> None:
    """An unrecognized connection type raises instead of guessing."""
    with pytest.raises(ValueError, match="Unknown connection type"):
        unique_id_for({"connection": "dialup", "unit": 8})
