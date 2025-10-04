#!/usr/bin/env python3

from lyrebird.schema import Album
from lyrebird.schema import Track
import datetime as dt
import argparse
import bs4
import requests
import re


def select(tag: bs4.Tag, query: str) -> bs4.Tag:
    matches = tag.css.select(query)
    assert len(matches) == 1, query
    return matches[0]


def scrape_track(track: bs4.Tag) -> Track:
    title = select(track, ".track-title").get_text().strip()
    time = select(track, ".time").get_text().strip()
    mm, ss = time.split(":")

    return Track(
        title=title,
        expect_duration=dt.timedelta(minutes=int(mm), seconds=int(ss)),
    )


def scrape_page(url: str) -> Album:
    r = requests.get(url)
    r.raise_for_status()
    soup = bs4.BeautifulSoup(r.text, "html.parser")

    title = select(soup, "h2.trackTitle").get_text().strip()
    artist = select(soup, "#band-name-location > .title").get_text().strip()
    cover = select(soup, "#tralbumArt > .popupImage")["href"]
    assert type(cover) is str

    released = select(soup, ".tralbumData.tralbum-credits").get_text().strip()
    m = re.match("released (([A-Z][a-z]+) ([0-9]+), ([0-9]+))", released)
    assert m
    date = dt.datetime.strptime(m.group(1), "%B %d, %Y").date()

    tracks = soup.css.select(".track_row_view")

    return Album(
        url=url,
        album=title,
        album_artist=artist,
        date=date,
        cover=cover,
        tracks=[scrape_track(t) for t in tracks],
    )
    raise ValueError()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    args = parser.parse_args()

    album = scrape_page(args.url)

    print(f"""
# fetching info
url: "{album.url}"

lrc:
  expect: true

# common metadata
album: "{album.album}"
album_artist: "{album.album_artist}"
date: {album.date:%Y-%m-%d}
cover: "{album.cover}"

tracks:
    """.strip())
    for track in album.tracks:
        print(f"""
- title: {track.title}
  expect_duration: {track.expect_duration}
        """.strip())


if __name__ == "__main__":
    main()
