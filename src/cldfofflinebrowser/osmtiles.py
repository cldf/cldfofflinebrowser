"""
Use the downloadosmtiles command to manage a map tiles.

See http://manpages.ubuntu.com/manpages/xenial/man1/downloadosmtiles.1p.html
"""
import pathlib
import itertools
import subprocess
import collections

# The following command will be available in Ubuntu, if libgeo-osm-tiles-perl is installed.
CMD = "downloadosmtiles"


def downloadosmtiles(*args, **opts):
    return subprocess.check_call(
        [CMD] + list(args) + ['--{}={}'.format(k, str(v)) for k, v in opts.items()])


class TileList:
    def __init__(self, p):
        subprocess.call([CMD, '-xyz'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.path = pathlib.Path(p)

    def create(self, coords, maxzoom, minzoom=0):
        """
        Write a list of tiles required to fit all coords in the zoom levels from minzoom to maxzoom.

        :param coords: `list` of (lat, lon) pairs.
        :param minzoom: `int` minimal required zoom level
        :param maxzoom: `int` maximal required zoom level
        :return:
        """
        if maxzoom > 12:
            # https://operations.osmfoundation.org/policies/tiles/
            raise ValueError('Maxzoom exceeds level allowed for bulk downloading!')
        lats, lons = list(zip(*coords))
        downloadosmtiles(
            dumptilelist=self.path,
            lat='{}:{}'.format(min(lats), max(lats)),
            lon='{}:{}'.format(min(lons), max(lons)),
            zoom='{}:{}'.format(minzoom, maxzoom),
        )

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
            # Note: We handcraft the rather simple yaml format of tilelists, rather than requiring
            # pyyaml.
            yaml = ['---']
            for zoom, tiles in sorted(missing_tiles.items(), key=lambda i: int(i[0])):
                yaml.append('{}:'.format(zoom))
                for tile in tiles:
                    yaml.append('  - xyz:')
                    yaml.extend(['      - {}'.format(i) for i in tile])
            self.path.write_text('\n'.join(yaml), encoding='utf8')
        return sum(len(v) for v in missing_tiles.values())

    def download(self, d=None):
        d = pathlib.Path(d) if d else self.path.parent
        downloadosmtiles(destdir=d, loadtilelist=self.path)

    def __iter__(self):
        xyz, index = [None, None, None], -1
        for line in self.path.read_text(encoding='utf8').split('\n'):
            line = line.strip()
            if line == '---':
                continue
            if line.startswith('-'):
                if line.endswith('xyz:'):
                    if index > 0:
                        yield xyz
                        index = -1
                else:
                    index += 1
                    xyz[index] = line[1:].strip()
        if index > 0:
            yield xyz
