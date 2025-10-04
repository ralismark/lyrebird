"""
Metadata definitions
"""

import datetime as dt
import pydantic


class AlbumMeta(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")

    album: str
    album_artist: str
    date: dt.date
    cover: str


class TrackMeta(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")

    title: str
    artists: list[str] | None = None
    cover: str | None = None
