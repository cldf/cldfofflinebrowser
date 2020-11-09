import json
import pathlib

from jinja2 import Environment, PackageLoader, select_autoescape

import cldfofflinebrowser

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
