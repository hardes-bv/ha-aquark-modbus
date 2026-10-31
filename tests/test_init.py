"""Placeholder test for the aquark_modbus integration.

Verifies that the pytest + `pytest-homeassistant-custom-component`
stack is functional; real integration tests will replace this.
"""

from homeassistant.core import CoreState, HomeAssistant


def test_placeholder(hass: HomeAssistant) -> None:
    """Smoke test: the HA test instance is up and running."""
    assert hass.state == CoreState.running
