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


class InheritableMeta(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")

    artist: list[str] | None = None
    date: dt.date | None = None
    cover: str | None = None

    @pydantic.field_validator("artist", mode="before")
    @classmethod
    def listify(cls, value: str | list[str]) -> list[str]:
        if not isinstance(value, list):
            return [value]
        return value


class AlbumMeta(InheritableMeta):
    model_config = pydantic.ConfigDict(extra="forbid")

    singles: bool = False
    album: str | None = None


class TrackMeta(InheritableMeta):
    model_config = pydantic.ConfigDict(extra="forbid")

    title: str = pydantic.Field(pattern="[^/]+")


# TODO this depends too much on the top-level types
def _generate_tags(
    track: "Track",
    album: "Album",
    index: int,
) -> t.Iterable[mutagen.id3.Frame]:
    utf8 = mutagen.id3.Encoding.UTF8

    # track tags
    yield mutagen.id3.TIT2(encoding=utf8, text=track.title)

    assert (artist := track.artist or album.artist) is not None
    yield mutagen.id3.TPE1(encoding=utf8, text=artist)

    if (date := track.date or album.date) is not None:
        yield mutagen.id3.TDRL(encoding=utf8, text=[date.strftime("%Y-%m-%d")])

    # sequence
    if not album.singles:
        yield mutagen.id3.TRCK(encoding=utf8, text=[f"{index}/{len(album.tracks)}"])

    # album tags
    if not album.singles:
        assert album.album
        assert album.artist
        assert album.date

        yield mutagen.id3.TALB(encoding=utf8, text=[album.album])
        yield mutagen.id3.TPE2(encoding=utf8, text=album.artist)

    # fetch
    yield mutagen.id3.WOAS(url=track.url or album.url)

    # cover
    if (cover := track.cover or album.cover) is not None:
        cover_mime, cover_data = fetch_cover(cover)
        yield mutagen.id3.APIC(
            mime=cover_mime,
            type=mutagen.id3.PictureType.COVER_FRONT,
            desc=cover,
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
