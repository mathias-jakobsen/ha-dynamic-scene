#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from __future__ import annotations
from . import track_manual_control
from .contextualizer import Contextualizer
from ..const import (
    ATTR_BLOCK_ENTITIES,
    ATTR_BRIGHTNESS,
    ATTR_COLOR_MODE,
    ATTR_COLOR_TEMP,
    ATTR_COLOR_VALUE,
    ATTR_ENTITY_ID,
    ATTR_TRANSITION,
    CONF_DURATION,
    CONF_ROTATE_COLORS,
    CONF_VARIANCE_BRIGHTNESS_PCT,
    CONF_VARIANCE_COLOR_TEMP,
    CONF_VARIANCE_DURATION,
    CONF_VARIANCE_HUE,
    CONF_VARIANCE_SATURATION,
    CONF_VARIANCE_TRANSITION,
    LIGHT_DOMAIN,
    SERVICE_TURN_ON
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later
from typing import Any, Callable, Dict, List
import random


#-----------------------------------------------------------#
#       DynamicScenePart
#-----------------------------------------------------------#

class DynamicScenePart:
    #--------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self, hass: HomeAssistant, contextualizer: Contextualizer, entity_id: str, scene_config: Dict[str, Any], light_config: List[Dict[str, Any]]):
        self._contextualizer = contextualizer
        self._blocked_indexes = []
        self._entity_id = entity_id
        self._hass = hass
        self._light_config = light_config
        self._listeners = []
        self._is_running = False
        self._scene_config = scene_config


    #--------------------------------------------#
    #       Properties
    #--------------------------------------------#

    @property
    def is_running(self) -> bool:
        """ Gets a boolean indicating whether the dynamic scene part is currently running. """
        return self._is_running


    #--------------------------------------------#
    #       Methods
    #--------------------------------------------#

    def start(self) -> None:
        """ Starts the dynamic scene part. """
        if self._is_running:
            return

        self._is_running = True
        self._update()

    def stop(self) -> None:
        """ Stops the dynamic scene part. """
        if not self._is_running:
            return

        while self._listeners:
            self._listeners.pop()()

        self._is_running = False


    #--------------------------------------------#
    #       Private Methods
    #--------------------------------------------#

    def _get_attribute(self, value: float, variance: float, min_value: float, max_value: float, modulo: float = None) -> float:
        """ Gets a newly calculated attribute value. """
        new_value = random.uniform(value - variance, value + variance)

        if modulo:
            new_value = new_value % modulo

        new_value = min(max_value, max(min_value, new_value))
        return round(new_value, None)

    def _update(self, *args: Any) -> None:
        """ Updates the color of the light. """
        current_index = random.randint(0, len(self._light_config) - 1)

        if len(self._light_config) == 1:
            while current_index in self._blocked_indexes:
                current_index = random.randint(0, len(self._light_config) - 1)

            self._blocked_indexes.append(current_index)

            if len(self._blocked_indexes) == len(self._light_config):
                self._blocked_indexes = []

        current_light_config = self._light_config[current_index]

        color_mode = current_light_config.get(ATTR_COLOR_MODE)
        color_value = current_light_config.get(ATTR_COLOR_VALUE)

        if color_mode == ATTR_COLOR_TEMP:
            color_temp_variance = self._scene_config.get(CONF_VARIANCE_COLOR_TEMP)
            color_value = self._get_attribute(color_value, color_temp_variance, 153, 500)
        else:
            hue, saturation = color_value

            hue_variance = self._scene_config.get(CONF_VARIANCE_HUE)
            saturation_variance = self._scene_config.get(CONF_VARIANCE_SATURATION)

            hue = self._get_attribute(hue, hue_variance, 0, 360, 360)
            saturation = self._get_attribute(saturation, saturation_variance, 0, 100)

            color_value = [hue, saturation]

        brightness_pct_variance = self._scene_config.get(CONF_VARIANCE_BRIGHTNESS_PCT)
        brightness = self._get_attribute(current_light_config.get(ATTR_BRIGHTNESS), 255 * brightness_pct_variance / 100, 0, 255)

        transition_variance = self._scene_config.get(CONF_VARIANCE_TRANSITION)
        transition = self._get_attribute(self._scene_config.get(ATTR_TRANSITION), transition_variance, 2, 100)

        duration_variance = self._scene_config.get(CONF_VARIANCE_DURATION)
        duration = self._get_attribute(self._scene_config.get(CONF_DURATION), duration_variance, 2, 100)

        service_data = { ATTR_ENTITY_ID: self._entity_id, ATTR_BRIGHTNESS: brightness, color_mode: color_value, ATTR_TRANSITION: transition }
        self._contextualizer.call_service(LIGHT_DOMAIN, SERVICE_TURN_ON, **service_data)

        self._listeners.append(async_call_later(self._hass, duration + transition, self._update))


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
