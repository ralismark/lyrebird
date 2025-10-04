"""
Metadata definitions
"""

from .fetch import fetch_cover
import datetime as dt
import mutagen.id3
import mutagen.mp3
import pydantic
import typing as t

if t.TYPE_CHECKING:
    from .schema import Track
    from .schema import Album


class AlbumMeta(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")

    album: str
    album_artist: str
    date: dt.date
    cover: str


class TrackMeta(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")

    title: str = pydantic.Field(pattern="[^/]+")
    artists: list[str] | None = None
    cover: str | None = None


# TODO this depends too much on the top-level types
def tag(
    track: "Track",
    album: "Album",
    index: int,
) -> mutagen.id3.ID3:
    utf8 = mutagen.id3.Encoding.UTF8

    frames: list[mutagen.id3.Frame] = []
    # track tags
    frames.extend([
        mutagen.id3.TIT2(encoding=utf8, text=track.title),
        mutagen.id3.TPE1(encoding=utf8, text=track.artists or [album.album_artist]),
        mutagen.id3.TRCK(encoding=utf8, text=[f"{index}/{len(album.tracks)}"]),
    ])
    # album tags
    frames.extend([
        mutagen.id3.TALB(encoding=utf8, text=[album.album]),
        mutagen.id3.TPE2(encoding=utf8, text=[album.album_artist]),
        mutagen.id3.TYER(encoding=utf8, text=[album.date.strftime("%Y")]),
        mutagen.id3.WOAS(url=album.url),
    ])
    # cover
    cover_url = track.cover or album.cover
    cover_mime, cover_data = fetch_cover(cover_url)
    frames.extend([
        mutagen.id3.APIC(
            mime=cover_mime,
            type=mutagen.id3.PictureType.COVER_FRONT,
            desc=cover_url,
            data=cover_data,
        )
    ])

    tags = mutagen.id3.ID3()
    for frame in frames:
        tags.add(frame)
    return tags
