import logging

from homeassistant.components.media_player import BrowseError, BrowseMedia
from homeassistant.components.media_player.const import (
    MEDIA_CLASS_ALBUM,
    MEDIA_CLASS_ARTIST,
    MEDIA_CLASS_CHANNEL,
    MEDIA_CLASS_DIRECTORY,
    MEDIA_CLASS_EPISODE,
    MEDIA_CLASS_MOVIE,
    MEDIA_CLASS_MUSIC,
    MEDIA_CLASS_PLAYLIST,
    MEDIA_CLASS_SEASON,
    MEDIA_CLASS_TRACK,
    MEDIA_CLASS_TV_SHOW,
    MEDIA_TYPE_ALBUM,
    MEDIA_TYPE_ARTIST,
    MEDIA_TYPE_CHANNEL,
    MEDIA_TYPE_EPISODE,
    MEDIA_TYPE_MOVIE,
    MEDIA_TYPE_PLAYLIST,
    MEDIA_TYPE_SEASON,
    MEDIA_TYPE_TRACK,
    MEDIA_TYPE_TVSHOW,
)

from .device import JellyfinDevice

PLAYABLE_MEDIA_TYPES = [
    MEDIA_TYPE_ALBUM,
    MEDIA_TYPE_ARTIST,
    MEDIA_TYPE_TRACK,
]

CONTAINER_TYPES_SPECIFIC_MEDIA_CLASS = {
    MEDIA_TYPE_ALBUM: MEDIA_CLASS_ALBUM,
    MEDIA_TYPE_ARTIST: MEDIA_CLASS_ARTIST,
    MEDIA_TYPE_PLAYLIST: MEDIA_CLASS_PLAYLIST,
    MEDIA_TYPE_SEASON: MEDIA_CLASS_SEASON,
    MEDIA_TYPE_TVSHOW: MEDIA_CLASS_TV_SHOW,
}

CHILD_TYPE_MEDIA_CLASS = {
    MEDIA_TYPE_SEASON: MEDIA_CLASS_SEASON,
    MEDIA_TYPE_ALBUM: MEDIA_CLASS_ALBUM,
    MEDIA_TYPE_ARTIST: MEDIA_CLASS_ARTIST,
    MEDIA_TYPE_MOVIE: MEDIA_CLASS_MOVIE,
    MEDIA_TYPE_PLAYLIST: MEDIA_CLASS_PLAYLIST,
    MEDIA_TYPE_TRACK: MEDIA_CLASS_TRACK,
    MEDIA_TYPE_TVSHOW: MEDIA_CLASS_TV_SHOW,
    MEDIA_TYPE_CHANNEL: MEDIA_CLASS_CHANNEL,
    MEDIA_TYPE_EPISODE: MEDIA_CLASS_EPISODE,
}

_LOGGER = logging.getLogger(__name__)

class UnknownMediaType(BrowseError):
    """Unknown media type."""

def Type2Mediatype(type):
    switcher = {
        "Movie": MEDIA_TYPE_MOVIE,
        "Series": MEDIA_TYPE_TVSHOW,
        "Season": MEDIA_TYPE_SEASON,
        "Episode": MEDIA_TYPE_EPISODE,
        "Music": MEDIA_TYPE_ALBUM,
        "Audio": MEDIA_TYPE_TRACK,
        "BoxSet": MEDIA_CLASS_DIRECTORY,
        "Folder": MEDIA_CLASS_DIRECTORY,
        "CollectionFolder": MEDIA_CLASS_DIRECTORY,
        "Playlist": MEDIA_CLASS_DIRECTORY,
        "MusicArtist": MEDIA_TYPE_ARTIST,
        "MusicAlbum": MEDIA_TYPE_ALBUM,
        "Audio": MEDIA_TYPE_TRACK,
    }
    return switcher[type]

def Type2Mediaclass(type):
    switcher = {
        "Movie": MEDIA_CLASS_MOVIE,
        "Series": MEDIA_CLASS_TV_SHOW,
        "Season": MEDIA_CLASS_SEASON,
        "Episode": MEDIA_CLASS_EPISODE,
        "Music": MEDIA_CLASS_DIRECTORY,
        "BoxSet": MEDIA_CLASS_DIRECTORY,
        "Folder": MEDIA_CLASS_DIRECTORY,
        "CollectionFolder": MEDIA_CLASS_DIRECTORY,
        "Playlist": MEDIA_CLASS_DIRECTORY,
        "MusicArtist": MEDIA_CLASS_ARTIST,
        "MusicAlbum": MEDIA_CLASS_ALBUM,
        "Audio": MEDIA_CLASS_TRACK,
    }
    return switcher[type]

def IsPlayable(type):
    switcher = {
        "Movie": True,
        "Series": True,
        "Season": True,
        "Episode": True,
        "Music": False,
        "BoxSet": True,
        "Folder": False,
        "CollectionFolder": False,
        "Playlist": True,
        "MusicArtist": True,
        "MusicAlbum": True,
        "Audio": True,
    }
    return switcher[type]

async def library_items(device: JellyfinDevice, media_content_type=None, media_content_id=None):
    """
    Create response payload to describe contents of a specific library.

    Used by async_browse_media.
    """

    library_info = None
    query = None

    if media_content_type in [None, "library"]:
        library_info = BrowseMedia(
            media_class=MEDIA_CLASS_DIRECTORY,
            media_content_id="library",
            media_content_type="library",
            title="Media Library",
            can_play=False,
            can_expand=True,
            children=[],
        )
    elif media_content_type in [MEDIA_CLASS_DIRECTORY, MEDIA_TYPE_ARTIST, MEDIA_TYPE_ALBUM, MEDIA_TYPE_PLAYLIST, MEDIA_TYPE_TVSHOW, MEDIA_TYPE_SEASON]:
        query = {
            "ParentId": media_content_id
        }

        parent_item = await device.get_item(media_content_id)
        library_info = BrowseMedia(
            media_class=media_content_type,
            media_content_id=media_content_id,
            media_content_type=media_content_type,
            title=parent_item["Name"],
            can_play=IsPlayable(parent_item["Type"]),
            can_expand=True,
            thumbnail=await device.get_artwork_url(media_content_id),
            children=[],
        )
    else:
        query = {
            "Id": media_content_id
        }
        library_info = BrowseMedia(
            media_class=MEDIA_CLASS_DIRECTORY,
            media_content_id=media_content_id,
            media_content_type=media_content_type,
            title="",
            can_play=True,
            can_expand=False,
            thumbnail=await device.get_artwork_url(media_content_id),
            children=[],
        )

    items = await device.get_items(query)
    for item in items:
        if media_content_type in [None, "library", MEDIA_CLASS_DIRECTORY, MEDIA_TYPE_ARTIST, MEDIA_TYPE_ALBUM, MEDIA_TYPE_PLAYLIST, MEDIA_TYPE_TVSHOW, MEDIA_TYPE_SEASON]:
            if item["IsFolder"]:
                library_info.children.append(BrowseMedia(
                    media_class=Type2Mediaclass(item["Type"]),
                    media_content_id=item["Id"],
                    media_content_type=Type2Mediatype(item["Type"]),
                    title=item["Name"],
                    can_play=IsPlayable(item["Type"]),
                    can_expand=True,
                    children=[],
                    thumbnail=await device.get_artwork_url(item["Id"])
                ))
            else:
                library_info.children.append(BrowseMedia(
                    media_class=Type2Mediaclass(item["Type"]),
                    media_content_id=item["Id"],
                    media_content_type=Type2Mediatype(item["Type"]),
                    title=item["Name"],
                    can_play=IsPlayable(item["Type"]),
                    can_expand=False,
                    children=[],
                    thumbnail=await device.get_artwork_url(item["Id"])
                ))
        else:
            library_info.title = item["Name"]
            library_info.media_content_id = item["Id"],
            library_info.media_content_type = Type2Mediatype(item["Type"])
            library_info.media_class = Type2Mediaclass(item["Type"])
            library_info.can_expand = False
            library_info.can_play=IsPlayable(item["Type"]),
            break

    return library_info
