"""
Fetching and processing lyrics.
"""

from .metadata import AlbumMeta
from .metadata import TrackMeta
import datetime as dt
import pydantic
import re
import requests
import typing as t


LRCLIB_API_BASE = "https://lrclib.net/api"

RE_LRC = re.compile(r"\[(\d\d):(\d\d)\.(\d\d)\](.*)")

HTTP = requests.Session()


def fmt_timedelta(t: dt.timedelta) -> str:
    neg = t < dt.timedelta()
    t = abs(t)

    mm, t = divmod(t, dt.timedelta(minutes=1))
    ss, t = divmod(t, dt.timedelta(seconds=1))
    xx = t // dt.timedelta(milliseconds=10)
    return f"{"-" if neg else ""}{mm:02}:{ss:02}.{xx:02}"


class LrclibResult(pydantic.BaseModel):
    id: int
    trackName: str
    artistName: str
    albumName: str
    duration: float
    instrumental: bool
    plainLyrics: str | None
    syncedLyrics: str | None

    source: str


class Lrc(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")

    # Validation
    expect: bool | None = None

    # Search
    id: int | None = None  # lrclib.net id
    try_exact: bool = True
    try_search: bool = True
    track: str = ""
    artist: str = ""
    album: str = ""
    duration: float = 0.0

    duration_slop: float = 2.5  # how much can duration differ before we reject it

    # Postprocessing
    offset: dt.timedelta | None = None
    start: dt.timedelta | None = None

    # Validator ===============================================================

    @pydantic.model_validator(mode="after")
    def _validate_id(self) -> t.Self:
        if self.id is not None and self.expect is False:
            raise ValueError("instrumental track cannot have id set")
        return self

    @pydantic.model_validator(mode="after")
    def _validate_offset_nand_start(self) -> t.Self:
        if self.offset and self.start:
            raise ValueError("cannot set both offset and start")
        return self

    # =========================================================================

    @classmethod
    def from_track(cls, track: TrackMeta, album: AlbumMeta, duration: float) -> t.Self:
        return cls(
            track=track.title,
            artist=", ".join(track.artists or [album.album_artist]),
            album=album.album or track.title,
            duration=duration,
        )

    def update(self, other: t.Self) -> t.Self:
        fields = {k: getattr(self, k) for k in self.model_fields_set}
        fields |= {k: getattr(other, k) for k in other.model_fields_set}
        return type(self)(**fields)

    def _fetch(self) -> LrclibResult | None:
        """
        Try to fetch .lrc from lrclib.net
        """
        # if id, use that directly
        if self.id:
            r = HTTP.get(f"{LRCLIB_API_BASE}/get/{self.id}")
            r.raise_for_status()
            return LrclibResult(**r.json(), source="id")

        # try match
        if self.try_exact:
            r = HTTP.get(
                f"{LRCLIB_API_BASE}/get",
                params={
                    "track_name": self.track,
                    "artist_name": self.artist,
                    "album_name": self.album,
                    "duration": round(self.duration),
                },
            )
            if r.status_code != 404:
                r.raise_for_status()
                data = LrclibResult(**r.json(), source="exact")
                if data.syncedLyrics:
                    return data

        # fallback: search
        if self.try_search:
            r = HTTP.get(
                f"{LRCLIB_API_BASE}/search",
                params={
                    "track_name": self.track,
                    "artist_name": self.artist,
                    "album_name": self.album,
                },
            )
            r.raise_for_status()
            matches = sorted(
                [LrclibResult(**x, source="search") for x in r.json()],
                key=lambda m: abs(m.duration - self.duration),
            )
            for m in matches:
                if not m.syncedLyrics:
                    continue  # we don't care about unsynced lyrics
                return m

        return None

    def _postprocess(self, lrc: str) -> str:
        """
        Perform post-processing steps on a lrc file.
        """
        # fastpath: if no processing needed, just return
        if self.offset is None and self.start is None:
            return lrc

        offset = self.offset or dt.timedelta()

        lines = []
        for i, line in enumerate(lrc.split("\n")):
            if not line:
                continue

            # read
            m = RE_LRC.fullmatch(line)
            assert m
            mm, ss, xx, lyric = m.groups()
            timestamp = dt.timedelta(
                minutes=int(mm), seconds=int(ss), milliseconds=10 * int(xx)
            )

            # apply offset
            if i == 0 and self.start:
                offset = self.start - timestamp
                print(f"    # offset: {fmt_timedelta(offset)}")

            timestamp += offset

            if i == 0 and not self.start:
                print(f"    start: {fmt_timedelta(timestamp)}")

            # write
            timestamp = max(timestamp, dt.timedelta())
            line = f"[{fmt_timedelta(timestamp)}]{lyric}"
            assert RE_LRC.fullmatch(line), f"{timestamp=} {line=}"
            lines.append(line)
        return "\n".join(lines)

    def load(self) -> str | None:
        if self.expect is False:
            return None

        print("  lrc:")

        result = self._fetch()
        if not result or not result.syncedLyrics:
            assert not self.expect, f"Expected lyrics but did not find ({result=})"
            print("    expect: false # did not find")
            return None

        print(f"    id: {result.id}")
        assert (
            abs(result.duration - self.duration) <= self.duration_slop
        ), f"lrc duration {result.duration}s too different from mp3 duration {self.duration}s"

        lrc = result.syncedLyrics
        lrc = self._postprocess(lrc)

        return lrc
