from .fetch import fetch_cover
from .lrc import Lrc
from .metadata import tag
from .schema import Album
from pathlib import Path
import argparse
import datetime as dt
import mimetypes
import rich.console
import mutagen.mp3
import shutil
import yaml
import asyncio


console = rich.console.Console()


async def process_album(
    album: Album,
    outdir: Path,
):
    # fetch album stuff
    fetched_files = album.fetch()
    assert len(fetched_files) == len(album.tracks)

    if album.cover:
        mime, data = fetch_cover(album.cover)
        ext = mimetypes.guess_extension(mime)
        assert ext
        with (outdir / f"cover{ext}").open("wb") as f:
            f.write(data)

    for i, (fetched_path, track) in enumerate(
        zip(fetched_files, album.tracks), start=1
    ):
        path: Path
        if album.singles:
            path = outdir / f"{track.title}.mp3"
        else:
            path = outdir / f"{track.title}.mp3"
        console.print(f"===== {path.name}", style="bold yellow")

        try:
            mp3 = mutagen.mp3.MP3(fetched_path)
            assert mp3.info
            duration = dt.timedelta(seconds=mp3.info.length)
            mm, ss = divmod(duration, dt.timedelta(minutes=1))

            # copy into output
            shutil.copyfile(fetched_path, path)

            tags = tag(track, album, index=i)
            tags.save(path, v1=0, v2_version=4)

            lrc = Lrc.from_track(track, album, mp3.info.length)
            if not album.singles:
                lrc = lrc.update(album.lrc)
            lrc = lrc.update(track.lrc)

            if lyrics := lrc.load():
                with path.with_suffix(".lrc").open("w") as f:
                    f.write(lyrics)
        except Exception:
            console.print_exception()


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("spec", nargs="+", type=Path)
    parser.add_argument(
        "--validate-only", action=argparse.BooleanOptionalAction, default=False
    )
    parser.add_argument("--out", "-o", type=Path, default=Path.cwd())
    parser.add_argument("--ifne", action=argparse.BooleanOptionalAction, default=False)
    args = parser.parse_args()

    albums: list[tuple[Path, Album]] = []
    for spec in args.spec:
        try:
            with spec.open("r") as f:
                album = Album(**yaml.safe_load(f))
        except Exception as e:
            parser.error(f"not valid: {spec}\n{e}")
        albums.append((spec, album))

    if args.validate_only:
        return

    for spec, album in albums:
        albumdir: Path
        if album.singles:
            albumdir = args.out / f"{album.album_artist}"
        else:
            albumdir = args.out / f"{album.album_artist} - {album.album}"

        if args.ifne and albumdir.exists():
            continue

        console.print(f"===== {spec}", style="bold blue")
        albumdir.mkdir(parents=True, exist_ok=True)

        try:
            await process_album(album, albumdir)
        except Exception:
            console.print_exception()


if __name__ == "__main__":
    asyncio.run(main())
