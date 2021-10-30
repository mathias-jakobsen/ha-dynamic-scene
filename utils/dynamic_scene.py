from homeassistant.components.sensor import SensorEntity
from ..config_flow import CONF_DURATION, CONF_ROTATE_COLORS, CONF_VARIANCE_BRIGHTNESS_PCT, CONF_VARIANCE_COLOR_TEMP, CONF_VARIANCE_HUE, CONF_VARIANCE_SATURATION
from ..const import ATTR_BLOCK_ENTITIES, ATTR_COLOR_TEMP, ATTR_COLOR_VALUE, CONF_VARIANCE_DURATION, CONF_VARIANCE_TRANSITION
from .contextualizer import Contextualizer
from .events import track_manual_control
from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_COLOR_MODE, ATTR_TRANSITION, DOMAIN as LIGHT_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_ON
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers.event import async_call_later
from logging import getLogger
from typing import Any, Callable, Dict, List
import random


#-----------------------------------------------------------#
#       Constants
#-----------------------------------------------------------#

LOGGER = getLogger(__name__)


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

    def __init__(self, entity: SensorEntity, hass: HomeAssistant, scene_id: str, scene_config: Dict[str, Any], start_delay: float = None):
        self._contextualizer : Contextualizer              = Contextualizer(hass)
        self._entity         : SensorEntity                = entity
        self._hass           : HomeAssistant               = hass
        self._listeners      : List[Callable]              = []
        self._scene_config   : Dict[str, Any]              = scene_config
        self._scene_parts    : Dict[str, DynamicScenePart] = {}
        self._scene_id       : str                         = scene_id

        if start_delay is None or start_delay == 0:
            start_delay = 0.2

        self._listeners.append(async_call_later(self._hass, start_delay, lambda *args: self.start()))


    #--------------------------------------------#
    #       Properties
    #--------------------------------------------#

    @property
    def is_running(self) -> bool:
        """ Gets a boolean indicating whether the dynamic scene is currently running. """
        return len([part for part in self._scene_parts.values() if part.is_running])


    #--------------------------------------------#
    #       Methods
    #--------------------------------------------#

    def pause(self, entity_ids: List[str] = []) -> None:
        """ Pauses the dynamic scene (or parts of it) """
        if len(entity_ids) == 0:
            entity_ids = self._scene_parts.keys()

        for entity_id in entity_ids:
            self._scene_parts[entity_id].stop()

    def resume(self, entity_ids: List[str] = []) -> None:
        """ Resumes the dynamic scene (or parts of it) """
        if len(entity_ids) == 0:
            entity_ids = self._scene_parts.keys()

        for entity_id in entity_ids:
            self._scene_parts[entity_id].start()

    def start(self) -> None:
        """ Starts the dynamic scene. """
        scene_part_keys = self._scene_parts.keys()

        if len(scene_part_keys) > 0:
            return

        self._setup_listeners()
        self._setup_scene_parts()

        for scene_part in self._scene_parts.values():
            scene_part.start()

    def stop(self) -> None:
        """ Stops the dynamic scene. """
        for scene_part in self._scene_parts.values():
            scene_part.stop()

        while self._listeners:
            self._listeners.pop()()

        self._scene_parts = {}


    #--------------------------------------------#
    #       Private Methods
    #--------------------------------------------#

    def _setup_listeners(self) -> None:
        """ Sets up the event listeners. """
        self._listeners.append(track_manual_control(self._hass, self._scene_config[ATTR_BLOCK_ENTITIES], self._async_on_manual_control, self._contextualizer.is_context_internal))

    def _setup_scene_parts(self) -> None:
        """ Sets up the individual scene parts. """
        lights = self._hass.states.get(self._scene_id).attributes.get(ATTR_ENTITY_ID, [])
        lights_config = {}

        for entity_id in lights:
            state = self._hass.states.get(entity_id)

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

        if self._scene_config.get(CONF_ROTATE_COLORS):
            def transform_configs(configs: Dict[str, Any], entity_id: str) -> object:
                result = [next((config for config_id, config in configs.items() if config_id == entity_id))]

                for config in [config for config_id, config in configs.items() if config_id != entity_id]:
                    result.append({**config, ATTR_BRIGHTNESS: result[0][ATTR_BRIGHTNESS]})

                return result

            color_configs = { entity_id: light_config[0] for entity_id, light_config in lights_config.items() }
            lights_config = { entity_id: transform_configs(color_configs, entity_id) for entity_id in lights_config.keys() }

        self._scene_parts = { entity_id: DynamicScenePart(self._hass, self._contextualizer, entity_id, self._scene_config, lights_config[entity_id]) for entity_id in lights_config.keys() }


    #--------------------------------------------#
    #       Event Handlers
    #--------------------------------------------#

    async def _async_on_manual_control(self, entity_ids: List[str], context: Context) -> None:
        for entity_id, scene_part in self._scene_parts.items():
            if entity_id in entity_ids and scene_part.is_running:
                self._entity.stop_scene(self._scene_id)
                LOGGER.error("Manual control detected.")
                return
