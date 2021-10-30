#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from .const import DOMAIN, PLATFORMS
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import IntegrationError
from logging import getLogger
from typing import Any, Dict


#-----------------------------------------------------------#
#       Constants
#-----------------------------------------------------------#

LOGGER = getLogger(__package__)
UNDO_LISTENERS = "undo_listeners"


#-----------------------------------------------------------#
#       Setup
#-----------------------------------------------------------#


async def async_setup(hass: HomeAssistant, config: Dict[Any, str]) -> bool:
    if DOMAIN in config:
        raise IntegrationError(
            f"{DOMAIN} can only be loaded from the UI. Remove {DOMAIN} from your YAML configuration."
        )

    return True

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    data = hass.data.setdefault(DOMAIN, {})

    data[config_entry.entry_id] = {UNDO_LISTENERS: []}
    data[config_entry.entry_id][UNDO_LISTENERS].append(
        config_entry.add_update_listener(async_update_options)
    )

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, platform)
        )

    return True

async def async_update_options(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(config_entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    unload_ok = all(
        [
            await hass.config_entries.async_forward_entry_unload(config_entry, platform)
            for platform in PLATFORMS
        ]
    )

    data = hass.data[DOMAIN]

    while data[config_entry.entry_id][UNDO_LISTENERS]:
        data[config_entry.entry_id][UNDO_LISTENERS].pop()()

    if unload_ok:
        data.pop(config_entry.entry_id)

    return unload_ok

async def async_remove_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    pass
