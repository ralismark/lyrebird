"""
Basic definitions for albums.
"""

from .fetch import AlbumFetch
from .fetch import TrackFetch
from .lrc import Lrc
from .metadata import AlbumMeta
from .metadata import TrackMeta
import pydantic


class Track(TrackMeta, TrackFetch):
    """
    Top-level schema for a track in an album.
    """

    model_config = pydantic.ConfigDict(extra="forbid")

    lrc: Lrc = Lrc()


class Album(AlbumMeta, AlbumFetch):
    """
    Top-level schema for an album.
    """

    model_config = pydantic.ConfigDict(extra="forbid")

    lrc: Lrc = Lrc()
    tracks: tuple[Track, ...]
