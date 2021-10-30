#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from __future__ import annotations
from .const import (
    CONF_BLOCK_ENTITIES,
    CONF_DURATION,
    CONF_ENABLED,
    CONF_ROTATE_COLORS,
    CONF_SCENE_ACTIVE,
    CONF_SCENE_SELECTED,
    CONF_SCENES_ENABLED,
    CONF_TRANSITION,
    CONF_VARIANCE_BRIGHTNESS_PCT,
    CONF_VARIANCE_COLOR_TEMP,
    CONF_VARIANCE_DURATION,
    CONF_VARIANCE_HUE,
    CONF_VARIANCE_SATURATION,
    CONF_VARIANCE_TRANSITION,
    DOMAIN,
    SCENE_DOMAIN
)
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from typing import Any, Dict, Union
import voluptuous as vol


#-----------------------------------------------------------#
#       Constants
#-----------------------------------------------------------#

# ------ Abort Reasons ---------------
ABORT_REASON_ALREADY_CONFIGURED = "already_configured"

# ------ Steps ---------------
STEP_INIT = "init"
STEP_SCENE = "scene"
STEP_USER = "user"


#-----------------------------------------------------------#
#       Steps
#-----------------------------------------------------------#

class MD_Steps:
    @staticmethod
    def init(hass: HomeAssistant, data: Dict[str, Any] = {}) -> vol.Schema:
        return vol.Schema({})

    @staticmethod
    def options_init(hass: HomeAssistant, data: Dict[str, Any] = {}) -> vol.Schema:
        scenes_enabled = list(data.keys())
        scenes = [None] + hass.states.async_entity_ids(SCENE_DOMAIN)

        return vol.Schema({
            vol.Required(CONF_SCENES_ENABLED, default=scenes_enabled): cv.multi_select(scenes_enabled),
            vol.Optional(CONF_SCENE_SELECTED, default=scenes[0]): vol.In(scenes)
        })

    @staticmethod
    def options_scene(hass: HomeAssistant, scene_id: str, data: Dict[str, Any] = {}) -> vol.Schema:
        scene_data = data.get(scene_id, {})
        scenes_enabled = list(data.keys())
        scenes = [None] + hass.states.async_entity_ids(SCENE_DOMAIN)
        lights = hass.states.async_entity_ids(LIGHT_DOMAIN)

        return vol.Schema({
            vol.Required(CONF_SCENE_ACTIVE, default=scene_id): scene_id,
            vol.Required(CONF_ENABLED, default=(scene_id in scenes_enabled)): bool,
            vol.Required(CONF_TRANSITION, default=scene_data.get(CONF_TRANSITION, 2)): vol.All(int, vol.Range(min=0, max_included=False)),
            vol.Required(CONF_VARIANCE_TRANSITION, default=scene_data.get(CONF_VARIANCE_TRANSITION, 0)): vol.All(int, vol.Range(min=0, max=100)),
            vol.Required(CONF_DURATION, default=scene_data.get(CONF_DURATION, 5)): vol.All(int, vol.Range(min=0, max_included=False)),
            vol.Required(CONF_VARIANCE_DURATION, default=scene_data.get(CONF_VARIANCE_DURATION, 0)): vol.All(int, vol.Range(min=0, max=100)),
            vol.Required(CONF_ROTATE_COLORS, default=scene_data.get(CONF_ROTATE_COLORS, False)): bool,
            vol.Required(CONF_VARIANCE_COLOR_TEMP, default=scene_data.get(CONF_VARIANCE_COLOR_TEMP, 40)): vol.All(int, vol.Range(min=0, max=300)),
            vol.Required(CONF_VARIANCE_HUE, default=scene_data.get(CONF_VARIANCE_HUE, 15)): vol.All(int, vol.Range(min=0, max=360)),
            vol.Required(CONF_VARIANCE_SATURATION, default=scene_data.get(CONF_VARIANCE_SATURATION, 5)): vol.All(int, vol.Range(min=0, max=100)),
            vol.Required(CONF_VARIANCE_BRIGHTNESS_PCT, default=scene_data.get(CONF_VARIANCE_BRIGHTNESS_PCT, 5)): vol.All(int, vol.Range(min=0, max=100)),
            vol.Required(CONF_BLOCK_ENTITIES, default=scene_data.get(CONF_BLOCK_ENTITIES, [])): cv.multi_select(lights),
            vol.Optional(CONF_SCENE_SELECTED, default=scenes[0]): vol.In(scenes)
        })


#-----------------------------------------------------------#
#       Config Flow
#-----------------------------------------------------------#

class Matjak_ConfigFlow(ConfigFlow, domain=DOMAIN):
    #--------------------------------------------#
    #       Static Properties
    #--------------------------------------------#

    VERSION = 1


    #--------------------------------------------#
    #       Static Methods
    #--------------------------------------------#

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> Matjak_OptionsFlow:
        return Matjak_OptionsFlow(config_entry)


    #--------------------------------------------#
    #       Methods
    #--------------------------------------------#

    async def async_step_user(self, user_input: Dict[str, Any] = None) -> FlowResult:
        if self._async_current_entries():
            self.async_abort(reason=ABORT_REASON_ALREADY_CONFIGURED)

        if user_input is not None:
            await self.async_set_unique_id(f"{DOMAIN}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=DOMAIN, data=user_input)

        schema = MD_Steps.init(self.hass)
        return self.async_show_form(step_id=STEP_USER, data_schema=schema)


#-----------------------------------------------------------#
#       Options Flow
#-----------------------------------------------------------#

class Matjak_OptionsFlow(OptionsFlow):
    #--------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self, config_entry: ConfigEntry):
        self._config_entry = config_entry
        self._data = { **config_entry.data, **config_entry.options }
        self._scene_selected = None


    #--------------------------------------------#
    #       Steps - Init
    #--------------------------------------------#

    async def async_step_init(self, user_input: Union[Dict[str, Any], None] = None) -> Dict[str, Any]:
        if user_input is not None:
            self._data = { scene_id: scene_config for scene_id, scene_config in self._data.items() if scene_id in user_input[CONF_SCENES_ENABLED] }
            self._scene_selected = user_input.get(CONF_SCENE_SELECTED)

            if self._scene_selected is None:
                return self.async_create_entry(title=DOMAIN, data=self._data)

            return await self.async_step_scene()

        schema = MD_Steps.options_init(self.hass, self._data)
        return self.async_show_form(step_id=STEP_INIT, data_schema=schema)

    async def async_step_scene(self, user_input: Union[Dict[str, Any], None] = None) -> Dict[str, Any]:
        if user_input is not None:
            scene_id = user_input.pop(CONF_SCENE_ACTIVE)
            enabled = user_input.pop(CONF_ENABLED)

            if not enabled:
                self._data.pop(self._scene_selected, None)
            else:
                old_data = self._data.get(scene_id, {})
                self._data[scene_id] = { **old_data, **user_input }

            self._scene_selected = user_input.get(CONF_SCENE_SELECTED)

            if self._scene_selected is None:
                return self.async_create_entry(title=DOMAIN, data=self._data)

        schema = MD_Steps.options_scene(self.hass, self._scene_selected, self._data)
        return self.async_show_form(step_id=STEP_SCENE, data_schema=schema)