#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from config.custom_components.matjak_lighting.utils.contextualizer import Contextualizer
from homeassistant.const import CONF_ENTITY_ID, CONF_LIGHTS
from .const import (
    ATTR_ACTIVE_SCENES,
    ATTR_BRIGHTNESS,
    ATTR_COLOR_MODE,
    ATTR_COLOR_TEMP,
    ATTR_COLOR_VALUE,
    ATTR_DOMAIN,
    ATTR_ENTITY_ID,
    ATTR_PAUSED_SCENES,
    ATTR_SERVICE,
    ATTR_SERVICE_DATA,
    ATTR_TRANSITION,
    CONF_ID,
    CONF_ROTATE_COLORS,
    DOMAIN_FRIENDLY_NAME,
    EVENT_CALL_SERVICE,
    EVENT_HOMEASSISTANT_START,
    SCENE_DOMAIN,
    SERVICES,
    SERVICE_TURN_ON
)
from .utils.dynamic_scene import DynamicScene
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity_platform import EntityPlatform
from homeassistant.helpers.event import async_call_later
from logging import getLogger
from typing import Any, Callable, Dict, List


#-----------------------------------------------------------#
#       Constants
#-----------------------------------------------------------#

LOGGER = getLogger(__name__)
MIN_DELAY_TIME = 2


#-----------------------------------------------------------#
#       Entry Setup
#-----------------------------------------------------------#

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: Callable) -> bool:
    """ Sets up the sensor entry. """
    async_add_entities([ML_SensorEntity(config_entry)], update_before_add=True)
    register_services(entity_platform.current_platform.get())


#-----------------------------------------------------------#
#       Service Setup
#-----------------------------------------------------------#

def register_services(platform: EntityPlatform) -> None:
    """ Registers all the integration services. """
    for service, schema in SERVICES.items():
        platform.async_register_entity_service(service, schema, f"async_service_{service}")


#-----------------------------------------------------------#
#       ML_SensorEntity
#-----------------------------------------------------------#

class ML_SensorEntity(SensorEntity):
    #--------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self, config_entry: ConfigEntry):
        self._config_entry : ConfigEntry             = config_entry
        self._listeners    : List[str]               = []
        self._name         : str                     = f"{DOMAIN_FRIENDLY_NAME}"
        self._scenes       : Dict[str, DynamicScene] = {}


    #-----------------------------------------------------------------------------#
    #
    #       Entity Section
    #
    #-----------------------------------------------------------------------------#
    #       Properties
    #--------------------------------------------#

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        """ Gets a dict containing the entity attributes. """
        attributes = {
            ATTR_ACTIVE_SCENES: [scene_id for scene_id, scene in self._scenes.items() if scene.is_running],
            ATTR_PAUSED_SCENES: [scene_id for scene_id, scene in self._scenes.items() if not scene.is_running]
        }

        return attributes

    @property
    def icon(self) -> str:
        """ Gets the icon of the entity. """
        return "mdi:theme-light-dark"

    @property
    def name(self) -> str:
        """ Gets the name of the entity. """
        return self._name

    @property
    def native_unit_of_measurement(self) -> str:
        """ Gets the unit of measurement of the entity. """
        return ""

    @property
    def should_poll(self) -> bool:
        """ Gets a boolean indicating whether Home Assistant should automatically poll the entity. """
        return True

    @property
    def state(self) -> bool:
        """ Gets the entity state. """
        return len([scene_id for scene_id in self._scenes.keys()])

    @property
    def unique_id(self) -> str:
        """ Gets the unique ID of entity. """
        return self._name


    #--------------------------------------------#
    #       Event Handlers
    #--------------------------------------------#

    async def async_added_to_hass(self) -> None:
        """ Triggered when the entity has been added to Home Assistant. """
        async def async_initialize(*args: Any) -> None:
            self._listeners.append(self.hass.bus.async_listen(EVENT_CALL_SERVICE, self._async_on_scene_activated))

        if self.hass.is_running:
            return await async_initialize()
        else:
            return self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, async_initialize)

    async def async_will_remove_from_hass(self) -> None:
        """ Triggered when the entity is being removed from Home Assistant. """
        while self._listeners:
            self._listeners.pop()()

        for scene in self._scenes.values():
            scene.stop()


    #-----------------------------------------------------------------------------#
    #
    #       Logic Section
    #
    #-----------------------------------------------------------------------------#
    #       Services
    #--------------------------------------------#

    async def async_service_dynamic_scene_pause(self, **service_data: Any) -> None:
        """ Handles a call to the 'matjak_lighting.dynamic_scene_pause' service. """
        scene_id = service_data.get(CONF_ID)
        light_ids = service_data.get(CONF_LIGHTS)

        if scene_id not in self._scenes:
            return

        self._scenes[scene_id].pause(light_ids)
        self.async_schedule_update_ha_state(True)

    async def async_service_dynamic_scene_stop(self, **service_data: Any) -> None:
        """ Handles a call to the 'matjak_lighting.dynamic_scene_stop' service. """
        scene_id = service_data.get(CONF_ID)

        if scene_id not in self._scenes:
            return

        self._scenes.pop(scene_id).stop()


    #--------------------------------------------#
    #       Event Handlers
    #--------------------------------------------#

    async def _async_on_scene_activated(self, event: Event) -> None:
        """ Called when a call_service event has occurred. """
        domain = event.data.get(ATTR_DOMAIN, None)
        service = event.data.get(ATTR_SERVICE, None)
        service_data = event.data.get(ATTR_SERVICE_DATA, {})

        if domain != SCENE_DOMAIN or service != SERVICE_TURN_ON:
            return

        scene_id = service_data.get(ATTR_ENTITY_ID, None)
        scene_config = self._config_entry.options.get(scene_id, None)
        scene_delay = max(service_data.get(ATTR_TRANSITION, MIN_DELAY_TIME), MIN_DELAY_TIME)

        if scene_config is None:
            return

        if scene_id in self._scenes:
            self._scenes[scene_id].stop()

        self._scenes[scene_id] = DynamicSceneTest(self, self.hass, scene_id, scene_config)
        self._listeners(self._scenes[scene_id].add_update_listener(self._async_on_dynamic_scene_update))
        self._listeners.append(async_call_later(self.hass, scene_delay, lambda: self._scenes[scene_id].start()))

    async def _async_on_dynamic_scene_update(self, dynamic_scene: DynamicScene) -> None:
        """ Called when a dynamic scene is updated (stopped or started) """
        self.async_schedule_update_ha_state(True)