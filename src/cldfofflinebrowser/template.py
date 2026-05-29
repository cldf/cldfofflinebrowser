import json
import pathlib
from typing import Literal, Any, Optional

from jinja2 import Environment, PackageLoader, select_autoescape

import cldfofflinebrowser

__all__ = ['render_to_string', 'render']

env = Environment(
    loader=PackageLoader(cldfofflinebrowser.__name__, 'templates'),
    autoescape=select_autoescape([])
)
env.filters.update(jsondumps=json.dumps, len=lambda v: len(v))


def render_to_string(template, **vars):
    return env.get_template(template).render(**vars)


def render(out, template, **vars):
    out = pathlib.Path(out)
    if out.is_dir():
        out = out / template
    out.write_text(render_to_string(template, **vars), encoding='utf8')


def render_directory(
        outdir: pathlib.Path,
        type_: Literal['language', 'parameter', 'index'],
        id_: Optional[str],
        obj: Optional[dict[str, Any]],
        json_data: dict[str, Any],
        max_zoom,
        tmpl_context,
        has_any_audio: bool = False,
):
    if type_ == 'index':
        pout = outdir
    else:
        pout = outdir / f'{type_}-{id_}'
    if not pout.exists():
        pout.mkdir()
    render(
        pout,
        'data.js',
        data=json_data,
        options={'minZoom': 0, 'maxZoom': max_zoom})
    context = {'index': type_ == 'index', 'data': json_data}
    if type_ == 'index':
        context['has_any_audio'] = has_any_audio
    else:
        context[type_] = obj
    context.update(tmpl_context)
    render(pout / 'index.html', f'{type_}.html', **context)
