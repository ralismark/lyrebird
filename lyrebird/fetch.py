"""
Specify how to fetch the MP3s for an album.
"""

from .exc import ExpectError
from .exc import ValidationError
from pathlib import Path
from yt_dlp import YoutubeDL
import functools
import pydantic
import requests
import shutil
import typing as t

CACHEDIR = Path.home() / ".cache" / "lyrebird"


def fetch_mp3s(url: str) -> Path:
    dir = CACHEDIR / url.replace("/", "%")
    if dir.exists():
        return dir

    try:
        with YoutubeDL(
            {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                    }
                ],
                "writethumbnail": True,
                # s/%/%%/g for printf-string
                "outtmpl": str(dir).replace("%", "%%")
                + "/%(autonumber)02d - %(title)s.%(ext)s",
            }
        ) as ydl:
            error = ydl.download([url])
            if error:
                raise RuntimeError(f"yt_dlp: {error}")
    except Exception as e:
        shutil.rmtree(dir)
        raise e
    else:
        return dir


# There's kinda 3 categories of specification:
#
# 1. One URL (the album) with a simple one-to-one correspondence between files
#    from that URL and track specs.
#
# 2. Each entry is a separate URL. No album-wide URL. i.e. singles collection
#    mode.
#
# 3. Mix of the two - one default URL, but each track specifies the file and
#    (optionally) a URL it is from.


class _TrackSrc(pydantic.BaseModel):
    url: str
    expect_count: int | None
    file: int | str

    def fetch(self) -> Path:
        dir = fetch_mp3s(self.url)

        # list of (track number, path)
        entries: list[tuple[int, Path]] = []
        for path in dir.iterdir():
            if path.suffix != ".mp3":
                continue

            index = int(path.name.split(" - ", maxsplit=1)[0])
            entries.append((index, path))
        entries = sorted(entries, key=lambda e: e[0])
        for i, (scanned_i, path) in enumerate(sorted(entries), start=1):
            assert i == scanned_i, f"skipped track index {i} (found {path} next)"

        if self.expect_count is not None and self.expect_count != len(entries):
            raise ValidationError(
                f"expected to fetch {self.expect_count} from {self.url}, got {len(entries)}"
            )

        # get file
        file: Path
        if isinstance(self.file, int):
            _, file = entries[self.file]
        elif isinstance(self.file, str):
            file = dir / self.file
            if not file.exists():
                raise ExpectError(f"url {self.url!r} did not yield file {self.file!r}")
        else:
            assert False

        return file


class TrackFetch(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")

    url: str | None = None
    file: str | None = None


class AlbumFetch(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")

    url: str | None

    tracks: tuple[TrackFetch, ...]

    @pydantic.model_validator(mode="after")
    def _validate_track_files_all_or_nothing(self) -> t.Self:
        if any(t.file is None for t in self.tracks) and not all(
            t.file is None for t in self.tracks
        ):
            raise ValueError("must specify file for either every or no tracks")
        return self

    @pydantic.model_validator(mode="after")
    def _validate_no_album_url(self) -> t.Self:
        if self.url is None:
            for i, track in enumerate(self.tracks):
                if track.url is None:
                    raise ValueError(f"no url for both album and track[{i}]")

        return self

    # =========================================================================

    def _srcs(self) -> list[_TrackSrc]:
        if all(t.url is None and t.file is None for t in self.tracks):
            # basic mode: one to one mapping from mp3s in url to tracks
            assert self.url
            return [
                _TrackSrc(
                    url=self.url,
                    expect_count=len(self.tracks),
                    file=i,
                )
                for i, t in enumerate(self.tracks)
            ]

        # advanced mode: standalone tracks, album url is default
        srcs = []
        for track in self.tracks:
            if track.file:
                url = track.url or self.url
                assert url is not None
                srcs.append(
                    _TrackSrc(
                        url=url,
                        expect_count=None,
                        file=track.file,
                    )
                )
            else:
                assert track.url
                srcs.append(
                    _TrackSrc(
                        url=track.url,
                        expect_count=1,
                        file=0,
                    )
                )

        return srcs

    def fetch(self) -> list[Path]:
        return [src.fetch() for src in self._srcs()]


@functools.cache
def fetch_cover(url: str) -> tuple[str, bytes]:
    """
    Fetch a cover URL, returning its mime type and the data.
    """
    r = requests.get(
        url,
        headers={
            # "user-agent": "Mozilla/5.0 (X11; Linux x86_64; rv:143.0) Gecko/20100101 Firefox/143.0"
        },
    )
    r.raise_for_status()

    mime = r.headers["content-type"]
    data = r.content
    return mime, data
