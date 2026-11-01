# Home Assistant Integration for Aquark (Modbus)

[![GitHub Release](https://img.shields.io/github/release/hardes-bv/ha-aquark-modbus.svg)](https://github.com/hardes-bv/ha-aquark-modbus/releases)

This integration enables monitoring and control of Aquark pool equipment in Home Assistant — salt chlorinators —
connecting locally to the devices via Modbus TCP or RTU.

## Supported devices

| Device | Status |
| --- | --- |
| Mr Pure | Untested |
| Inverclear | Untested |
| Mr Pure Pro | Untested |

If you have one of the untested models above, please create an issue to report whether it works or not.

The device support comes from the [aquark-modbus](https://github.com/hardes-bv/python-aquark-modbus)
library, which Home Assistant installs from PyPI.

## Installation

Home Assistant 2026.10.2 or later: the test package this code comes from ran on 2026.10.2, and the tests run on 2026.10.3.

1. In HACS, open the menu, select **Custom repositories**, and add
   `https://github.com/hardes-bv/ha-aquark-modbus` as an **Integration**.
2. Install **Aquark (Modbus)**, then restart Home Assistant.

## Connecting the chlorinator

The control board has a 2-pin RS485 port marked `B` and `A`. Wire it to
either:

- an RS485 to Modbus TCP gateway, set to **Modbus TCP to RTU**, 9600 baud, 8 data bits,
  no parity, 1 stop bit;
- or a USB RS485 adapter on the Home Assistant host.

Swap `A` and `B` if the heat pump does not answer. The board answers at Modbus address 8 by default.

## Configuration

Go to **Settings** > **Devices & services** > **Add integration**, select
**Aquark (Modbus)**, then choose the network or the serial port and enter the gateway
address or the adapter.

## License
This project is licensed under the Apache v2 License - see the LICENSE file for details.
