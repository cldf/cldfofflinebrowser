# cldfofflinebrowser

Provides a cldfbench plugin to create offline-browseable representations
of the data in a CLDF dataset.

[![Build Status](https://github.com/cldf/cldfofflinebrowser/workflows/tests/badge.svg)](https://github.com/cldf/cldfofflinebrowser/actions?query=workflow%3Atests)
[![PyPI](https://img.shields.io/pypi/v/cldfofflinebrowser.svg)](https://pypi.org/project/cldfofflinebrowser)

## Notes on offline maps

`cldfbench create --with-tiles […]` allows you to predownload the world map at
different zoom levels for offline viewing.  These tiles are provided by the kind
folk at [OpenStreetMap][osm] – free of charge, no less.  But obviously they're
not wizards who can make bandwidth appear out of thin air.  That's why we should
all be nice to them and [play by their rules][osm-policy] to reduce strain on
their servers.

[osm]: https://www.openstreetmap.org/
[osm-policy]: https://operations.osmfoundation.org/policies/tiles/

This is why we would like to ask you to follow the following guidelines:

 * *Don't delete your `offline/tiles` folder unless you really, really have
   to!*<br>
   If you do you'll just end up re-downloading the same map tiles all over
   again, which is a waste of everybody's time and bandwidth.
 * *Keep your `LanguageTable` clean!*<br>
   Make sure it only contains languages that you have actual data points for,
   otherwise you'll end up downloading map tiles for regions that nobody will
   look at.
 * *Set `--max-zoom` to a reasonably low zoom level!*<br>
   This is especially true if your language sample spans over great distances.
   A map of that covers like half the planet will result in *tens if not
   hundreds of thousands of tile downloads* at higher zoom levels (10, 11, 12).
   So it's better to find a zoom-level that makes your data comfortable to look
   at and not go any deeper than that.
 * *Bulk-downloading map tiles for zoom level 13 or higher is forbidden!*<br>
   At these zoom levels, if you try to download more than 250 tiles at once, OSM
   will straight-up refuse your request.  End of story.
 * *Don't run `cldfbench offline.create` multiple times at once!*<br>
   Whatever download speed you get is probably either your bandwidth limit or
   the server's.  Either way, battering the server with more download requests
   isn't gonna make anything faster.

## FAQ

**Q:** How to add sound files and transcriptions to an offline dataset?

**A:** If you want to make a new sound file and transcription browseable in an offline version:
1. Determine relevant language (`LID`) and parameter (`PID`) (aka concept) IDs.
2. Copy the sound file to `./parameter-<PID>/<LID>.mp3`.
3. Add a corresponding row to `cldf/media.csv`.
4. Add a row to `cldf/forms.csv`.
5. Re-run `cldfbench offline.create ...`.
