from __future__ import annotations

import logging

from homeassistant import config_entries, core
from homeassistant.components.select import SelectEntity
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

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


class SonyAVRHDMIOutputSelect(SelectEntity, RestoreEntity):
    """Selects the HDMI monitor output (A / B / A+B / Off).

    The receiver accepts the command but never reports the current output (no
    query, no notification), so this is a write-only, optimistic control: it
    shows the last value we sent and restores it across restarts.
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

    async def async_added_to_hass(self) -> None:
        """Restore the last selected output and subscribe to state updates."""
        await super().async_added_to_hass()
        if self._device.hdmiout_select is None:
            last = await self.async_get_last_state()
            if last and last.state in self._device.hdmiout_options:
                self._device.state_service.hdmiout_select = last.state
        # Re-render on power changes so availability/current option stay correct.
        self._device.add_update_listener(self.async_update_callback)

    async def async_will_remove_from_hass(self) -> None:
        self._device.remove_update_listener(self.async_update_callback)

    @callback
    def async_update_callback(self, reason=False):
        self.async_schedule_update_ha_state()

    @property
    def should_poll(self):
        return False

    @property
    def available(self) -> bool:
        # HDMI output can only be commanded while the AVR is on, and the device
        # never reports it back - so this is a write-only, optimistic control.
        return bool(self._device.state_service.power)

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
