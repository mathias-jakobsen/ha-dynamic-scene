#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_BRIGHTNESS_PCT,
    ATTR_COLOR_MODE,
    ATTR_COLOR_TEMP,
    ATTR_HS_COLOR,
    ATTR_TRANSITION,
    DOMAIN as LIGHT_DOMAIN
)
from homeassistant.components.scene import DOMAIN as SCENE_DOMAIN
from homeassistant.const import (
    ATTR_DOMAIN,
    ATTR_ENTITY_ID,
    ATTR_SERVICE,
    ATTR_SERVICE_DATA,
    CONF_ENTITY_ID,
    CONF_ID,
    CONF_LIGHTS,
    CONF_SCENE,
    EVENT_CALL_SERVICE,
    EVENT_HOMEASSISTANT_START,
    SERVICE_TURN_ON
)
import voluptuous as vol
import homeassistant.helpers.config_validation as cv


#-----------------------------------------------------------#
#       Custom Component
#-----------------------------------------------------------#

DOMAIN = "matjak_lighting"
DOMAIN_FRIENDLY_NAME = "Matjak Lighting"
PLATFORMS = ["sensor"]


#-----------------------------------------------------------#
#       Attributes
#-----------------------------------------------------------#

ATTR_ACTIVE_SCENES = "active_scenes"
ATTR_BLOCK_ENTITIES = "block_entities"
ATTR_COLOR_VALUE = "color_value"
ATTR_DURATION = "duration"
ATTR_PAUSED_SCENES = "paused_scenes"


#-----------------------------------------------------------#
#       Configuration Keys
#-----------------------------------------------------------#

CONF_ENABLED = "enabled"
CONF_SCENES = "scenes"
CONF_SCENES_ENABLED = "scenes_enabled"
CONF_SCENE_SELECTED = "scene_selected"
CONF_ROTATE_COLORS = "rotate_colors"

#--- Config Flow -----
CONF_BLOCK_ENTITIES = "block_entities"
CONF_DURATION = "duration"
CONF_ENABLED = "enabled"
CONF_ROTATE_COLORS = "rotate_colors"
CONF_SCENE_ACTIVE = "scene_active"
CONF_TRANSITION = "transition"
CONF_VARIANCE_BRIGHTNESS_PCT = "brightness_pct_variance"
CONF_VARIANCE_COLOR_TEMP = "color_temp_variance"
CONF_VARIANCE_DURATION = "duration_variance"
CONF_VARIANCE_HUE = "hue_variance"
CONF_VARIANCE_SATURATION = "saturation_variance"
CONF_VARIANCE_TRANSITION = "transition_variance"


#-----------------------------------------------------------#
#       Services
#-----------------------------------------------------------#

SERVICES = {
    "dynamic_scene_pause": {
        vol.Required(CONF_ID): str,
        vol.Required(CONF_LIGHTS, default=[]): cv.entity_ids
    },
    "dynamic_scene_resume": {
        vol.Required(CONF_ID): str,
        vol.Required(CONF_LIGHTS, default=[]): cv.entity_ids
    },
    "dynamic_scene_stop": {
        vol.Required(CONF_ID): str
    }
}


