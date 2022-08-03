"""
Use the downloadosmtiles command to manage a map tiles.

See http://manpages.ubuntu.com/manpages/xenial/man1/downloadosmtiles.1p.html
"""
import decimal
import pathlib
import itertools
import subprocess
import collections

__all__ = [
    'CMD', 'TileList',
    'get_bounding_box',
    'get_missing_tiles',
    'download_tiles',
]

# The following command will be available in Ubuntu, if libgeo-osm-tiles-perl is installed.
CMD = "downloadosmtiles"


def _clamp_lat(lat):
    return min(90.0, max(-90.0, lat))


def _wrap_lon(lon):
    while lon < -180.0:
        lon += 360.0
    while lon > 180.0:
        lon -= 360.0
    return lon


def _rel_to_dateline(lon):
    if lon == 0.0:
        return 180.0
    elif lon > 0.0:
        return lon - 180.0
    else:
        return lon + 180.0


def _lon_dist(lon1, lon2):
    if lon2 > lon1:
        return lon2 - lon1
    else:
        return 360.0 + lon2 - lon1


def get_bounding_box(coords):
    if not coords:
        raise ValueError('Cannot create bounding box without any coordinates.')

    north = _clamp_lat(max(lat for lat, _ in coords))
    south = _clamp_lat(min(lat for lat, _ in coords))

    normalised_lons = [_wrap_lon(lon) for _, lon in coords]
    west_of_null = min(normalised_lons)
    east_of_null = max(normalised_lons)

    by_dateline_distance = sorted(normalised_lons, key=_rel_to_dateline)
    west_of_datel = by_dateline_distance[0]
    east_of_datel = by_dateline_distance[-1]

    if west_of_null < 0.0 and east_of_null < 0.0:
        return north, west_of_null, south, east_of_null
    elif west_of_null > 0.0 and east_of_null > 0.0:
        return north, west_of_null, south, east_of_null
    elif _lon_dist(west_of_datel, east_of_datel) < _lon_dist(west_of_null, east_of_null):
        return north, west_of_datel, south, east_of_datel
    else:
        return north, west_of_null, south, east_of_null


def get_missing_tiles(
    minzoom, maxzoom, min_lat, min_lon, max_lat, max_lon, padding
):
    # TODO
    return None


def download_tiles(missing_tiles):
    # TODO
    return None


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
