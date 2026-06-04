from __future__ import annotations

import logging

from homeassistant import config_entries, core
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# (key, friendly name, state_service attribute, icon)
BINARY_SENSORS = (
    ("pure_direct", "Pure Direct", "pure_direct", "mdi:speaker"),
    ("auto_standby", "Auto Standby", "auto_standby", "mdi:timer-cog-outline"),
    (
        "auto_phase_matching",
        "Auto Phase Matching",
        "auto_phase_matching",
        "mdi:sine-wave",
    ),
)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
) -> None:
    config = hass.data[DOMAIN][config_entry.entry_id]

    if config_entry.options:
        config.update(config_entry.options)

    sonyavr = config["sonyavr"]

    async_add_entities(
        SonyAVRBinarySensor(sonyavr, hass, key, name, attr, icon)
        for key, name, attr, icon in BINARY_SENSORS
    )


class SonyAVRBinarySensor(BinarySensorEntity):
    """Read-only sensor for a decoded boolean device state.

    These values are already parsed from the AVR's feedback stream but were
    never surfaced as entities. They are read-only because the corresponding
    'set' commands have not been verified yet.
    """

    def __init__(self, device, hass, key, name, attr, icon):
        self._device = device
        self._hass = hass
        self._key = key
        self._name = name
        self._attr = attr
        self._icon = icon
        self._entity_id = f"binary_sensor.sonyavr_{key}"
        self._base_id = "sonyavr_" + self._device.name.replace(" ", "_").replace(
            "-", "_"
        ).replace(":", "_")
        self._unique_id = self._base_id + f"_{key}"

    async def async_added_to_hass(self):
        """Subscribe to device events."""
        self._device.add_update_listener(self.async_update_callback)

    async def async_will_remove_from_hass(self) -> None:
        self._device.remove_update_listener(self.async_update_callback)

    @callback
    def async_update_callback(self, reason=False):
        """Update the entity's state."""
        self.async_schedule_update_ha_state()

    @property
    def should_poll(self):
        return False

    @property
    def name(self):
        return self._name

    @property
    def has_entity_name(self):
        return True

    @property
    def icon(self):
        return self._icon

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
    def is_on(self) -> bool | None:
        return getattr(self._device.state_service, self._attr)
