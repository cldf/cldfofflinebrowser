import pathlib

from cldfofflinebrowser.template import render, render_to_string


def test_render(tmpdir):
    vars = {'title': 'äüöß'}
    render(str(tmpdir), 'index.html', **vars)
    out = pathlib.Path(str(tmpdir)).joinpath('index.html')
    assert out.exists()
    assert out.read_text(encoding='utf8') == render_to_string('index.html', **vars)

    out = out.parent / 'other.html'
    render(out, 'index.html')
    assert out.exists()
