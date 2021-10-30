#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from ..const import LIGHT_DOMAIN
from homeassistant.const import ATTR_DOMAIN, ATTR_SERVICE, ATTR_SERVICE_DATA, CONF_ENTITY_ID, EVENT_CALL_SERVICE, EVENT_STATE_CHANGED, SERVICE_RELOAD
from homeassistant.core import Context, Event, HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_registry
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

    registry = await entity_registry.async_get_registry(hass)
    entity_ids = hass.states.async_entity_ids(LIGHT_DOMAIN)

    target_areas = target.get("area_id", [])
    target_devices = target.get("device_id", [])
    target_entities = target.get("entity_id", [])

    for entity_id in entity_ids:
        entity = registry.entities.get(entity_id, None)

        if entity:
            if entity.disabled:
                continue

            if entity.entity_id in target_entities:
                result.append(entity.entity_id)
                continue

            if entity.device_id is not None and entity.device_id in target_devices:
                result.append(entity.entity_id)
                continue

            if entity.area_id is not None and entity.area_id in target_areas:
                result.append(entity.entity_id)
        else:
            if entity_id in target_entities:
                result.append(entity_id)

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