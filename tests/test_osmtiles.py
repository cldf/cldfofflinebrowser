import pathlib

import pytest

from cldfofflinebrowser.osmtiles import *

TILELIST = """
---
1:
  - xyz:
      - 1
      - 1
      - 1
2:
  - xyz:
      - 3
      - 2
      - 2
"""
FILES = ['1/1/1.png', '2/3/2.png']


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

    tl.create([(1, 1), (2, 2)], 5)
    assert tl.path.exists()
    assert tl.prune() == 2
    tl.download(pathlib.Path(str(tmpdir)))
    assert tl.prune() == 0
