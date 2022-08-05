"""
Use the downloadosmtiles command to manage a map tiles.

See http://manpages.ubuntu.com/manpages/xenial/man1/downloadosmtiles.1p.html
"""
import collections
import decimal
import itertools
import math
import pathlib
import random
import subprocess
import sys
from urllib.request import Request, urlopen

__all__ = [
    'CMD', 'TileList',
    'get_bounding_box',
    'get_area_tiles',
    'download_tiles',
]

# The following command will be available in Ubuntu, if libgeo-osm-tiles-perl is installed.
CMD = "downloadosmtiles"


def clamp_latitude(lat):
    return min(90.0, max(-90.0, lat))


def wrap_longitude(lon):
    while lon < -180.0:
        lon += 360.0
    while lon > 180.0:
        lon -= 360.0
    return lon


def distance_to_dateline(lon):
    if lon == 0.0:
        return 180.0
    elif lon > 0.0:
        return lon - 180.0
    else:
        return lon + 180.0


def longitude_distance(lon1, lon2):
    if lon2 > lon1:
        return lon2 - lon1
    else:
        return 360.0 + lon2 - lon1


def get_bounding_box(coords):
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
    elif west_of_null > 0.0 and east_of_null > 0.0:
        return north, west_of_null, south, east_of_null
    elif (
        longitude_distance(west_of_datel, east_of_datel)
        < longitude_distance(west_of_null, east_of_null)
    ):
        return north, west_of_datel, south, east_of_datel
    else:
        return north, west_of_null, south, east_of_null


def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)


def get_area_tiles(north, west, south, east, zoom):
    if zoom == 0:
        yield (0, 0)
        return

    # make sure we don't hit imaginary tiles starting at 180°E or 180°W
    def clamp_tile(pair):
        return (
            max(0, min(2**zoom - 1, pair[0])),
            max(0, min(2**zoom - 1, pair[1])))

    topleft_x, topleft_y = clamp_tile(deg2num(north, west, zoom))
    botright_x, botright_y = clamp_tile(deg2num(south, east, zoom))

    if east > west:
        # one continuous box
        for x in range(topleft_x, botright_x + 1):
            for y in range(topleft_y, botright_y + 1):
                yield (x, y)
    else:
        # box west of the date line
        far_right_x, far_right_y = clamp_tile(deg2num(south, 180.0, zoom))
        for x in range(topleft_x, far_right_x + 1):
            for y in range(topleft_y, far_right_y + 1):
                yield (x, y)
        # box east of the date line
        far_left_x, far_left_y = clamp_tile(deg2num(north, -180.0, zoom))
        for x in range(far_left_x, botright_x + 1):
            for y in range(far_left_y, botright_y + 1):
                yield (x, y)


def padded_box(zoom, north, west, south, east, padding):
    pad = padding / (2**zoom)
    return (
        clamp_latitude(north + pad),
        wrap_longitude(west - pad),
        clamp_latitude(south - pad),
        wrap_longitude(east + pad))


def get_tile_list(minzoom, maxzoom, north, west, south, east, padding):
    if maxzoom > 12:
        # https://operations.osmfoundation.org/policies/tiles/
        raise ValueError('Maxzoom exceeds level allowed for bulk downloading!')

    padded_boxes = [
        (padded_box(zoom, north, west, south, east, padding), zoom)
        for zoom in range(minzoom, maxzoom + 1)]
    tile_list = [
        (x, y, zoom)
        for (n, w, s, e), zoom in padded_boxes
        for x, y in get_area_tiles(n, w, s, e, zoom)]
    return tile_list


def get_tile_path(parent, x, y, zoom):
    return parent / str(zoom) / str(x) / '{}.png'.format(y)


def download_tiles(tile_list, path, log=None):  # pragma: nocover
    todo = [
        (x, y, zoom)
        for x, y, zoom in tile_list
        if not get_tile_path(path, x, y, zoom).exists()
        and zoom <= 12]

    if log is not None:
        if len(tile_list) - len(todo):
            log.info(
                '{} tiles are already there.  '
                "No need to redownload them.".format(len(tile_list) - len(todo)))
        if not todo:
            log.info('Nothing to download')

    i = None
    for i, (x, y, zoom) in enumerate(todo):
        if (i + 1) % 10 == 0:
            print('{}....'.format(i + 1), end='', file=sys.stderr, flush=True)

        tile_path = get_tile_path(path, x, y, zoom)
        if not tile_path.parent.is_dir():
            tile_path.parent.mkdir(parents=True)

        request = Request(
            'http://{subdomain}.tile.openstreetmap.org/{z}/{x}/{y}.png'.format(
                subdomain=random.choice(('a', 'b', 'c')), x=x, y=y, z=zoom),
            headers={'User-Agent': 'cldfofflinebrowser/0.1'})
        with urlopen(request) as conn:
            tile_data = conn.read()

        with open(tile_path, 'wb') as f:
            f.write(tile_data)

    if i is not None and (i + 1) > 10:
        msg = '' if ((i + 1) % 10) == 0 else i + 1
        print(msg, file=sys.stderr, flush=True)

    return len(todo)


def downloadosmtiles(*args, **opts):
    return subprocess.check_call(
        [CMD] + list(args) + ['--{}={}'.format(k, str(v)) for k, v in opts.items()])


class TileList:
    def __init__(self, p):
        subprocess.call([CMD, '-xyz'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.path = pathlib.Path(p)

    def create(self, coords, maxzoom, padding=10):
        """
        Write a list of tiles required to fit all coords in the zoom levels from minzoom to maxzoom.

        :param coords: `list` of (lat, lon) pairs.
        :param maxzoom: `int` maximal required zoom level
        :return:
        """
        if maxzoom > 12:
            # https://operations.osmfoundation.org/policies/tiles/
            raise ValueError('Maxzoom exceeds level allowed for bulk downloading!')

        def _required_tiles():
            return {z: list(t) for z, t in itertools.groupby(self, lambda xyz: int(xyz[2]))}

        lats, lons = list(zip(*coords))
        minlat, maxlat = min(lats), max(lats)
        minlon, maxlon = min(lons), max(lons)
        tiles = collections.defaultdict(set)
        # then enlarge bounding box per zoom level
        for i, zoom in enumerate(range(5, maxzoom + 1)):
            pad = decimal.Decimal(padding / pow(2, i))
            minlonpad, maxlonpad = minlon - pad, maxlon + pad
            minmaxlonpad = None
            if maxlonpad > 180:
                minmaxlonpad = (-180, -360 + maxlonpad)
                maxlonpad = 180
            if minlonpad < -180:
                minmaxlonpad = (360 + minlonpad, 180)
                minlonpad = -180
            downloadosmtiles(
                dumptilelist=self.path,
                lat='{}:{}'.format(minlat - pad, maxlat + pad),
                lon='{}:{}'.format(minlonpad, maxlonpad),
                zoom='{}:{}'.format(zoom, zoom),
            )
            tiles[zoom].update(_required_tiles()[zoom])
            # map crossing date line? add other side
            if minmaxlonpad:
                downloadosmtiles(
                    dumptilelist=self.path,
                    lat='{}:{}'.format(minlat - pad, maxlat + pad),
                    lon='{}:{}'.format(minmaxlonpad[0], minmaxlonpad[1]),
                    zoom='{}:{}'.format(zoom, zoom),
                )
                tiles[zoom].update(_required_tiles()[zoom])
        self.write(tiles)

    def prune(self, d=None):
        """
        Prune the tile list, removing tiles which are already present in the directory `d`.

        :param d: Path to tiles directory.
        :return: `int` number of tiles that are missing in `d`.
        """
        d = pathlib.Path(d) if d else self.path.parent
        missing_tiles = collections.defaultdict(list)
        for zoom, tiles in itertools.groupby(self, lambda xyz: xyz[2]):
            for x, y, z in tiles:
                if not d.joinpath(z, x, '{}.png'.format(y)).exists():
                    missing_tiles[z].append((x, y, z))

        if missing_tiles:
            self.write(missing_tiles)
        return sum(len(v) for v in missing_tiles.values())

    def download(self, d=None):
        d = pathlib.Path(d) if d else self.path.parent
        downloadosmtiles(destdir=d, loadtilelist=self.path)

    def write(self, tiles):
        # Note: We handcraft the rather simple yaml format of tilelists, rather than requiring
        # pyyaml.
        yaml = ['---']
        for zoom, tiles in sorted(tiles.items(), key=lambda i: int(i[0])):
            yaml.append('{}:'.format(zoom))
            for tile in tiles:
                yaml.append('  - xyz:')
                yaml.extend(['      - {}'.format(i) for i in tile])
        self.path.write_text('\n'.join(yaml), encoding='utf8')

    def __iter__(self):
        xyz, index = [None, None, None], -1
        for line in self.path.read_text(encoding='utf8').split('\n'):
            line = line.strip()
            if line == '---':
                continue
            if line.startswith('-'):
                if line.endswith('xyz:'):
                    if index > 0:
                        yield tuple(xyz)
                        index = -1
                else:
                    index += 1
                    xyz[index] = line[1:].strip()
        if index > 0:
            yield tuple(xyz)
