"""
Basic definitions for albums.
"""

from .fetch import AlbumFetch
from .lrc import Lrc
from .metadata import AlbumMeta
from .metadata import TrackMeta
import datetime as dt
import pydantic
import typing as t
import yaml


class Track(TrackMeta):
    """
    Top-level schema for a single track.
    """
    model_config = pydantic.ConfigDict(extra="forbid")

    expect_duration: dt.timedelta | None = None
    lrc: Lrc = Lrc()


class Album(AlbumMeta, AlbumFetch):
    """
    Top-level schema for an album.
    """
    model_config = pydantic.ConfigDict(extra="forbid")

    lrc: Lrc = Lrc()
    tracks: list[Track]

    @pydantic.model_validator(mode="after")
    def _validate_ntracks(self) -> t.Self:
        # Treat `tracks` as canonical
        ntracks = len(self.tracks)
        if self.expect_files is not None:
            if ntracks != len(self.expect_files):
                raise ValueError(f"len(expect_files) ({len(self.expect_files)}) != len(tracks) {ntracks}")
        return self

    # =========================================================================

    @classmethod
    def argparse(cls, path: str) -> t.Self:
        with open(path, "rt") as f:
            try:
                return cls(**yaml.safe_load(f))
            except pydantic.ValidationError as e:
                print(e)
                raise e
