import pathlib

import unittest
import pytest

from cldfofflinebrowser.osmtiles import *

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
        assert get_bounding_box(coords) == (4.32, -114.77, -26.75, -92.62)

    def test_eastern_hemisphere(self):
        coords = [
            (-17.79, 144.70),
            (-43.28, 166.10),
            (-13.26, 151.11),
            (-14.96, 149.92),
            (10.10, 157.33)]
        assert get_bounding_box(coords) == (10.10, 144.70, -43.28, 166.10)

    def test_at_null_meridian(self):
        coords = [
            (10.06, 2.36),
            (33.60, 6.11),
            (-0.31, -10.85),
            (-10.45, -17.72),
            (38.53, 0.40)]
        assert get_bounding_box(coords) == (38.53, -17.72, -10.45, -6.11)

    def test_at_date_line(self):
        coords = [
            (-4.15, 161.73),
            (15.30, -169.55),
            (-22.83, -169.80),
            (-21.13, 172.26),
            (10.87, -151.64)]
        assert get_bounding_box(coords) == (15.30, 161.73, -22.83, -151.64)


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
    tl = TileList(pathlib.Path(str(tmpdir)) / 'tiles.yaml')

    with pytest.raises(ValueError):
        tl.create([(1, 1), (2, 2)], 50)

    tl.create([(1, 1), (2, 2)], 6)
    assert tl.path.exists()
    assert tl.prune() == 2
    tl.download(pathlib.Path(str(tmpdir)))
    assert tl.prune() == 0
