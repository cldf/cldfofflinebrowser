"""
Create an offline browseable version of a CLDF Wordlist.
"""
import sys
import shutil
import pathlib

from pycldf.cli_util import get_dataset, add_dataset
from clldutils.clilib import PathType

import cldfofflinebrowser
from cldfofflinebrowser import osmtiles
from cldfofflinebrowser.template import render_directory
from cldfofflinebrowser import media
from cldfofflinebrowser.create import Data


def register(parser):
    parser.add_argument(
        '--outdir',
        help="Directory in which to create the offline browseable files.",
        default='offline')
    parser.add_argument(
        '--tiles',
        help='Also add map tiles from the mbtiles file specified.',
        type=PathType(type='file'),
        default=None)
    parser.add_argument(
        '--with-audio',
        help="Also download audio files",
        action='store_true',
        default=False)
    parser.add_argument(
        '--include',
        help="Whitespace separated list of parameter IDs",
        type=lambda s: s.split(),
        default=None)
    add_dataset(parser)
    parser.add_argument(
        '--padding',
        default=8,
        help="Padding in degree longitude at zoom level 5 to add to minimal bounding box when "
             "retrieving map tiles.",
        type=int)
    parser.add_argument(
        '--max-zoom',
        default=10,
        help="Maximal zoom level for which to add map tiles (must be < 13)",
        type=int)
    #
    # FIXME: configuration? Name of the media FK column?
    # sorting of markers?
    #


def _recursive_overwrite(src, dest):
    """Copy a folder structure overwriting existing files"""
    if src.is_dir():
        if not dest.exists():
            dest.mkdir(parents=True)
        for f in src.iterdir():
            _recursive_overwrite(f, dest / f.name)
    else:
        shutil.copyfile(str(src), str(dest))


def loggable_progress(things, file=sys.stderr):  # pragma: no cover
    """'Progressbar' that doesn't clog up logs with escape codes.

    Loops over `things` and prints a status update every 10 elements.
    Writes status updates to `file` (standard error by default).

    Yields elements in `things`.
    """
    for index, thing in enumerate(things):
        if (index + 1) % 10 == 0:
            print(index + 1, '....', sep='', end='', file=file, flush=True)
        yield thing
    print('done.', file=file, flush=True)


def run(args):
    cldf = get_dataset(args)

    outdir = pathlib.Path(args.outdir)
    if not outdir.exists():
        outdir.mkdir()

    for sub in ['tiles', 'static']:
        sub = outdir / sub
        if not sub.exists():
            sub.mkdir()

    for p in pathlib.Path(cldfofflinebrowser.__file__).parent.joinpath('static').iterdir():
        shutil.copy(p, outdir / 'static' / p.name)

    # reading the cldf data
    data = Data.from_dataset(cldf, args.include, args.with_audio, args.log)

    # download section
    tiles_outdir = outdir / 'tiles'
    _recursive_overwrite(pathlib.Path(__file__).parent.parent / 'tiles', tiles_outdir)
    if args.tiles:  # pragma: no cover
        osmtiles.download_tiles(
            args.tiles,
            tiles_outdir,
            [(lang['latitude'], lang['longitude']) for lang in data.languages.values()],
            args.max_zoom,
            args.padding,
            args.log)

    download_list = list(data.iter_missing_audio(cldf, outdir))
    if download_list:
        args.log.info('Downloading %s audio files...', len(download_list))
        for target, url in loggable_progress(download_list):
            target.parent.mkdir(exist_ok=True, parents=True)
            media.download(cldf, target, url)

    # create offline browser
    for pid, param_forms in data.iter_forms_by_parameter():
        render_directory(
            outdir,
            'parameter',
            pid,
            data.parameters[pid],
            data.parameter_page_data(param_forms),
            args.max_zoom,
            data.template_context)

    for lid, lang_forms in data.iter_forms_by_language():
        render_directory(
            outdir,
            'language',
            lid,
            data.languages[lid],
            data.language_page_data(lang_forms),
            args.max_zoom,
            data.template_context)

    # render index
    language_data = {
        k: {
            'Name': v['name'],
            'ID': k,
            'latitude': v['latitude'],
            'longitude': v['longitude'],
        }
        for k, v in data.languages.items()}
    data_ = {
        'index': True,
        'languages': language_data,
    }

    render_directory(
        outdir,
        'index',
        None,
        None,
        data_,
        args.max_zoom,
        data.template_context,
        any(p['has_audio'] for p in data.parameters.values()))
