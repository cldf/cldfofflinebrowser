"""
Create an offline browseable version of a CLDF Wordlist.
"""
import decimal
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
        help='Also download map tiles',
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

    # reading the cldf data

    languages = {
        lang['id']: lang
        for lang in cldf.iter_rows(
            'LanguageTable', 'latitude', 'longitude', 'id', 'name')
        if lang['latitude'] is not None and lang['longitude'] is not None}
    # Python's json library can't deal with decimal.Decimal's
    languages = {
        lid: {
            k: float(v) if isinstance(v, decimal.Decimal) else v
            for k, v in lang.items()
            if k not in ('Latitude', 'Longitude')}
        for lid, lang in languages.items()}

    parameters = {
        param['id']: {
            'id': param['id'],
            'name': param['name'],
            'representation': set(),
            'has_audio': False,
        }
        for param in cldf.iter_rows('ParameterTable', 'id', 'name')
        if args.include is None or param['id'] in args.include}

    forms = {
        form['id']: form
        for form in cldf.iter_rows(
            'FormTable', 'id', 'languageReference', 'parameterReference', 'form')}

    if not args.with_audio:
        audio = {}
        form2audio = {}
    else:
        # We expect a list of audio files in a table "media.csv", with a column "mimetype".
        # TODO maybe check for MediaTable component first, then fall back
        # to `media.csv` file name
        audio = {
            row['ID']: row
            for row in cldf['media.csv']
            if row['mimetype'].startswith('audio/')}

        form2audio = collections.defaultdict(list)

        # look for form references in the media table
        form_id_field = (
            cldf.get(('media.csv', 'formReference'))
            or cldf.get(('media.csv', 'Form_ID')))
        if form_id_field:
            for audio_file in audio.values():
                fid = audio_file.get(form_id_field.name)
                if not fid:
                    continue
                elif isinstance(fid, list):
                    form2audio[fid].extend(audio_file['ID'])
                else:
                    form2audio[fid].append(audio_file['ID'])

        # look for media references in the form table
        audio_id_field = (
            cldf.get(('FormTable', 'mediaReference'))
            or cldf.get(('FormTable', 'Audio_Files')))
        if audio_id_field:
            for form in forms.values():
                audio_ids = form.get(audio_id_field.name)
                if not audio_ids:
                    continue
                elif isinstance(audio_ids, list):
                    form2audio[form['id']].extend(audio_ids)
                else:
                    form2audio[form['id']].append(audio_ids)

        form2audio = {
            fid: media.get_best_audio(
                [audio[mid] for mid in mids if audio.get(mid)])
            for fid, mids in form2audio.items()}
        form2audio = {
            fid: audio_file['ID']
            for fid, audio_file in form2audio.items()
            if audio_file is not None}

    # tell parameter table about languages with values
    for form in forms.values():
        pid = form.get('parameterReference')
        lid = form.get('languageReference')
        if pid in parameters and lid in languages:
            parameters[pid]['representation'].add(lid)

    # tell the parameter table about audio files
    for fid in form2audio:
        pid = forms[fid].get('parameterReference')
        if pid in parameters:
            parameters[pid]['has_audio'] = True

    # download section

    tiles_outdir = outdir / 'tiles'
    _recursive_overwrite(pathlib.Path(__file__).parent.parent / 'tiles', tiles_outdir)
    if args.with_tiles:
        north, west, south, east = osmtiles.get_bounding_box([
            (lang['latitude'], lang['longitude'])
            for lang in languages.values()])
        tile_list = osmtiles.get_tile_list(
            minzoom=0, maxzoom=args.max_zoom,
            north=north, west=west, south=south, east=east,
            padding=args.padding)
        if tile_list:
            osmtiles.download_tiles(tiles_outdir, tile_list, args.log)

    for fid, aid in form2audio.items():
        pid = forms[fid].get('parameterReference')
        lid = forms[fid].get('languageReference')
        if pid not in parameters:
            continue
        audio_file = audio[aid]

        suffix = media.PREFERRED_AUDIO.get(audio_file['mimetype']) \
            or mimetypes.guess_extension(audio_file['mimetype']) \
            or '.bin'
        basename = '{}{}'.format(lid, suffix)
        dirname = outdir / 'parameter-{}'.format(pid)
        if not dirname.exists():
            dirname.mkdir()

        audio_file['file-path'] = media.download(
            cldf, audio_file, dirname, basename)

    # create offline browser

    #
    # FIXME: looping over FormTable means we only support Wordlist!
    #
    for pid, param_forms in itertools.groupby(
        sorted(forms.values(), key=lambda r: (r['parameterReference'], r['id'])),
        lambda r: r['parameterReference'],
    ):
        if args.include and (pid not in args.include):
            continue
        data = {
            'languages': {},
            'forms': collections.defaultdict(dict),
        }

        for form in param_forms:
            if form['languageReference'] not in languages:
                continue
            data['forms'][form['languageReference']] = {
                'form': form['form'],
                'audio': None,
            }
            data['languages'][form['languageReference']] = languages[form['languageReference']]
            if form['id'] in form2audio:
                audio_file = audio[form2audio[form['id']]]
                data['forms'][form['languageReference']]['audio'] = {
                    'name': audio_file['file-path'].name,
                    'mimetype': audio_file['mimetype'],
                }

        pout = outdir / 'parameter-{}'.format(pid)
        if not pout.exists():
            pout.mkdir()

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
