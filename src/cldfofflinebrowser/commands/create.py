"""
Create an offline browseable version of a CLDF Wordlist.
"""
import decimal
import shutil
import pathlib
import itertools
import mimetypes
import collections

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
    for lang in languages.values():
        lang['has_audio'] = False

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
        # We check for the MediaTable component first, and then fall back to
        # a list of audio files in a table "media.csv", with a column
        # "mimetype".
        media_table = cldf.get('MediaTable') or cldf.get('media.csv')
        if media_table is None:
            args.log.error('No media table found')
            return

        id_col = media_table.get_column(
            'http://cldf.clld.org/v1.0/terms.rdf#id')
        id_col = id_col.name if id_col is not None else 'ID'
        mtype_col = media_table.get_column(
            'http://cldf.clld.org/v1.0/terms.rdf#mediaType')
        mtype_col = mtype_col.name if mtype_col is not None else 'mimetype'

        # TODO maybe check for MediaTable component first, then fall back
        # to `media.csv` file name
        audio = {
            row[id_col]: row
            for row in media_table
            if row.get(id_col) and row[mtype_col].startswith('audio/')}

        # normalise relevant column headers to their CLDF property names
        # to reduce headache
        media_colmap = {
            id_col: 'id',
            mtype_col: 'mediaType',
        }
        audio = {
            aid: {(media_colmap.get(k) or k): v for k, v in audio_file.items()}
            for aid, audio_file in audio.items()}

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
                    form2audio[fid].extend(audio_file['id'])
                else:
                    form2audio[fid].append(audio_file['id'])

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
            fid: audio_file['id']
            for fid, audio_file in form2audio.items()
            if audio_file is not None}

    # tell parameter table about languages with values
    for form in forms.values():
        pid = form.get('parameterReference')
        lid = form.get('languageReference')
        if pid in parameters and lid in languages:
            parameters[pid]['representation'].add(lid)

    # tell language and parameter table about audio files
    for fid in form2audio:
        lid = forms[fid].get('languageReference')
        pid = forms[fid].get('parameterReference')
        if lid in languages:
            languages[lid]['has_audio'] = True
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

        suffix = media.PREFERRED_AUDIO.get(audio_file['mediaType']) \
            or mimetypes.guess_extension(audio_file['mediaType']) \
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

        param_forms = {
            form['languageReference']: {
                'form': form['form'],
                # FIXME I maneuvered myself in some ugly syntax... (<_<)"
                'audio': {
                    'name': audio[form2audio[form['id']]]['file-path'].name,
                    'mediaType': audio[form2audio[form['id']]]['mediaType'],
                } if form['id'] in form2audio else None,
            }
            for form in param_forms
            if form.get('languageReference') in languages}
        param_languages = {
            lid: languages[lid]
            for lid in param_forms}

        data = {
            'languages': param_languages,
            'forms': param_forms,
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
            languages=languages.items(),
            title_tooltip=title_tooltip,
            title=title,
        )

    for lid, lang_forms in itertools.groupby(
        sorted(forms.values(), key=lambda r: (r['languageReference'], r['id'])),
        lambda r: r['languageReference'],
    ):
        if lid not in languages:
            continue

        lang_forms = {
            form['parameterReference']: {
                'form': form['form'],
                # FIXME I maneuvered myself in some ugly syntax... (<_<)"
                'audio': {
                    # audio file lies in parameters folder
                    'name': '../parameter-{}/{}'.format(
                        pid, audio[form2audio[form['id']]]['file-path'].name),
                    'mimetype': audio[form2audio[form['id']]]['mediaType'],
                } if form['id'] in form2audio else None,
            }
            for form in lang_forms
            if (not args.include or form.get('parameterReference') in args.include)
            and form.get('parameterReference') in parameters}
        lang_parameters = {
            pid: {
                'id': parameters[pid]['name'],
                'name': parameters[pid]['name'],
            }
            for pid in lang_forms}

        data = {
            'parameters': lang_parameters,
            'forms': lang_forms,
        }

        pout = outdir / 'language-{}'.format(lid)
        if not pout.exists():
            pout.mkdir()

        render(
            pout,
            'data.js',
            data=data,
            options={'minZoom': 0, 'maxZoom': args.max_zoom})
        render(
            pout / 'index.html',
            'language.html',
            language=languages[lid],
            index=False,
            data=data,
            parameters=parameters.items(),
            languages=languages.items(),
            title_tooltip=title_tooltip,
            title=title,
        )

    language_data = {
        k: {
            'Name': v['name'],
            'latitude': v['latitude'],
            'longitude': v['longitude'],
        }
        for k, v in languages.items()}
    data = {
        'index': True,
        'languages': language_data,
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
