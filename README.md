# What

_Lyrebird_ has organically grown out of my desire to systematically tag my music collection, into a toolkit for fetching and processing music and its lyrics.

# How

- Music is fetched from whereever via [yt-dlp](https://github.com/yt-dlp/yt-dlp).
- Lyrics are fetched from <https://lrclib.net>

Currently, dependencies are provided using Nix via `shell.nix`.
Once it is loaded, the main entrypoint is `python3 -m lyrebird`, aliased as just the `lyrebird` command.

# Who

I built this myself for myself!
It is provided as-is, with no guarantees of fitness for purpose or support.

# Why

It began with a single question:
_How do you tag MP3s with multiple artists?_

Following jumbled and contradictory guidance on separators I found over the years, mixed with diverging behaviour across tag editors, led to my library containing numerous instances of artists strung together, not recognisable as the distinct individuals they were meant to be.
And so eventually, I was forced to seek out the sacred texts themselves (the standards documents) which, I learnt, decreed the correct method:

- for ID3v2.3.0, [list them all in a single TPE1 frame, separated by the "/" character](https://id3.org/id3v2.3.0#TPE1).

	> TPE1: The 'Lead artist(s)/Lead performer(s)/Soloist(s)/Performing group' is used for the main artist(s). They are seperated with the "/" character.

- for ID3v2.4.0, [list them in a single TPE1 frame, separated by a NULL character](https://id3.org/id3v2.4.0-frames#line-256).

	> All text information frames supports multiple strings, stored as a null separated list, where null is reperesented by the termination code for the charater encoding.

Now, when I set out on this quest I was only dimly aware of the existence of two competing standards -- this detail was obscured in my previous tag editor, [EasyTAG](https://wiki.gnome.org/Apps/EasyTAG), and so I did not suspect it.
Similarly was the use of NULL for ID3v2.4 -- I now see why the question was so difficult to answer, as NULL is not typically typeable, and so must be transliterated by the tag editor.
And naturally, they disagreed on its representation, and some outright did not support it.

(In fact, EasyTAG had told me it [supported splitting tags on " - "](https://help.gnome.org/users/easytag/stable/problems-ogg-split.html.en), but I did not notice the caveat that that behaviour was only for Ogg and FLAC, not MP3)

Like many quests, I was changed by it; I could not return to how things were before.
I now knew how to remedy this problem outright in my collections, and how tag editors would betray me in my journey towards it.
And so I reached for the tools I knew best: Python scripts.

And if tagging, why not also fetching the music in the first place?
Why not also fetching and cleaning their lyrics?
