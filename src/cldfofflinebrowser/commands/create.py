"""
Create an offline browseable version of a CLDF Wordlist.
"""
import shutil
import pathlib
import itertools
import mimetypes
import collections

from tqdm import tqdm
from cldfbench.cli_util import add_dataset_spec, get_dataset

import cldfofflinebrowser
from cldfofflinebrowser import osmtiles
from cldfofflinebrowser.template import render
from cldfofflinebrowser import media


def register(parser):
    parser.add_argument(
        '--outdir',
        help="Directory in which to create the offline browseable files.",
        default='offline')
    parser.add_argument(
        '--with-tiles',
        help="Also download map tiles (requires {})".format(osmtiles.CMD),
        action='store_true',
        default=False)
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
    add_dataset_spec(parser)
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


def run(args):
    ds = get_dataset(args)
    cldf = ds.cldf_reader()
    # We expect a list of audio files in a table "media.csv", with a column "mimetype".
    audio, form2audio = media.read_media_files(
        cldf, filter=lambda r: r['mimetype'].startswith('audio/'))
    title_ = cldf.properties['dc:title'].replace('"', '”')
    title = '<div class="truncate">{}.</div>'.format(title_)
    title_tooltip = title_

    outdir = pathlib.Path(args.outdir)
    if not outdir.exists():
        outdir.mkdir()

    for sub in ['tiles', 'static']:
        sub = outdir / sub
        if not sub.exists():
            sub.mkdir()

    for p in pathlib.Path(cldfofflinebrowser.__file__).parent.joinpath('static').iterdir():
        shutil.copy(str(p), str(outdir / 'static' / p.name))

    parameters = {}
    for p in cldf.iter_rows('ParameterTable', 'id', 'name'):
        if (args.include is None) or (p['id'] in args.include):
            p.update(representation=set(), has_audio=False)
            parameters[p['id']] = p

    languages, coords = {}, []
    for p in cldf.iter_rows('LanguageTable', 'latitude', 'longitude', 'id', 'name'):
        for c in ['Latitude', 'Longitude']:
            if c in p:
                del p[c]
        if p['latitude'] is None or p['longitude'] is None:
            continue
        coords.append((p['latitude'], p['longitude']))
        p['latitude'] = float(p['latitude'])
        p['longitude'] = float(p['longitude'])
        languages[p['ID']] = p

    tiles_outdir = outdir / 'tiles'
    _recursive_overwrite(pathlib.Path(__file__).parent.parent / 'tiles', tiles_outdir)
    if args.with_tiles:
        # NOTE: coords contains all coordinates
        # TODO: (check if those are actually numbers)
        # FIXME hard-coded values
        missing_tiles = osmtiles.get_missing_tiles(
            minzoom=0, maxzoom=10,
            min_lat=-45.0, max_lat=45.0,
            min_lon=-45.0, max_lon=45.0)
        if missing_tiles:
            args.log.info('Downloading {} map tiles'.format(len(missing_tiles)))
            osmtiles.download_tiles(missing_tiles)
        else:
            args.log.info('All map tiles are there; nothing to download.')

    #
    # FIXME: looping over FormTable means we only support Wordlist!
    #
    for pid, forms in tqdm(itertools.groupby(
        sorted(
            cldf.iter_rows('FormTable', 'id', 'languageReference', 'parameterReference', 'form'),
            key=lambda r: (r['parameterReference'], r['id'])),
        lambda r: r['Parameter_ID'],
    )):
        if args.include and (pid not in args.include):
            continue
        data = {
            'languages': {},
            'forms': collections.defaultdict(dict),
        }
        pout = outdir / 'parameter-{}'.format(pid)
        if not pout.exists():
            pout.mkdir()

        for form in forms:
            if form['languageReference'] not in languages:
                continue
            data['forms'][form['languageReference']] = {
                'form': form['form'],
                'audio': None,
            }
            data['languages'][form['languageReference']] = languages[form['languageReference']]
            parameters[pid]['representation'].add(form['languageReference'])
            if 'Audio_Files' in form:
                # Audio files may either be linked via a list-valued foreign key column
                # "Audio_Files" ...
                audio_files = [audio[aid] for aid in form['Audio_Files'] if aid in audio]
            else:
                # ... or via a formReference in the media table:
                audio_files = form2audio.get(form['id'], [])
            audio_file = media.get_best_audio(audio_files)
            if audio_file and args.with_audio:
                suffix = media.PREFERRED_AUDIO.get(audio_file['mimetype']) \
                    or mimetypes.guess_extension(audio_file['mimetype']) \
                    or '.bin'
                data['forms'][form['languageReference']]['audio'] = {
                    'name': media.download(
                        cldf,
                        audio_file,
                        pout,
                        '{}{}'.format(form['languageReference'], suffix)).name,
                    'mimetype': audio_file['mimetype'],
                }
                parameters[pid]['has_audio'] = True

        render(
            pout,
            'data.js',
            data=data,
            options={'minZoom': 0, 'maxZoom': args.max_zoom})
        render(
            pout / 'index.html',
            'parameter.html',
            parameter=parameters[pid],
            index=False,
            data=data,
            parameters=parameters.items(),
            title_tooltip=title_tooltip,
            title=title,
        )

    for c in ['forms', 'languages']:
        if c in data:
            del data[c]
    data['index'] = True
    data['languages'] = {}
    for k, v in languages.items():
        data['languages'][k] = {
            'Name': v['Name'],
            'latitude': v['latitude'],
            'longitude': v['longitude'],
        }

    render(
        outdir,
        'data.js',
        data=data,
        options={'minZoom': 0, 'maxZoom': args.max_zoom})
    render(
        outdir,
        'index.html',
        parameters=parameters.items(),
        index=True,
        data=data,
        has_any_audio=any(p['has_audio'] for p in parameters.values()),
        title_tooltip=title_tooltip,
        title=title,
    )
