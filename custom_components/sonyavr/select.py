from __future__ import annotations

import logging

from homeassistant import config_entries, core
from homeassistant.components.select import SelectEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
) -> None:
    config = hass.data[DOMAIN][config_entry.entry_id]

    if config_entry.options:
        config.update(config_entry.options)

    sonyavr = config["sonyavr"]

    async_add_entities([SonyAVRHDMIOutputSelect(sonyavr, hass)])


class SonyAVRHDMIOutputSelect(SelectEntity):
    """Selects the HDMI monitor output (A / B / A+B / Off).

    The receiver accepts the command but never reports the current output, so
    this entity is optimistic - it shows the last value we set.
    """

    _attr_icon = "mdi:hdmi-port"

    def __init__(self, device, hass):
        self._device = device
        self._hass = hass
        self._entity_id = "select.sonyavr_hdmi_output"
        self._base_id = "sonyavr_" + self._device.name.replace(" ", "_").replace(
            "-", "_"
        ).replace(":", "_")
        self._unique_id = self._base_id + "_hdmi_output"

    @property
    def should_poll(self):
        return False

    @property
    def name(self):
        return "HDMI Output"

    @property
    def has_entity_name(self):
        return True

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._base_id)},
            name=self._device.name,
            manufacturer="Sony",
            model=self._device.model,
        )

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def entity_id(self):
        return self._entity_id

    @entity_id.setter
    def entity_id(self, entity_id):
        self._entity_id = entity_id

    @property
    def options(self) -> list[str]:
        return list(self._device.hdmiout_options)

    @property
    def current_option(self) -> str | None:
        return self._device.hdmiout_select

    async def async_select_option(self, option: str) -> None:
        await self._device.async_set_hdmiout(option)
        self.async_write_ha_state()
