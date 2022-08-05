import pathlib

import unittest
import pytest

from cldfofflinebrowser import osmtiles as o

TILELIST = """
---
5:
  - xyz:
      - 1
      - 1
      - 5
6:
  - xyz:
      - 3
      - 2
      - 6
"""
FILES = ['5/1/1.png', '6/3/2.png']


class BoundingBox(unittest.TestCase):
    def test_western_hemisphere(self):
        coords = [
            (4.32, -92.62),
            (-3.29, -107.49),
            (-20.55, -114.77),
            (-12.54, -109.42),
            (-26.75, -102.79)]
        assert o.get_bounding_box(coords) == (4.32, -114.77, -26.75, -92.62)

    def test_eastern_hemisphere(self):
        coords = [
            (-17.79, 144.70),
            (-43.28, 166.10),
            (-13.26, 151.11),
            (-14.96, 149.92),
            (10.10, 157.33)]
        assert o.get_bounding_box(coords) == (10.10, 144.70, -43.28, 166.10)

    def test_at_null_meridian(self):
        coords = [
            (10.06, 2.36),
            (33.60, 6.11),
            (-0.31, -10.85),
            (-10.45, -17.72),
            (38.53, 0.40)]
        assert o.get_bounding_box(coords) == (38.53, -17.72, -10.45, 6.11)

    def test_at_date_line(self):
        coords = [
            (-4.15, 161.73),
            (15.30, -169.55),
            (-22.83, -169.80),
            (-21.13, 172.26),
            (10.87, -151.64)]
        assert o.get_bounding_box(coords) == (15.30, 161.73, -22.83, -151.64)

    def test_no_coordinates(self):
        with self.assertRaises(ValueError):
            o.get_bounding_box([])

    def test_null_island(self):
        assert o.get_bounding_box([(0.0, 0.0), (1.0, 1.0)]) == (1.0, 0.0, 0.0, 1.0)
        assert o.get_bounding_box([(0.0, 0.0), (-1.0, 1.0)]) == (0.0, 0.0, -1.0, 1.0)
        assert o.get_bounding_box([(0.0, 0.0), (1.0, -1.0)]) == (1.0, -1.0, 0.0, 0.0)
        assert o.get_bounding_box([(0.0, 0.0), (-1.0, -1.0)]) == (0.0, -1.0, -1.0, 0.0)

    def test_date_island(self):
        # no idea if `date island` is a real term btw (<_<)"
        assert o.get_bounding_box([(0.0, 180.0), (1.0, -179.0)]) == (1.0, 180.0, 0.0, -179.0)
        assert o.get_bounding_box([(0.0, 180.0), (-1.0, -179.0)]) == (0.0, 180.0, -1.0, -179.0)
        assert o.get_bounding_box([(0.0, 180.0), (1.0, 179.0)]) == (1.0, 179.0, 0.0, 180.0)
        assert o.get_bounding_box([(0.0, 180.0), (-1.0, 179.0)]) == (0.0, 179.0, -1.0, 180.0)
        # mathematically speaking `date island` has two names...
        assert o.get_bounding_box([(0.0, -180.0), (1.0, -179.0)]) == (1.0, -180.0, 0.0, -179.0)
        assert o.get_bounding_box([(0.0, -180.0), (-1.0, -179.0)]) == (0.0, -180.0, -1.0, -179.0)
        assert o.get_bounding_box([(0.0, -180.0), (1.0, 179.0)]) == (1.0, 179.0, 0.0, -180.0)
        assert o.get_bounding_box([(0.0, -180.0), (-1.0, 179.0)]) == (0.0, 179.0, -1.0, -180.0)


class BoxToTiles(unittest.TestCase):
    def test_just_checking_the_basics_null_meridian(self):
        nw = (5.615985819155334, -5.625)
        ne = (5.615985819155334, 5.625)
        sw = (-5.615985819155334, -5.625)
        se = (-5.615985819155334, 5.625)
        assert o.deg2num(nw[0], nw[1], 6) == (31, 31)
        assert o.deg2num(ne[0], ne[1], 6) == (33, 31)
        assert o.deg2num(sw[0], sw[1], 6) == (31, 33)
        assert o.deg2num(se[0], se[1], 6) == (33, 33)

    def test_just_checking_the_basics_dateline(self):
        nw = (5.615985819155334, 174.375)
        ne = (5.615985819155334, -174.375)
        sw = (-5.615985819155334, 174.375)
        se = (-5.615985819155334, -174.375)
        assert o.deg2num(nw[0], nw[1], 6) == (63, 31)
        assert o.deg2num(ne[0], ne[1], 6) == (1, 31)
        assert o.deg2num(sw[0], sw[1], 6) == (63, 33)
        assert o.deg2num(se[0], se[1], 6) == (1, 33)

    def test_null_meridian_at_zoom_0(self):
        n, w, s, e = (5.615985819155334, -5.625, -5.615985819155334, 5.625)
        result = list(o.get_area_tiles(n, w, s, e, 0))
        expected = [(0, 0)]
        self.assertEqual(result, expected)

    def test_dateline_at_zoom_0(self):
        n, w, s, e = (5.615985819155334, 174.375, -5.615985819155334, -174.375)
        result = list(o.get_area_tiles(n, w, s, e, 0))
        expected = [(0, 0)]
        self.assertEqual(result, expected)

    def test_null_meridian_at_zoom_1(self):
        n, w, s, e = (5.615985819155334, -5.625, -5.615985819155334, 5.625)
        result = list(o.get_area_tiles(n, w, s, e, 1))
        expected = [(0, 0), (0, 1), (1, 0), (1, 1)]
        self.assertEqual(result, expected)

    def test_dateline_at_zoom_1(self):
        n, w, s, e = (5.615985819155334, 174.375, -5.615985819155334, -174.375)
        result = list(o.get_area_tiles(n, w, s, e, 1))
        expected = [(1, 0), (1, 1), (0, 0), (0, 1)]
        self.assertEqual(result, expected)

    def test_null_meridian_at_zoom_2(self):
        n, w, s, e = (5.615985819155334, -5.625, -5.615985819155334, 5.625)
        result = list(o.get_area_tiles(n, w, s, e, 2))
        expected = [(1, 1), (1, 2), (2, 1), (2, 2)]
        self.assertEqual(result, expected)

    def test_dateline_at_zoom_2(self):
        n, w, s, e = (5.615985819155334, 174.375, -5.615985819155334, -174.375)
        result = list(o.get_area_tiles(n, w, s, e, 2))
        expected = [(3, 1), (3, 2), (0, 1), (0, 2)]
        self.assertEqual(result, expected)

    def test_null_meridian_at_zoom_3(self):
        n, w, s, e = (5.615985819155334, -5.625, -5.615985819155334, 5.625)
        result = list(o.get_area_tiles(n, w, s, e, 3))
        expected = [(3, 3), (3, 4), (4, 3), (4, 4)]
        self.assertEqual(result, expected)

    def test_dateline_at_zoom_3(self):
        n, w, s, e = (5.615985819155334, 174.375, -5.615985819155334, -174.375)
        result = list(o.get_area_tiles(n, w, s, e, 3))
        expected = [(7, 3), (7, 4), (0, 3), (0, 4)]
        self.assertEqual(result, expected)

    def test_null_meridian_at_zoom_7(self):
        n, w, s, e = (5.615985819155334, -5.625, -5.615985819155334, 5.625)
        result = list(o.get_area_tiles(n, w, s, e, 7))
        # we get a 5x5 area because coord (5.61°S, 5.625°E) is right at the edge
        # of tile [66, 66] and tile ranges are inclusive
        expected = [
            (62, 62), (62, 63), (62, 64), (62, 65), (62, 66),
            (63, 62), (63, 63), (63, 64), (63, 65), (63, 66),
            (64, 62), (64, 63), (64, 64), (64, 65), (64, 66),
            (65, 62), (65, 63), (65, 64), (65, 65), (65, 66),
            (66, 62), (66, 63), (66, 64), (66, 65), (66, 66),
        ]
        self.assertEqual(result, expected)

    def test_dateline_at_zoom_7(self):
        n, w, s, e = (5.615985819155334, 174.375, -5.615985819155334, -174.375)
        result = list(o.get_area_tiles(n, w, s, e, 7))
        # we get a 5x5 area because coord (5.61°S, 174.375°W) is right at the
        # edge of tile [2, 66] and tile ranges are inclusive
        expected = [
            (126, 62), (126, 63), (126, 64), (126, 65), (126, 66),
            (127, 62), (127, 63), (127, 64), (127, 65), (127, 66),
            (0, 62), (0, 63), (0, 64), (0, 65), (0, 66),
            (1, 62), (1, 63), (1, 64), (1, 65), (1, 66),
            (2, 62), (2, 63), (2, 64), (2, 65), (2, 66),
        ]
        self.assertEqual(result, expected)


def test_TileList(mocker, tmpdir):
    class subprocess(mocker.Mock):
        def check_call(self, args, **kw):
            for arg in args:
                if arg.startswith('--dumptilelist'):
                    pathlib.Path(arg.split('=')[1]).write_text(TILELIST, encoding='utf8')
                    break
                if arg.startswith('--destdir'):
                    for f in FILES:
                        f = pathlib.Path(arg.split('=')[1]).joinpath(f)
                        f.parent.mkdir(parents=True)
                        f.write_text(' ', encoding='utf8')
                    break

    mocker.patch('cldfofflinebrowser.osmtiles.subprocess', subprocess())
    tl = o.TileList(pathlib.Path(str(tmpdir)) / 'tiles.yaml')

    with pytest.raises(ValueError):
        tl.create([(1, 1), (2, 2)], 50)

    tl.create([(1, 1), (2, 2)], 6)
    assert tl.path.exists()
    assert tl.prune() == 2
    tl.download(pathlib.Path(str(tmpdir)))
    assert tl.prune() == 0
