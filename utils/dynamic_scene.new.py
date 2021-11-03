#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from __future__ import annotations
from . import track_manual_control
from .contextualizer import Contextualizer
from ..const import ATTR_COLOR_VALUE, CONF_ROTATE_COLORS
from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_COLOR_MODE, ATTR_COLOR_TEMP
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from typing import Any, Callable, Dict, List


#-----------------------------------------------------------#
#       DynamicScenePart
#-----------------------------------------------------------#

class DynamicScenePart:
    pass



#-----------------------------------------------------------#
#       DynamicScene
#-----------------------------------------------------------#

class DynamicScene:
    #--------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self, hass: HomeAssistant, scene_id: str, scene_config: Dict[str, Any]):
        self._contextualizer : Contextualizer              = Contextualizer(hass)
        self._hass           : HomeAssistant               = hass
        self._listeners      : List[Callable]              = []
        self._scene_parts    : Dict[str, DynamicScenePart] = self._setup_scene_parts(hass, scene_id, scene_config)


    #--------------------------------------------#
    #       Properties
    #--------------------------------------------#

    @property
    def is_running(self) -> bool:
        """ Gets a boolean indicating whether the dynamic scene is currently running. """
        return len([part for part in self._scene_parts.values() if part.is_running]) > 0


    #--------------------------------------------#
    #       Methods -> Listeners
    #--------------------------------------------#

    def add_update_listener(self, listener: Callable[[DynamicScene], None]) -> Callable:
        """ Adds an update listener. """
        def remove_listener() -> None:
            self._listeners.remove(listener)

        self._listeners.append(listener)
        return remove_listener


    #--------------------------------------------#
    #       Methods -> Controls
    #--------------------------------------------#

    def start(self, entity_ids: List[str] = None) -> None:
        """ Starts the dynamic scene. """
        is_running = self.is_running

        if entity_ids is None:
            entity_ids = self._scene_parts.keys()

        for entity_id in entity_ids:
            self._scene_parts[entity_id].start()

        if is_running != self.is_running:
            self._fire_event()

    def stop(self, entity_ids: List[str] = None) -> None:
        """ Stops the dynamic scene. """
        is_running = self.is_running

        if entity_ids is None:
            entity_ids = self._scene_parts.keys()

        for entity_id in entity_ids:
            self._scene_parts[entity_id].stop()

        if is_running != self.is_running:
            self._fire_event()


    #--------------------------------------------#
    #       Private Methods
    #--------------------------------------------#

    def _fire_event(self) -> None:
        """ Fires an event. """
        for listener in self._listeners:
            listener(self)

    def _setup_scene_parts(self, hass: HomeAssistant, scene_id: str, scene_config: Dict[str, Any]) -> Dict[str, DynamicScenePart]:
        """ Sets up the individual scene parts. """
        lights = hass.states.get(scene_id).attributes.get(ATTR_ENTITY_ID, [])
        lights_config = {}

        for entity_id in lights:
            state = hass.states.get(entity_id)

            if state is None:
                continue

            color_mode = state.attributes.get(ATTR_COLOR_MODE, None)

            if color_mode is None:
                continue

            if color_mode != ATTR_COLOR_TEMP:
                color_mode = f"{color_mode}_color"

            brightness = state.attributes.get(ATTR_BRIGHTNESS)
            color_value = state.attributes.get(color_mode)

            lights_config.update({ entity_id: [{ ATTR_BRIGHTNESS: brightness, ATTR_COLOR_MODE: color_mode, ATTR_COLOR_VALUE: color_value }] })

        if scene_config.get(CONF_ROTATE_COLORS):
            def transform_configs(configs: Dict[str, Any], entity_id: str) -> object:
                result = [next((config for config_id, config in configs.items() if config_id == entity_id))]

                for config in [config for config_id, config in configs.items() if config_id != entity_id]:
                    result.append({**config, ATTR_BRIGHTNESS: result[0][ATTR_BRIGHTNESS]})

                return result

            color_configs = { entity_id: light_config[0] for entity_id, light_config in lights_config.items() }
            lights_config = { entity_id: transform_configs(color_configs, entity_id) for entity_id in lights_config.keys() }

        return { entity_id: DynamicScenePart(self._hass, self._contextualizer, entity_id, scene_config, lights_config[entity_id]) for entity_id in lights_config.keys() }
