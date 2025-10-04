from .lrc import Lrc
from .schema import Album
from .fetch import fetch_cover
from pathlib import Path
import argparse
import mimetypes
import mutagen.id3
import mutagen.mp3
import shutil


def scan_dir(dir: Path) -> list[Path]:
    """
    Scan a directory, returning songs in order.
    """
    entries: list[tuple[int, Path]] = []
    for path in dir.iterdir():
        if path.suffix != ".mp3":
            continue

        index = int(path.name.split(" - ", maxsplit=1)[0])
        entries.append((index, path))

    out: list[Path] = []
    for i, (scanned_i, path) in enumerate(sorted(entries), start=1):
        assert i == scanned_i
        out.append(path)

    return out


def save_cover(url: str, dir: Path):
    mime, data = fetch_cover(url)
    ext = mimetypes.guess_extension(mime)
    assert ext

    with (dir / f"cover{ext}").open("wb") as f:
        f.write(data)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("spec", type=Album.argparse)
    parser.add_argument("--validate-only", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--rename", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--tags", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--lyrics", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--out", "-o", type=Path, default=Path.cwd())
    parser.add_argument("--only-if-out-missing", action=argparse.BooleanOptionalAction, default=False)
    args = parser.parse_args()

    album: Album = args.spec
    if args.validate_only:
        return

    albumdir = args.out / f"{album.album_artist} - {album.album}"
    if args.only_if_out_missing and albumdir.exists():
        print(f"Skipping: {albumdir} exist")
        return
    albumdir.mkdir(parents=True, exist_ok=True)

    # fetch album stuff
    fetched_files = album.fetch_album()
    assert len(fetched_files) == len(album.tracks)

    save_cover(album.cover, albumdir)

    for i, (fetched_path, track) in enumerate(zip(fetched_files, album.tracks), start=1):
        assert not any(badchar in track.title for badchar in "/"), track.title
        path = albumdir / f"{i:02} - {track.title}.mp3"

        mp3 = mutagen.mp3.MP3(fetched_path)
        assert mp3.info

        print(f"=== {path.name} ({int(mp3.info.length // 60)}:{int(mp3.info.length % 60):02})")

        # copy into output
        shutil.copyfile(fetched_path, path)

        # assert -1.5 <= mp3.info.length - track.duration <= 1.5, f"Track duration ({mp3.info.length}s) not expected ({track.duration}s)"

        if args.tags:
            utf8 = mutagen.id3.Encoding.UTF8

            frames: list[mutagen.id3.Frame] = []
            # track tags
            frames.extend([
                mutagen.id3.TIT2(encoding=utf8, text=track.title),
                mutagen.id3.TPE1(encoding=utf8, text=track.artists or [album.album_artist]),
                mutagen.id3.TRCK(encoding=utf8, text=[f"{i}/{len(album.tracks)}"]),
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
            cover_mime, cover_data = fetch_cover(track.cover or album.cover)
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
            tags.save(path, v1=0, v2_version=4)

        lrc = (
            Lrc
            .from_track(track, album, mp3.info.length)
            .update(album.lrc)
            .update(track.lrc)
        )
        if lyrics := lrc.load():
            with path.with_suffix(".lrc").open("w") as lrc:
                lrc.write(lyrics)


if __name__ == "__main__":
    main()
