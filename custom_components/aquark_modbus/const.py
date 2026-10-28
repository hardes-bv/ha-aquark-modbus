"""Constants for the Aquark Modbus integration."""

from datetime import timedelta
from typing import Final

DOMAIN = "aquark_modbus"
MANUFACTURER = "Aquark"

CONF_UNIT_ID = "unit_id"
DEFAULT_UNIT_ID = 8  # TODO: migrate this constant to aquark-modbus library

TYPE_SERIAL = "serial"
TYPE_TCP = "tcp"

DEFAULT_PORT = 502

# The board's fixed line settings: 9600 baud, 8 data bits, no parity, 1 stop bit.
SERIAL_BAUDRATE: Final = 9600
SERIAL_PARITY: Final = "N"
SERIAL_STOPBITS: Final = 1

UPDATE_INTERVAL = timedelta(seconds=30)
