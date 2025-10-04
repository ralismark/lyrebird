from .exc import ExpectError
from .exc import ValidationError
from pathlib import Path
from yt_dlp import YoutubeDL
import functools
import pydantic
import requests
import shutil

CACHEDIR = Path.home() / ".cache" / "mp3fetch"


class AlbumFetch(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")

    url: str
    expect_files: list[str] | None = None

    def cachedir_album(self) -> Path:
        return CACHEDIR / self.url.replace("/", "%")

    @staticmethod
    def _do_fetch_album(url: str, dir: Path):
        try:
            ydl_opts = {
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                }],
                "writethumbnail": True,
                # s/%/%%/g for printf-string
                "outtmpl": str(dir).replace("%", "%%") + "/%(autonumber)02d - %(title)s.%(ext)s",
            }
            with YoutubeDL(ydl_opts) as ydl:
                error = ydl.download([url])
                if error:
                    raise RuntimeError(f"yt_dlp: {error}")
        except Exception as e:
            shutil.rmtree(dir)
            raise e

    def fetch_album(self) -> list[Path]:
        dir = self.cachedir_album()
        if not dir.exists():
            self._do_fetch_album(self.url, dir)

        # list of (track number, path)
        entries: list[tuple[int, Path]] = []
        for path in dir.iterdir():
            if path.suffix != ".mp3":
                continue

            index = int(path.name.split(" - ", maxsplit=1)[0])
            entries.append((index, path))
        entries = sorted(entries, key=lambda e: e[0])

        mp3s: list[Path] = [p for _, p in entries]

        # Validation
        for i, (scanned_i, _) in enumerate(sorted(entries), start=1):
            if i != scanned_i:
                raise ValidationError(f"skipped track index: {i} (found {path} next)")

        if self.expect_files is not None:
            filenames = [p.name for p in mp3s]
            if self.expect_files != filenames:
                raise ExpectError(f"did not match expect_files: {filenames}")
        else:
            print("expect_files:")
            for file in mp3s:
                print(f"  - \"{file.name.replace('"', '\\"')}\"")

        return mp3s


@functools.cache
def fetch_cover(url: str) -> tuple[str, bytes]:
    """
    Fetch a cover URL, returning its mime type and the data.
    """
    r = requests.get(url, headers={"user-agent": "Mozilla/5.0 (X11; Linux x86_64; rv:143.0) Gecko/20100101 Firefox/143.0"})
    r.raise_for_status()

    mime = r.headers["content-type"]
    data = r.content
    return mime, data
