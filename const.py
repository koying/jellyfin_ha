"""Constants for the jellyfin integration."""

DOMAIN = "jellyfin"
SIGNAL_STATE_UPDATED = "{}.updated".format(DOMAIN)

DEFAULT_SSL = False
DEFAULT_VERIFY_SSL = True
DEFAULT_PORT = 8096

CONN_TIMEOUT = 5.0

STATE_PLAYING = 'Playing'
STATE_PAUSED = 'Paused'
STATE_IDLE = 'Idle'
STATE_OFF = 'Off'