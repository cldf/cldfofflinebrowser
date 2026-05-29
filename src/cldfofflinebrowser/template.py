"""
Functionality to render Jinja2 templates.
"""
import json
import pathlib
from typing import Literal, Any, Optional

from jinja2 import Environment, PackageLoader, select_autoescape

import cldfofflinebrowser

__all__ = ['render_directory']

env = Environment(
    loader=PackageLoader(cldfofflinebrowser.__name__, 'templates'),
    autoescape=select_autoescape([])
)
env.filters.update(jsondumps=json.dumps, len=len)


def _render(out, template, **vars_):
    out = pathlib.Path(out)
    if out.is_dir():
        out = out / template
    out.write_text(env.get_template(template).render(**vars_), encoding='utf8')


def render_directory(  # pylint: disable=R0913,R0917
        outdir: pathlib.Path,
        type_: Literal['language', 'parameter', 'index'],
        id_: Optional[str],
        obj: Optional[dict[str, Any]],
        json_data: dict[str, Any],
        max_zoom,
        tmpl_context,
        has_any_audio: bool = False,
):
    """
    Create a directory for the offline browser, containing the data for one language, one parameter
    or the index.
    """
    if type_ == 'index':
        pout = outdir
    else:
        pout = outdir / f'{type_}-{id_}'
    if not pout.exists():
        pout.mkdir()
    _render(
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
    _render(pout / 'index.html', f'{type_}.html', **context)
