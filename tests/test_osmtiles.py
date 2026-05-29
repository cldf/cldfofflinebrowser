import logging
import pathlib
import contextlib

import pytest

from cldfofflinebrowser import osmtiles as o, osmtiles


@pytest.mark.parametrize(
    'in_,out_',
    [
        (225.0, -135.0),
        (315.0, -45.0),
        (495.0, 135.0),
        (585.0, -135.0),
        (-225.0, 135.0),
        (-315.0, 45.0),
        (-495.0, -135.0),
        (-585.0, 135.0),
    ]
)
def test_longitude_wrapping(in_, out_):
    assert o.wrap_longitude(in_) == out_


@pytest.mark.parametrize(
    'coords,expected',
    [
        ([
            (4.32, -92.62),
            (-3.29, -107.49),
            (-20.55, -114.77),
            (-12.54, -109.42),
            (-26.75, -102.79)],
         (4.32, -114.77, -26.75, -92.62)),
        ([
            (-17.79, 144.70),
            (-43.28, 166.10),
            (-13.26, 151.11),
            (-14.96, 149.92),
            (10.10, 157.33)], (10.10, 144.70, -43.28, 166.10)),
        ([
            (10.06, 2.36),
            (33.60, 6.11),
            (-0.31, -10.85),
            (-10.45, -17.72),
            (38.53, 0.40)], (38.53, -17.72, -10.45, 6.11)),
        ([
            (-4.15, 161.73),
            (15.30, -169.55),
            (-22.83, -169.80),
            (-21.13, 172.26),
            (10.87, -151.64)], (15.30, 161.73, -22.83, -151.64)),
        ([(0.0, 0.0), (1.0, 1.0)], (1.0, 0.0, 0.0, 1.0)),
        ([(0.0, 0.0), (-1.0, 1.0)], (0.0, 0.0, -1.0, 1.0)),
        ([(0.0, 0.0), (1.0, -1.0)], (1.0, -1.0, 0.0, 0.0)),
        ([(0.0, 0.0), (-1.0, -1.0)], (0.0, -1.0, -1.0, 0.0)),
        # no idea if `date island` is a real term btw (<_<)"
        ([(0.0, 180.0), (1.0, -179.0)], (1.0, 180.0, 0.0, -179.0)),
        ([(0.0, 180.0), (-1.0, -179.0)], (0.0, 180.0, -1.0, -179.0)),
        ([(0.0, 180.0), (1.0, 179.0)], (1.0, 179.0, 0.0, 180.0)),
        ([(0.0, 180.0), (-1.0, 179.0)], (0.0, 179.0, -1.0, 180.0)),
        # mathematically speaking `date island` has two names...
        ([(0.0, -180.0), (1.0, -179.0)], (1.0, -180.0, 0.0, -179.0)),
        ([(0.0, -180.0), (-1.0, -179.0)], (0.0, -180.0, -1.0, -179.0)),
        ([(0.0, -180.0), (1.0, 179.0)], (1.0, 179.0, 0.0, -180.0)),
        ([(0.0, -180.0), (-1.0, 179.0)], (0.0, 179.0, -1.0, -180.0)),
    ]
)
def test_get_bounding_box(coords, expected):
    assert o.get_bounding_box(coords) == expected


def test_no_coordinates():
    with pytest.raises(ValueError):
        o.get_bounding_box([])


@pytest.mark.parametrize(
    'lat,lon,xy',
    [
        # just_checking_the_basics_null_meridian
        (5.615985819155334, -5.625, (31, 31)),
        (5.615985819155334, 5.625, (33, 31)),
        (-5.615985819155334, -5.625, (31, 33)),
        (-5.615985819155334, 5.625, (33, 33)),
        # just_checking_the_basics_dateline(self):
        (5.615985819155334, 174.375, (63, 31)),
        (5.615985819155334, -174.375, (1, 31)),
        (-5.615985819155334, 174.375, (63, 33)),
        (-5.615985819155334, -174.375, (1, 33)),
    ]
)
def test_Tile_from_latlon(lat, lon, xy):
    t = o.Tile.from_latlon(lat, lon, 6)
    assert (t.x, t.y) == xy


def test_get_tile_list(mocker, tmpdir):
    n, w, s, e = o.get_bounding_box([(1.0, -1.0), (-1.0, 1.0)])

    with pytest.raises(ValueError):
        _ = o.get_tile_list(0, 50, n, w, s, e, 10)
    tile_list = o.get_tile_list(0, 1, n, w, s, e, 10)
    assert len(tile_list) == 5


def test_Tile():
    assert str(o.Tile(1, 2, 3).path(pathlib.Path('tiles'))) == 'tiles/3/1/2.png'


@pytest.mark.parametrize(
    'n,w,s,e,zoom,expected,msg',
    [
        (5.615985819155334, -5.625, -5.615985819155334, 5.625, 0,
         [(0, 0)], 'null_meridian_at_zoom_0'),
        (5.615985819155334, 174.375, -5.615985819155334, -174.375, 0,
         [(0, 0)], 'dateline_at_zoom_0'),
        (5.615985819155334, -5.625, -5.615985819155334, 5.625, 1,
         [(0, 0), (0, 1), (1, 0), (1, 1)], 'null_meridian_at_zoom_1'),
        (5.615985819155334, 174.375, -5.615985819155334, -174.375, 1,
         [(1, 0), (1, 1), (0, 0), (0, 1)], 'dateline_at_zoom_1'),
        (5.615985819155334, -5.625, -5.615985819155334, 5.625, 2,
         [(1, 1), (1, 2), (2, 1), (2, 2)], 'null_meridian_at_zoom_2'),
        (5.615985819155334, 174.375, -5.615985819155334, -174.375, 2,
         [(3, 1), (3, 2), (0, 1), (0, 2)], 'dateline_at_zoom_2'),
        (5.615985819155334, -5.625, -5.615985819155334, 5.625, 3,
         [(3, 3), (3, 4), (4, 3), (4, 4)], 'null_meridian_at_zoom_3'),
        (5.615985819155334, 174.375, -5.615985819155334, -174.375, 3,
         [(7, 3), (7, 4), (0, 3), (0, 4)], 'dateline_at_zoom_3'),
        (5.615985819155334, -5.625, -5.615985819155334, 5.625, 7,
         # we get a 5x5 area because coord (5.61°S, 5.625°E) is right at the edge
         # of tile [66, 66] and tile ranges are inclusive
         [
            (62, 62), (62, 63), (62, 64), (62, 65), (62, 66),
            (63, 62), (63, 63), (63, 64), (63, 65), (63, 66),
            (64, 62), (64, 63), (64, 64), (64, 65), (64, 66),
            (65, 62), (65, 63), (65, 64), (65, 65), (65, 66),
            (66, 62), (66, 63), (66, 64), (66, 65), (66, 66),
        ], 'null_meridian_at_zoom_7'),
        (5.615985819155334, 174.375, -5.615985819155334, -174.375, 7,
         # we get a 5x5 area because coord (5.61°S, 174.375°W) is right at the
         # edge of tile [2, 66] and tile ranges are inclusive
         [
            (126, 62), (126, 63), (126, 64), (126, 65), (126, 66),
            (127, 62), (127, 63), (127, 64), (127, 65), (127, 66),
            (0, 62), (0, 63), (0, 64), (0, 65), (0, 66),
            (1, 62), (1, 63), (1, 64), (1, 65), (1, 66),
            (2, 62), (2, 63), (2, 64), (2, 65), (2, 66),
        ], 'dateline_at_zoom_7'),
]
)
def test_iter_area_tiles(n: float, w: float, s: float, e: float, zoom: int, expected, msg):
    assert [(t.x, t.y) for t in o.iter_area_tiles(n, w, s, e, zoom)] == expected, msg


def test_download_tiles(tmp_path, mocker, caplog):
    def urlretrieve(_, p):
        p.write_text('x', encoding='utf8')

    @contextlib.contextmanager
    def tileserver(_):
        class TS:
            def url(self, _):
                return None
        yield TS()

    mocker.patch('cldfofflinebrowser.osmtiles.urlretrieve', urlretrieve)
    mocker.patch('cldfofflinebrowser.osmtiles.TileServer', tileserver)

    with caplog.at_level(logging.INFO):
        res = osmtiles.download_tiles(
            tmp_path,
            tmp_path,
            [(12.1, 23.3)], 3, 1, logging.getLogger(__name__))
        assert '4 out of 4' in caplog.records[0].message
        assert res == 4, 'one tile per zoom level'
    res = osmtiles.download_tiles(tmp_path, tmp_path, [(12.1, 23.3)], 3, 1, None)
    assert res == 0, 'all already there'


def test_TileServer(tmp_path):
    from urllib.request import urlretrieve

    class TS(osmtiles.TileServer):
        @property
        def command(self):
            return [
                'python3', '-m', 'http.server',
                str(self.port), '--bind', '127.0.0.1', '--directory', str(self.mbtiles)]

    tmp_path.joinpath('index.html').write_text('<html>')
    with TS(tmp_path, 8888) as ts:
        index = tmp_path / 'test.html'
        urlretrieve('http://localhost:8888/index.html', index)
        assert index.exists()
        assert all(str(x) in ts.url(osmtiles.Tile(4, 5, 6)) for x in {4, 5, 6})

        with pytest.raises(ValueError):
            with TS(tmp_path, 8888):
                pass  # pragma: no cover
