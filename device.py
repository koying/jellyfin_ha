import logging
from .const import (
    STATE_OFF,
    STATE_IDLE,
    STATE_PAUSED,
    STATE_PLAYING,
)

_LOGGER = logging.getLogger(__name__)

class JellyfinDevice(object):
    """ Represents properties of an Emby Device. """
    def __init__(self, session, server):
        """Initialize Emby device object."""
        self.server = server
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
            url = self.server.api.artwork(self.media_id, image_type, 500)
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

    async def set_playstate(self, state, pos=0):
        """ Send media commands to server. """

        params = {}
        if state == 'Seek':
            params['SeekPositionTicks'] = int(pos * 10000000)
            params['static'] = 'true'

        await self.server.set_playstate(self.session_id, state, params)

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