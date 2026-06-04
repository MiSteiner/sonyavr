import logging
from typing import Any, Dict
from urllib.parse import urlparse

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries, core
from homeassistant.const import (
    CONF_HOST,
    CONF_MODEL,
    CONF_NAME,
    CONF_PORT,
)
from homeassistant.core import callback

from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)
from homeassistant.helpers.service_info.ssdp import SsdpServiceInfo

from .const import DOMAIN, CONF_PING_INTERVAL, CONF_MAX_VOLUME, CONF_POWER_CYCLE_INIT

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_MODEL): cv.string,
        vol.Optional(CONF_PORT, default=33335): cv.string,
    }
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional("max_volume"): vol.All(
            NumberSelector(
                NumberSelectorConfig(min=-100, max=100, mode=NumberSelectorMode.SLIDER)
            ),
            vol.Coerce(int),
        ),
        vol.Optional("ping_interval"): vol.All(
            NumberSelector(
                NumberSelectorConfig(min=0, max=600, mode=NumberSelectorMode.SLIDER)
            ),
            vol.Coerce(int),
        ),
        vol.Optional(CONF_POWER_CYCLE_INIT, default=True): BooleanSelector(),
    }
)


async def validate_auth(hass: core.HomeAssistant, data: dict) -> None:
    if "host" not in data.keys():
        data["host"] = ""

    if "name" not in data.keys():
        data["name"] = ""

    if "model" not in data.keys():
        data["model"] = ""

    if "port" not in data.keys():
        data["port"] = ""

    if (
        (len(data["host"]) < 3)
        or (len(data["name"]) < 1)
        or (len(data["model"]) < 1)
        or (len(data["port"]) < 1)
    ):
        # Manual entry requires host and name
        raise ValueError


class SonyAVRConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self) -> None:
        self._discovered: dict[str, Any] = {}

    async def async_step_user(self, user_input=None):
        """Invoked when a user initiates a flow via the user interface."""
        errors: Dict[str, str] = {}
        if user_input is not None:
            try:
                await validate_auth(self.hass, user_input)
            except ValueError:
                errors["base"] = "data"
            if not errors:
                # Input is valid, set data.
                self.data = user_input
                return self.async_create_entry(title="Sony AVR", data=self.data)

        # If there is no user input or there were errors, show the form again, including any errors that were found with the input.
        return self.async_show_form(
            step_id="user", data_schema=CONFIG_SCHEMA, errors=errors
        )

    async def async_step_ssdp(self, discovery_info: SsdpServiceInfo):
        """Handle a receiver discovered via SSDP."""
        upnp = discovery_info.upnp
        host = urlparse(discovery_info.ssdp_location or "").hostname
        udn = upnp.get("UDN")
        model = upnp.get("modelName", "")
        name = upnp.get("friendlyName") or model or "Sony AVR"

        if not host:
            return self.async_abort(reason="cannot_connect")

        # The UDN is stable per device, so use it to avoid duplicates and to
        # update the host if the receiver's IP changed.
        await self.async_set_unique_id(udn)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        self._discovered = {
            CONF_HOST: host,
            CONF_NAME: name,
            CONF_MODEL: model,
            CONF_PORT: "33335",
        }
        self.context["title_placeholders"] = {"name": name}
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input=None):
        """Confirm setup of an SSDP-discovered receiver."""
        if user_input is not None:
            self.data = self._discovered
            return self.async_create_entry(
                title=self._discovered[CONF_NAME], data=self.data
            )

        return self.async_show_form(
            step_id="confirm",
            description_placeholders={"name": self._discovered[CONF_NAME]},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self) -> None:
        """Initialize options flow."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA,
                {
                    CONF_MAX_VOLUME: self.config_entry.options.get(CONF_MAX_VOLUME),
                    CONF_PING_INTERVAL: self.config_entry.options.get(
                        CONF_PING_INTERVAL, 60
                    ),
                    CONF_POWER_CYCLE_INIT: self.config_entry.options.get(
                        CONF_POWER_CYCLE_INIT, True
                    ),
                },
            ),
        )
