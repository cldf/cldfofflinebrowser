"""
Use the downloadosmtiles command to manage a map tiles.

See http://manpages.ubuntu.com/manpages/xenial/man1/downloadosmtiles.1p.html
"""
import math
import random
import sys
from urllib.request import Request, urlopen

__all__ = [
    'get_bounding_box',
    'get_area_tiles',
    'download_tiles',
]


def clamp_latitude(lat):
    # osm's mercator projections only go up to ±85° anyways
    return min(85.0, max(-85.0, lat))


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


def download_tiles(path, tile_list, log=None):  # pragma: nocover
    todo = [
        (x, y, zoom)
        for x, y, zoom in tile_list
        if not get_tile_path(path, x, y, zoom).exists()
        and zoom <= 12]

    if log is not None:
        if len(todo) == len(tile_list):
            log.info('Downloading {} tiles.'.format(len(todo)))
        elif len(todo):
            log.info(
                '{} tiles are already there.  '
                "Downloading {} tiles.".format(
                    len(tile_list) - len(todo), len(todo)))
        else:
            log.info(
                'All {} tiles are already there.'
                '  Nothing to do.'.format(len(tile_list)))

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
