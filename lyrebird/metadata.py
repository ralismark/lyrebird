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

    album: str | None
    album_artist: str
    date: dt.date | None
    cover: str | None

    singles: bool = False


class TrackMeta(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")

    title: str = pydantic.Field(pattern="[^/]+")
    artists: list[str] | None = None
    cover: str | None = None


# TODO this depends too much on the top-level types
def _generate_tags(
    track: "Track",
    album: "Album",
    index: int,
) -> t.Iterable[mutagen.id3.Frame]:
    utf8 = mutagen.id3.Encoding.UTF8

    # track tags
    yield mutagen.id3.TIT2(encoding=utf8, text=track.title)
    yield mutagen.id3.TPE1(encoding=utf8, text=track.artists or [album.album_artist])
    if not album.singles:
        yield mutagen.id3.TRCK(encoding=utf8, text=[f"{index}/{len(album.tracks)}"])

    # album tags
    if not album.singles:
        assert album.album
        assert album.album_artist
        assert album.date

        yield mutagen.id3.TALB(encoding=utf8, text=[album.album])
        yield mutagen.id3.TPE2(encoding=utf8, text=[album.album_artist])
        yield mutagen.id3.TYER(encoding=utf8, text=[album.date.strftime("%Y")])

    # fetch
    yield mutagen.id3.WOAS(url=track.url or album.url)

    # cover
    cover_url = track.cover or album.cover
    if cover_url:
        cover_mime, cover_data = fetch_cover(cover_url)
        yield mutagen.id3.APIC(
            mime=cover_mime,
            type=mutagen.id3.PictureType.COVER_FRONT,
            desc=cover_url,
            data=cover_data,
        )


def tag(
    track: "Track",
    album: "Album",
    index: int,
) -> mutagen.id3.ID3:
    tags = mutagen.id3.ID3()
    for frame in _generate_tags(track, album, index):
        tags.add(frame)
    return tags
