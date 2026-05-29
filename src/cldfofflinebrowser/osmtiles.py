"""
Download mbtiles from https://www.maptiler.com/on-prem-datasets/planet/
Install and run tileserver-gl
https://tileserver.readthedocs.io/en/latest/installation.html

E.g. on Ubuntu 24.04 this can be done running
```
sudo apt install build-essential python3-setuptools pkg-config xvfb libglfw3-dev libuv1-dev \
libjpeg-turbo8 libicu-dev libcairo2-dev libpango1.0-dev libpng-dev libjpeg-dev libgif-dev \
librsvg2-dev librsvg2-dev libcurl4-openssl-dev libpixman-1-dev
sudo npm install -g tileserver-gl
sudo npm rebuild canvas --build-from-source
```
"""
import os
import math
import time
import pathlib
import subprocess
import dataclasses
from urllib.request import urlretrieve
from collections.abc import Iterable, Generator

from tqdm import tqdm
from clldutils.path import ensure_cmd

__all__ = ['download_tiles']

MAX_ZOOM = 14


@dataclasses.dataclass(frozen=True)
class Tile:
    """A map tile."""
    x: int
    y: int
    zoom: int

    @classmethod
    def from_latlon(cls, lat, lon, zoom):
        """
        See https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames
        """
        lat_rad = math.radians(lat)
        n = 2.0 ** zoom
        xtile = int((lon + 180.0) / 360.0 * n)
        ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return cls(xtile, ytile, zoom)

    def clamp(self) -> 'Tile':
        """make sure we don't hit imaginary tiles starting at 180°E or 180°W"""
        return Tile(
            max(0, min(2**self.zoom - 1, self.x)),
            max(0, min(2**self.zoom - 1, self.y)),
            self.zoom)

    def path(self, parent: pathlib.Path):
        return parent / str(self.zoom) / str(self.x) / f'{self.y}.png'


class TileServer:
    """A tileserver that can be run as context."""
    def __init__(self, mbtiles_path: pathlib.Path, port: int = 8080):
        self.mbtiles = mbtiles_path
        self.port = port
        self.process = None

    @property
    def command(self) -> list[str]:  # pragma: no cover
        """Command to invoke in a subprocess."""
        return [ensure_cmd("tileserver-gl"), "--file", self.mbtiles.name, "--port", str(self.port)]

    def url(self, t: Tile) -> str:
        """The URL from which to retrieve the PNG data for the tile."""
        return f'http://localhost:{self.port}/styles/basic-preview/512/{t.zoom}/{t.x}/{t.y}.png'

    def __enter__(self):
        self.process = subprocess.Popen(
            self.command,
            # shell=True is only required on Windows for global npm executables
            shell=os.name == "nt",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(self.mbtiles.parent),
        )
        time.sleep(3)

        if self.process.poll() is not None:
            _, stderr = self.process.communicate()
            raise ValueError(f"Failed to start server: {stderr}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.process:
            self.process.terminate()
            self.process.wait()


def clamp_latitude(lat: float) -> float:
    # osm's mercator projections only go up to ±85° anyways
    return min(85.0, max(-85.0, lat))


def wrap_longitude(lon: float) -> float:
    """Make sure lon is between -180 and 180."""
    while lon < -180.0:
        lon += 360.0
    while lon > 180.0:
        lon -= 360.0
    return lon


def distance_to_dateline(lon: float) -> float:
    if lon == 0.0:
        return 180.0
    if lon > 0.0:
        return lon - 180.0
    return lon + 180.0


def longitude_distance(lon1: float, lon2: float) -> float:
    if lon2 > lon1:
        return lon2 - lon1
    return 360.0 + lon2 - lon1


def get_bounding_box(coords: Iterable[tuple[float, float]]) -> tuple[float, float, float, float]:
    if not coords:
        raise ValueError('Cannot create bounding box without any coordinates.')

    north = clamp_latitude(max(lat for lat, _ in coords))
    south = clamp_latitude(min(lat for lat, _ in coords))

    normalised_lons = [wrap_longitude(lon) for _, lon in coords]
    west_of_null = min(normalised_lons)
    east_of_null = max(normalised_lons)

    by_dateline_distance = sorted(normalised_lons, key=distance_to_dateline)
    west_of_datel = by_dateline_distance[0]
    east_of_datel = by_dateline_distance[-1]

    if west_of_null < 0.0 and east_of_null < 0.0:
        return north, west_of_null, south, east_of_null
    if west_of_null > 0.0 and east_of_null > 0.0:
        return north, west_of_null, south, east_of_null
    if (
        longitude_distance(west_of_datel, east_of_datel)
        < longitude_distance(west_of_null, east_of_null)
    ):
        return north, west_of_datel, south, east_of_datel
    return north, west_of_null, south, east_of_null


def iter_area_tiles(
        north: float,
        west: float,
        south: float,
        east: float,
        zoom: int,
) -> Generator[Tile, None, None]:
    if zoom == 0:
        yield Tile(0, 0, zoom)
        return

    topleft = Tile.from_latlon(north, west, zoom).clamp()
    botright = Tile.from_latlon(south, east, zoom).clamp()

    def _tiles(tlx, brx, tly, bry):
        for x in range(tlx, brx):
            for y in range(tly, bry):
                yield Tile(x, y, zoom)

    if east > west:
        # one continuous box
        yield from _tiles(topleft.x, botright.x + 1, topleft.y, botright.y + 1)
        return

    # box west of the date line
    far_right = Tile.from_latlon(south, 180.0, zoom).clamp()
    yield from _tiles(topleft.x, far_right.x + 1, topleft.y, far_right.y + 1)
    # box east of the date line
    far_left = Tile.from_latlon(north, -180.0, zoom).clamp()
    yield from _tiles(far_left.x, botright.x + 1, far_left.y, botright.y + 1)


def padded_box(zoom, north, west, south, east, padding):
    pad = padding / (2**zoom)
    return (
        clamp_latitude(north + pad),
        wrap_longitude(west - pad),
        clamp_latitude(south - pad),
        wrap_longitude(east + pad))


def get_tile_list(
        minzoom: int,
        maxzoom: int,
        north: float,
        west: float,
        south: float,
        east: float,
        padding: int,
) -> list[Tile]:
    if maxzoom > MAX_ZOOM:
        raise ValueError(f'Only zoom levels up to {MAX_ZOOM} are supported.')
    padded_boxes = [
        (padded_box(zoom, north, west, south, east, padding), zoom)
        for zoom in range(minzoom, maxzoom + 1)]
    return [
        tile
        for (n, w, s, e), zoom in padded_boxes
        for tile in iter_area_tiles(n, w, s, e, zoom)]


def download_tiles(
        mbtiles_path: pathlib.Path,
        out_dir: pathlib.Path,
        coords: Iterable[tuple[float, float]],
        max_zoom: int,
        padding: int,
        log=None,
) -> int:
    north, west, south, east = get_bounding_box(coords)
    tile_list = get_tile_list(
        minzoom=0, maxzoom=max_zoom,
        north=north, west=west, south=south, east=east,
        padding=padding)
    if not tile_list:
        return 0  # pragma: no cover

    todo = [(tile, tile.path(out_dir)) for tile in tile_list]
    todo = [(tile, p) for tile, p in todo if not p.exists()]

    if log:
        log.info('Downloading %s out of %s required tiles.', len(todo), len(tile_list))

    with TileServer(mbtiles_path) as tileserver:
        for tile, tile_path in tqdm(todo):
            tile_path.parent.mkdir(exist_ok=True, parents=True)
            urlretrieve(tileserver.url(tile), tile_path)

    return len(todo)
