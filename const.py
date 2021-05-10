"""Constants for the jellyfin integration."""

DOMAIN = "jellyfin"
SIGNAL_STATE_UPDATED = "{}.updated".format(DOMAIN)

SERVICE_SCAN = "trigger_scan"
SERVICE_YAMC_SETPAGE = "yamc_setpage"
SERVICE_BROWSE = "browse"
SERVICE_DELETE = "delete"

ATTR_PAGE = 'page'

USER_APP_NAME = "Home Assistant"
CLIENT_VERSION = "1.0"

DEFAULT_SSL = False
DEFAULT_VERIFY_SSL = True
DEFAULT_PORT = 8096

CONN_TIMEOUT = 5.0

STATE_PLAYING = 'Playing'
STATE_PAUSED = 'Paused'
STATE_IDLE = 'Idle'
STATE_OFF = 'Off'

CONF_GENERATE_UPCOMING = "generate_upcoming"
CONF_GENERATE_YAMC = "generate_yamc"

YAMC_PAGE_SIZE=7