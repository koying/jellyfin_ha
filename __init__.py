"""The jellyfin component."""
import logging
import time
import re
import traceback
import collections.abc
from typing import Mapping, MutableMapping, Optional, Sequence, Iterable, List, Tuple

import voluptuous as vol

from homeassistant.exceptions import ConfigEntryNotReady
from jellyfin_apiclient_python import JellyfinClient
from jellyfin_apiclient_python.connection_manager import CONNECTION_STATE

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (  # pylint: disable=import-error
    ATTR_ENTITY_ID,
    CONF_URL,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_VERIFY_SSL,
    CONF_CLIENT_ID,
    EVENT_HOMEASSISTANT_STOP,
)
import homeassistant.helpers.config_validation as cv  # pylint: disable=import-error

from homeassistant.helpers.dispatcher import (  # pylint: disable=import-error
    async_dispatcher_send,
)

from .const import (
    DOMAIN,
    USER_APP_NAME,
    CLIENT_VERSION,
    SIGNAL_STATE_UPDATED,
    SERVICE_SCAN,
    STATE_OFF,
    STATE_IDLE,
    STATE_PAUSED,
    STATE_PLAYING,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "media_player"]
UPDATE_UNLISTENER = None

PATH_REGEX = re.compile("^(https?://)?([^/:]+)(:[0-9]+)?(/.*)?$")

SCAN_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
    }
)

def autolog(message):
    "Automatically log the current function details."
    import inspect
    # Get the previous frame in the stack, otherwise it would
    # be this function!!!
    func = inspect.currentframe().f_back.f_code
    # Dump the message + the name of this function to the log.
    _LOGGER.debug("%s: %s in %s:%i" % (
        message, 
        func.co_name, 
        func.co_filename, 
        func.co_firstlineno
    ))

async def async_setup(hass: HomeAssistant, config: dict):
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    global UPDATE_UNLISTENER
    if UPDATE_UNLISTENER:
        UPDATE_UNLISTENER()

    if not config_entry.unique_id:
        hass.config_entries.async_update_entry(
            config_entry, unique_id=config_entry.title
        )

    config = {}
    for key, value in config_entry.data.items():
        config[key] = value
    for key, value in config_entry.options.items():
        config[key] = value
    if config_entry.options:
        hass.config_entries.async_update_entry(config_entry, data=config, options={})

    UPDATE_UNLISTENER = config_entry.add_update_listener(_update_listener)

    hass.data[DOMAIN][config.get(CONF_URL)] = {}
    _jelly = JellyfinClientManager(hass, config)
    try:
        await _jelly.connect()
        hass.data[DOMAIN][config.get(CONF_URL)]["manager"] = _jelly
    except:
        _LOGGER.error("Cannot connect to Jellyfin server.")
        raise

    async def service_trigger_scan(service):
        entity_id = service.data.get(ATTR_ENTITY_ID)

        for sensor in hass.data[DOMAIN][config.get(CONF_URL)]["sensor"]["entities"]:
            if sensor.entity_id == entity_id:
                await sensor.async_trigger_scan()

    hass.services.async_register(
        DOMAIN,
        SERVICE_SCAN,
        service_trigger_scan,
        schema=SCAN_SERVICE_SCHEMA,
    )

    for component in PLATFORMS:
        hass.data[DOMAIN][config.get(CONF_URL)][component] = {}
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, component)
        )

    async_dispatcher_send(hass, SIGNAL_STATE_UPDATED)

    async def stop_jellyfin(event):
        """Stop Jellyfin connection."""
        await _jelly.stop()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_jellyfin)
    
    await _jelly.start()

    return True


async def _update_listener(hass, config_entry):
    """Update listener."""
    await hass.config_entries.async_reload(config_entry.entry_id)


class JellyfinDevice(object):
    """ Represents properties of an Jellyfin Device. """

    def __init__(self, session, jf_manager):
        """Initialize Emby device object."""
        self.jf_manager = jf_manager
        self.is_active = True
        self.update_data(session)

    def update_data(self, session):
        """ Update session object. """
        self.session = session

    def set_active(self, active):
        """ Mark device as on/off. """
        self.is_active = active

    @property
    def session_raw(self):
        """ Return raw session data. """
        return self.session

    @property
    def session_id(self):
        """ Return current session Id. """
        try:
            return self.session['Id']
        except KeyError:
            return None

    @property
    def unique_id(self):
        """ Return device id."""
        try:
            return self.session['DeviceId']
        except KeyError:
            return None

    @property
    def name(self):
        """ Return device name."""
        try:
            return self.session['DeviceName']
        except KeyError:
            return None

    @property
    def client(self):
        """ Return client name. """
        try:
            return self.session['Client']
        except KeyError:
            return None

    @property
    def username(self):
        """ Return device name."""
        try:
            return self.session['UserName']
        except KeyError:
            return None

    @property
    def media_title(self):
        """ Return title currently playing."""
        try:
            return self.session['NowPlayingItem']['Name']
        except KeyError:
            return None

    @property
    def media_season(self):
        """Season of curent playing media (TV Show only)."""
        try:
            return self.session['NowPlayingItem']['ParentIndexNumber']
        except KeyError:
            return None

    @property
    def media_series_title(self):
        """The title of the series of current playing media (TV Show only)."""
        try:
            return self.session['NowPlayingItem']['SeriesName']
        except KeyError:
            return None

    @property
    def media_episode(self):
        """Episode of current playing media (TV Show only)."""
        try:
            return self.session['NowPlayingItem']['IndexNumber']
        except KeyError:
            return None

    @property
    def media_album_name(self):
        """Album name of current playing media (Music track only)."""
        try:
            return self.session['NowPlayingItem']['Album']
        except KeyError:
            return None

    @property
    def media_artist(self):
        """Artist of current playing media (Music track only)."""
        try:
            artists = self.session['NowPlayingItem']['Artists']
            if len(artists) > 1:
                return artists[0]
            else:
                return artists
        except KeyError:
            return None

    @property
    def media_album_artist(self):
        """Album artist of current playing media (Music track only)."""
        try:
            return self.session['NowPlayingItem']['AlbumArtist']
        except KeyError:
            return None

    @property
    def media_id(self):
        """ Return title currently playing."""
        try:
            return self.session['NowPlayingItem']['Id']
        except KeyError:
            return None

    @property
    def media_type(self):
        """ Return type currently playing."""
        try:
            return self.session['NowPlayingItem']['Type']
        except KeyError:
            return None

    @property
    def media_image_url(self):
        """Image url of current playing media."""
        if self.is_nowplaying:
            try:
                image_id = self.session['NowPlayingItem']['ImageTags']['Thumb']
                image_type = 'Thumb'
            except KeyError:
                try:
                    image_id = self.session[
                        'NowPlayingItem']['ImageTags']['Primary']
                    image_type = 'Primary'
                except KeyError:
                    return None
            url = self.jf_manager.api.artwork(self.media_id, image_type, 500)
            return url
        else:
            return None

    @property
    def media_position(self):
        """ Return position currently playing."""
        try:
            return int(self.session['PlayState']['PositionTicks']) / 10000000
        except KeyError:
            return None

    @property
    def media_runtime(self):
        """ Return total runtime length."""
        try:
            return int(
                self.session['NowPlayingItem']['RunTimeTicks']) / 10000000
        except KeyError:
            return None

    @property
    def media_percent_played(self):
        """ Return media percent played. """
        try:
            return (self.media_position / self.media_runtime) * 100
        except TypeError:
            return None

    @property
    def state(self):
        """ Return current playstate of the device. """
        if self.is_active:
            if 'NowPlayingItem' in self.session:
                if self.session['PlayState']['IsPaused']:
                    return STATE_PAUSED
                else:
                    return STATE_PLAYING
            else:
                return STATE_IDLE
        else:
            return STATE_OFF

    @property
    def is_nowplaying(self):
        """ Return true if an item is currently active. """
        if self.state == 'Idle' or self.state == 'Off':
            return False
        else:
            return True

    @property
    def supports_remote_control(self):
        """ Return remote control status. """
        return self.session['SupportsRemoteControl']

    async def get_item(self, id):
        return await self.jf_manager.get_item(id)

    async def get_items(self, query=None):
        return await self.jf_manager.get_items(query)

    async def get_artwork(self, media_id) -> Tuple[Optional[str], Optional[str]]:
        return await self.jf_manager.get_artwork(media_id)

    async def get_artwork_url(self, media_id) -> str:
        return await self.jf_manager.get_artwork_url(media_id)

    async def set_playstate(self, state, pos=0):
        """ Send media commands to server. """
        params = {}
        if state == 'Seek':
            params['SeekPositionTicks'] = int(pos * 10000000)
            params['static'] = 'true'

        await self.jf_manager.set_playstate(self.session_id, state, params)

    def media_play(self):
        """ Send play command to device. """
        return self.set_playstate('Unpause')

    def media_pause(self):
        """ Send pause command to device. """
        return self.set_playstate('Pause')

    def media_stop(self):
        """ Send stop command to device. """
        return self.set_playstate('Stop')

    def media_next(self):
        """ Send next track command to device. """
        return self.set_playstate('NextTrack')

    def media_previous(self):
        """ Send previous track command to device. """
        return self.set_playstate('PreviousTrack')

    def media_seek(self, position):
        """ Send seek command to device. """
        return self.set_playstate('Seek', position)

    async def play_media(self, media_id):
        await self.jf_manager.play_media(self.session_id, media_id)

class JellyfinClientManager(object):
    def __init__(self, hass: HomeAssistant, config_entry):
        self.hass = hass
        self.callback = lambda client, event_name, data: None
        self.jf_client: JellyfinClient = None
        self.is_stopping = True
        self._event_loop = hass.loop
        
        self.host = config_entry[CONF_URL]
        self._info = None

        self.config_entry = config_entry
        self.server_url = ""

        self._sessions = None
        self._devices: Mapping[str, JellyfinDevice] = {}

        # Callbacks
        self._new_devices_callbacks = []
        self._stale_devices_callbacks = []
        self._update_callbacks = []

    @staticmethod
    def expo(max_value = None):
        n = 0
        while True:
            a = 2 ** n
            if max_value is None or a < max_value:
                yield a
                n += 1
            else:
                yield max_value

    @staticmethod
    def clean_none_dict_values(obj):
        """
        Recursively remove keys with a value of None
        """
        if not isinstance(obj, collections.abc.Iterable) or isinstance(obj, str):
            return obj

        queue = [obj]

        while queue:
            item = queue.pop()

            if isinstance(item, collections.abc.Mapping):
                mutable = isinstance(item, collections.abc.MutableMapping)
                remove = []

                for key, value in item.items():
                    if value is None and mutable:
                        remove.append(key)

                    elif isinstance(value, str):
                        continue

                    elif isinstance(value, collections.abc.Iterable):
                        queue.append(value)

                if mutable:
                    # Remove keys with None value
                    for key in remove:
                        item.pop(key)

            elif isinstance(item, collections.abc.Iterable):
                for value in item:
                    if value is None or isinstance(value, str):
                        continue
                    elif isinstance(value, collections.abc.Iterable):
                        queue.append(value)

        return obj

    async def connect(self):
        autolog(">>>")

        is_logged_in = await self.hass.async_add_executor_job(self.login)

        if is_logged_in:
            _LOGGER.info("Successfully added server.")
        else:
            raise ConfigEntryNotReady

    @staticmethod
    def client_factory(config_entry):
        client = JellyfinClient(allow_multiple_clients=True)
        client.config.data["app.default"] = True
        client.config.app(
            USER_APP_NAME, CLIENT_VERSION, USER_APP_NAME, config_entry[CONF_CLIENT_ID]
        )
        client.config.data["auth.ssl"] = config_entry[CONF_VERIFY_SSL]
        return client

    def login(self):
        autolog(">>>")

        self.server_url = self.config_entry[CONF_URL]

        if self.server_url.endswith("/"):
            self.server_url = self.server_url[:-1]

        protocol, host, port, path = PATH_REGEX.match(self.server_url).groups()

        if not protocol:
            _LOGGER.warning("Adding http:// because it was not provided.")
            protocol = "http://"

        if protocol == "http://" and not port:
            _LOGGER.warning("Adding port 8096 for insecure local http connection.")
            _LOGGER.warning(
                "If you want to connect to standard http port 80, use :80 in the url."
            )
            port = ":8096"

        if protocol == "https://" and not port:
            port = ":443"

        self.server_url = "".join(filter(bool, (protocol, host, port, path)))

        self.jf_client = self.client_factory(self.config_entry)
        self.jf_client.auth.connect_to_address(self.server_url)
        result = self.jf_client.auth.login(self.server_url, self.config_entry[CONF_USERNAME], self.config_entry[CONF_PASSWORD])
        if "AccessToken" not in result:
            return False

        credentials = self.jf_client.auth.credentials.get_credentials()
        self.jf_client.authenticate(credentials)
        return True

    async def start(self):
        autolog(">>>")

        def event(event_name, data):
            _LOGGER.debug("Event: %s", event_name)
            if event_name == "WebSocketConnect":
                self.jf_client.wsc.send("SessionsStart", "0,1500")
            elif event_name == "WebSocketDisconnect":
                timeout_gen = self.expo(100)
                while not self.is_stopping:
                    timeout = next(timeout_gen)
                    _LOGGER.warning(
                        "No connection to server. Next try in {0} second(s)".format(
                            timeout
                        )
                    )
                    self.jf_client.stop()
                    time.sleep(timeout)
                    if self.login():
                        break
            elif event_name == "Sessions":
                self._sessions = self.clean_none_dict_values(data)["value"]
                self.update_device_list()
            else:
                self.callback(self.jf_client, event_name, data)

        self.jf_client.callback = event
        self.jf_client.callback_ws = event

        await self.hass.async_add_executor_job(self.jf_client.start, True)
        self.is_stopping = False

        self._info = await self.hass.async_add_executor_job(self.jf_client.jellyfin._get, "System/Info")
        self._sessions = self.clean_none_dict_values(await self.hass.async_add_executor_job(self.jf_client.jellyfin.get_sessions))

    async def stop(self):
        autolog(">>>")

        await self.hass.async_add_executor_job(self.jf_client.stop)
        self.is_stopping = True

    def update_device_list(self):
        """ Update device list. """
        autolog(">>>")
        # _LOGGER.debug("sessions: %s", str(sessions))
        if self._sessions is None:
            _LOGGER.error('Error updating Jellyfin devices.')
            return

        try:
            new_devices = []
            active_devices = []
            dev_update = False
            for device in self._sessions:
                # _LOGGER.debug("device: %s", str(device))
                dev_name = '{}.{}'.format(device['DeviceId'], device['Client'])

                try:
                    _LOGGER.debug('Session msg on %s of type: %s, themeflag: %s',
                                dev_name, device['NowPlayingItem']['Type'],
                                device['NowPlayingItem']['IsThemeMedia'])
                except KeyError:
                    pass

                active_devices.append(dev_name)
                if dev_name not in self._devices and \
                        device['DeviceId'] != self.config_entry[CONF_CLIENT_ID]:
                    _LOGGER.debug('New Jellyfin DeviceID: %s. Adding to device list.',
                                dev_name)
                    new = JellyfinDevice(device, self)
                    self._devices[dev_name] = new
                    new_devices.append(new)
                elif device['DeviceId'] != self.config_entry[CONF_CLIENT_ID]:
                    # Before we send in new data check for changes to state
                    # to decide if we need to fire the update callback
                    if not self._devices[dev_name].is_active:
                        # Device wasn't active on the last update
                        # We need to fire a device callback to let subs now
                        dev_update = True

                    do_update = self.update_check(
                        self._devices[dev_name], device)
                    self._devices[dev_name].update_data(device)
                    self._devices[dev_name].set_active(True)
                    if dev_update:
                        self._do_new_devices_callback(0)
                        dev_update = False
                    if do_update:
                        self._do_update_callback(dev_name)

            # Need to check for new inactive devices and flag
            for dev_id in self._devices:
                if dev_id not in active_devices:
                    # Device no longer active
                    if self._devices[dev_id].is_active:
                        self._devices[dev_id].set_active(False)
                        self._do_update_callback(dev_id)
                        self._do_stale_devices_callback(dev_id)

            # Call device callback if new devices were found.
            if new_devices:
                self._do_new_devices_callback(0)
        except Exception as e:
            _LOGGER.critical(traceback.format_exc())
            raise

    def update_check(self, existing: JellyfinDevice, new: JellyfinDevice):
        """ Check device state to see if we need to fire the callback.
        True if either state is 'Playing'
        False if both states are: 'Paused', 'Idle', or 'Off'
        True on any state transition.
        """
        autolog(">>>")

        old_state = existing.state
        if 'NowPlayingItem' in existing.session_raw:
            try:
                old_theme = existing.session_raw['NowPlayingItem']['IsThemeMedia']
            except KeyError:
                old_theme = False
        else:
            old_theme = False

        if 'NowPlayingItem' in new:
            if new['PlayState']['IsPaused']:
                new_state = STATE_PAUSED
            else:
                new_state = STATE_PLAYING

            try:
                new_theme = new['NowPlayingItem']['IsThemeMedia']
            except KeyError:
                new_theme = False

        else:
            new_state = STATE_IDLE
            new_theme = False

        if old_theme or new_theme:
            return False
        elif old_state == STATE_PLAYING or new_state == STATE_PLAYING:
            return True
        elif old_state != new_state:
            return True
        else:
            return False

    @property
    def info(self):
        if self.is_stopping:
            return None

        return self._info
        
    async def trigger_scan(self):
        await self.hass.async_add_executor_job(self.jf_client.jellyfin._post, "Library/Refresh")

    def get_server_url(self) -> str:
        return self.jf_client.config.data["auth.server"]

    def get_auth_token(self) -> str:
        return self.jf_client.config.data["auth.token"]

    async def get_item(self, id):
        return await self.hass.async_add_executor_job(self.jf_client.jellyfin.get_item, id)

    async def get_items(self, query=None):
        response = await self.hass.async_add_executor_job(self.jf_client.jellyfin.users, "/Items", "GET", query)
        #_LOGGER.debug("get_items: %s | %s", str(query), str(response))
        return response["Items"]

    async def set_playstate(self, session_id, state, params):
        await self.hass.async_add_executor_job(self.jf_client.jellyfin.post_session, session_id, "Playing/%s" % state,  params)

    async def play_media(self, session_id, media_id):
        params = {
            "playCommand": "PlayNow",
            "itemIds": media_id
        }
        await self.hass.async_add_executor_job(self.jf_client.jellyfin.post_session, session_id, "Playing", params)

    async def get_artwork(self, media_id) -> Tuple[Optional[str], Optional[str]]:
        query = {
            "format": "PNG",
            "maxWidth": 500,
            "maxHeight": 500
        }
        image = await self.hass.async_add_executor_job(self.jf_client.jellyfin.items, "GET", "%s/Images/Primary" % media_id, query)
        if image is not None:
            return (image, "image/png")

        return (None, None)

    async def get_play_info(self, media_id, profile):
        return await self.hass.async_add_executor_job(self.jf_client.jellyfin.get_play_info, media_id, profile)

    async def get_artwork_url(self, media_id) -> str:
        return await self.hass.async_add_executor_job(self.jf_client.jellyfin.artwork, media_id, "Primary", 500)

    @property
    def api(self):
        """ Return the api. """
        return self.jf_client.jellyfin

    @property
    def devices(self) -> Mapping[str, JellyfinDevice]:
        """ Return devices dictionary. """
        return self._devices

    @property
    def is_available(self):
        return not self.is_stopping

    # Callbacks

    def add_new_devices_callback(self, callback):
        """Register as callback for when new devices are added. """
        self._new_devices_callbacks.append(callback)
        _LOGGER.debug('Added new devices callback to %s', callback)

    def _do_new_devices_callback(self, msg):
        """Call registered callback functions."""
        for callback in self._new_devices_callbacks:
            _LOGGER.debug('Devices callback %s', callback)
            self._event_loop.call_soon(callback, msg)

    def add_stale_devices_callback(self, callback):
        """Register as callback for when stale devices exist. """
        self._stale_devices_callbacks.append(callback)
        _LOGGER.debug('Added stale devices callback to %s', callback)

    def _do_stale_devices_callback(self, msg):
        """Call registered callback functions."""
        for callback in self._stale_devices_callbacks:
            _LOGGER.debug('Stale Devices callback %s', callback)
            self._event_loop.call_soon(callback, msg)

    def add_update_callback(self, callback, device):
        """Register as callback for when a matching device changes."""
        self._update_callbacks.append([callback, device])
        _LOGGER.debug('Added update callback to %s on %s', callback, device)

    def remove_update_callback(self, callback, device):
        """ Remove a registered update callback. """
        if [callback, device] in self._update_callbacks:
            self._update_callbacks.remove([callback, device])
            _LOGGER.debug('Removed update callback %s for %s',
                          callback, device)

    def _do_update_callback(self, msg):
        """Call registered callback functions."""
        for callback, device in self._update_callbacks:
            if device == msg:
                _LOGGER.debug('Update callback %s for device %s by %s',
                              callback, device, msg)
                self._event_loop.call_soon(callback, msg)
