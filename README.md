# cldfofflinebrowser

A [cldfbench](https://github.com/cldf/cldfbench) plugin to create an offline-browseable representation
of a [CLDF Wordlist](https://github.com/cldf/cldf/tree/master/modules/Wordlist) with audio. This
representation consists of a set of HTML pages augmented with Javascript which can be viewed in a
web browser without requiring internet.

[![Build Status](https://github.com/cldf/cldfofflinebrowser/workflows/tests/badge.svg)](https://github.com/cldf/cldfofflinebrowser/actions?query=workflow%3Atests)
[![PyPI](https://img.shields.io/pypi/v/cldfofflinebrowser.svg)](https://pypi.org/project/cldfofflinebrowser)


## Install

Install the package via
```shell
pip install cldfofflinebrowser
```


## CLI

The functionality of this package is provided as `cldfbench` subcommand:
```shell
$ cldfbench offline.create -h
usage: cldfbench offline.create [-h] [--outdir OUTDIR] [--tiles TILES] [--with-audio] [--include INCLUDE] [--download-dir DOWNLOAD_DIR] [--padding PADDING] [--max-zoom MAX_ZOOM]
                                DATASET

Create an offline browseable version of a CLDF Wordlist.

positional arguments:
  DATASET               Dataset locator (i.e. URL or path to a CLDF metadata file or to the data file). Resolving dataset locators like DOI URLs might require installation of third-
                        party packages, registering such functionality using the `pycldf_dataset_resolver` entry point.

options:
  -h, --help            show this help message and exit
  --outdir OUTDIR       Directory in which to create the offline browseable files. (default: offline)
  --tiles TILES         Also add map tiles from the mbtiles file specified. (default: None)
  --with-audio          Also download audio files (default: False)
  --include INCLUDE     Whitespace separated list of parameter IDs (default: None)
  --download-dir DOWNLOAD_DIR
                        An existing directory to use for downloading a dataset (if necessary). (default: None)
  --padding PADDING     Padding in degree longitude at zoom level 5 to add to minimal bounding box when retrieving map tiles. (default: 8)
  --max-zoom MAX_ZOOM   Maximal zoom level for which to add map tiles. (default: 10)
```


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
