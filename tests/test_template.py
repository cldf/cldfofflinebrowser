import pathlib

from cldfofflinebrowser.template import _render


def test_render(tmpdir):
    vars = {'title': 'äüöß'}
    _render(str(tmpdir), 'index.html', **vars)
    out = pathlib.Path(str(tmpdir)).joinpath('index.html')
    assert out.exists()

    out = out.parent / 'other.html'
    _render(out, 'index.html')
    assert out.exists()
