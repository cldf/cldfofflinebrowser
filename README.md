# cldfofflinebrowser

A [cldfbench](https://github.com/cldf/cldfbench) plugin to create an offline-browseable representation
of a [CLDF Wordlist](https://github.com/cldf/cldf/tree/master/modules/Wordlist) with audio. This
representation consists of a set of HTML pages augmented with Javascript which can be viewed in a
web browser without requiring internet.

[![Build Status](https://github.com/cldf/cldfofflinebrowser/workflows/tests/badge.svg)](https://github.com/cldf/cldfofflinebrowser/actions?query=workflow%3Atests)
[![PyPI](https://img.shields.io/pypi/v/cldfofflinebrowser.svg)](https://pypi.org/project/cldfofflinebrowser)


## Notes on offline maps

The browser pages use geographic maps to visualize the languages and words in the dataset in geographic
space. The Javascript library implementing this functionality requires map data to be available as
[set of tiles](https://en.wikipedia.org/wiki/Tiled_web_map).

`cldfbench create --tiles […]` allows you to add map tiles at different zoom levels for offline 
viewing to the browser. Since bulk downloads of map tiles from the internet require a lot of bandwith
and server processing, it is generally discouraged. Thus, `cldfofflinebrowser` support an alternative
way to obtain map tiles using a local [tileserver](https://github.com/maptiler/tileserver-gl), serving
data from a [MBTiles](https://wiki.openstreetmap.org/wiki/MBTiles) file.

So, after
- downloading a suitable MBTiles file from https://www.maptiler.com/on-prem-datasets/planet/ and
- installing `tileserver-gl`

you should be able to run
```shell
cldfbench offline.create --tiles PATH/TO/osm-*.mbtiles […]
```

To keep the amount of required map tiles at a minimum (making the browser's storage footprint smaller),
you should follow these guidelines:

 * *Keep your `LanguageTable` clean!*<br>
   Make sure it only contains languages that you have actual data points for,
   otherwise you'll end up downloading map tiles for regions that nobody will
   look at.
 * *Set `--max-zoom` to a reasonably low zoom level!*<br>
   This is especially true if your language sample spans over great distances.
   A map that covers half the planet will result in *tens if not
   hundreds of thousands of tile downloads* at higher zoom levels (10, 11, 12).
   So it's better to find a zoom-level that makes your data comfortable to look
   at and not go any deeper than that.
