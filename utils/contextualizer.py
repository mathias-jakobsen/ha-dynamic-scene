#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers.template import is_template_string, Template
from homeassistant.util import get_random_string
from typing import Any, Dict


#-----------------------------------------------------------#
#       Constants
#-----------------------------------------------------------#

CONTEXT_MAX_LENGTH = 36


#-----------------------------------------------------------#
#       Contextualizer
#-----------------------------------------------------------#

class Contextualizer:
    #--------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self, hass: HomeAssistant):
        self._context_unique_id = get_random_string(6)
        self._hass = hass


    #--------------------------------------------#
    #       Methods - Context
    #--------------------------------------------#

    def create_context(self) -> Context:
        """ Creates a new context. """
        return Context(id=f"{self._context_unique_id}{get_random_string(CONTEXT_MAX_LENGTH)}"[:CONTEXT_MAX_LENGTH])

    def is_context_internal(self, context: Context) -> bool:
        """ Determines whether the context is of internal origin (created by the class instance). """
        return context.id.startswith(self._context_unique_id)


    #--------------------------------------------#
    #       Methods - Actions
    #--------------------------------------------#

    def call_service(self, domain: str, service: str, **service_data: Any) -> Context:
        """ Calls a service. """
        context = self.create_context()
        parsed_service_data = self._parse_service_data(service_data)
        self._hass.async_create_task(self._hass.services.async_call(domain, service, { **parsed_service_data }, context=context))
        return context

    def fire_event(self, event_type: str, **event_data: Any) -> Context:
        """ Fires an event using the Home Assistant event bus. """
        context = self.create_context()
        self._hass.bus.async_fire(event_type, event_data, context=context)
        return context


    #--------------------------------------------#
    #       Private Methods
    #--------------------------------------------#

    def _parse_service_data(self, service_data: Dict[str, Any]) -> Dict[str, Any]:
        """ Parses the service data by rendering possible templates. """
        result = {}

        for key, value in service_data.items():
            if isinstance(value, str) and is_template_string(value):
                try:
                    template = Template(value, self.hass)
                    result[key] = template.async_render()
                except Exception as e:
                    self._logger.warn(f"Error parsing {key} in service_data {service_data}: Invalid template was given -> {value}.")
                    self._logger.warn(e)
            else:
                result[key] = value

        return result