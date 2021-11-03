#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from homeassistant.const import ATTR_DOMAIN, ATTR_SERVICE_DATA, EVENT_CALL_SERVICE
from homeassistant.core import Context, Event, HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.template import area_entities, device_entities
from logging import getLogger
from typing import Any, Callable, Dict, List, Union


#-----------------------------------------------------------#
#       Constants
#-----------------------------------------------------------#

LOGGER = getLogger(__name__)


#-----------------------------------------------------------#
#       Target Resolve
#-----------------------------------------------------------#

async def async_resolve_target(hass: HomeAssistant, target: Union[str, List[str], Dict[str, Any]]) -> List[str]:
    """ Resolves the target argument of a service call and returns a list of entity ids. """
    if isinstance(target, str):
        return cv.ensure_list_csv(target)

    if isinstance(target, list):
        return target

    result = []
    target_areas = target.get("area_id", [])
    target_devices = target.get("device_id", [])
    target_entities = target.get("entity_id", [])

    for area in target_areas:
        result.extend([entity_id for entity_id in area_entities(hass, area) if entity_id not in result])

    for device in target_devices:
        result.extend([entity_id for entity_id in device_entities(hass, device) if entity_id not in result])

    result.extend([entity_id for entity_id in target_entities if entity_id not in result])
    return result


#-----------------------------------------------------------#
#       Track Manual Control
#-----------------------------------------------------------#

def track_manual_control(hass: HomeAssistant, entity_id: Union[str, List[str]], action: Callable[[List[str], Context], None], context_validator: Callable[[Context], bool]) -> Callable[[], None]:
    """ Tracks manual control of specific entities. """
    entity_ids = cv.ensure_list_csv(entity_id)
    domains = list(set([id.split(".")[0] for id in entity_ids]))

    async def on_service_call(event: Event) -> None:
        if not event.data.get(ATTR_DOMAIN, "") in domains:
            return

        service_data = event.data.get(ATTR_SERVICE_DATA, {})
        resolved_target = await async_resolve_target(hass, service_data)
        matched_entity_ids = [id for id in resolved_target if id in entity_ids]

        if len(matched_entity_ids) == 0:
            return

        if context_validator(event.context):
            return

        await action(matched_entity_ids, event.context)

    return hass.bus.async_listen(EVENT_CALL_SERVICE, on_service_call)