"""

"""
import shutil
import pathlib
import itertools
import collections

from tqdm import tqdm
from cldfbench.cli_util import add_dataset_spec, get_dataset

import cldfofflinebrowser
from cldfofflinebrowser.osmtiles import TileList
from cldfofflinebrowser.template import render
from cldfofflinebrowser import media


def register(parser):
    parser.add_argument('--outdir', default='offline')
    parser.add_argument('--include', default=None)
    add_dataset_spec(parser)
    parser.add_argument('--min-zoom', default=1, type=int)
    parser.add_argument('--max-zoom', default=10, type=int)


def run(args):
    args.include = args.include.split() if args.include else None

    ds = get_dataset(args)
    cldf = ds.cldf_reader()
    # We expect a list of audio files in a table "media.csv", with a column "mimetype".
    audio = {r['ID']: r for r in cldf['media.csv'] if r['mimetype'] == 'audio/mpeg'}

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
        coords.append((p['latitude'], p['longitude']))
        p['latitude'] = float(p['latitude'])
        p['longitude'] = float(p['longitude'])
        languages[p['ID']] = p

    tiles = TileList(outdir / 'tiles' / 'tilelist.yaml')
    tiles.create(coords, args.max_zoom, minzoom=args.min_zoom)
    missing = tiles.prune()
    if missing:
        args.log.info('Must download {} tiles'.format(missing))
        tiles.download()

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
        audios = []
        data = {
            'languages': {},
            'forms': collections.defaultdict(dict),
        }
        pout = outdir / 'parameter-{}'.format(pid)
        if not pout.exists():
            pout.mkdir()

        for form in forms:
            data['forms'][form['languageReference']] = {
                'form': form['form'],
                'audio': False,
            }
            data['languages'][form['languageReference']] = languages[form['languageReference']]
            parameters[pid]['representation'].add(form['languageReference'])
            # We expect linked audio in a list-valued foreign key column "Audio_Files"
            for aid in form['Audio_Files']:
                if aid in audio:
                    media.download(
                        cldf,
                        audio[aid],
                        pout,
                        '{}.mp3'.format(form['languageReference']))
                    data['forms'][form['languageReference']]['audio'] = True
                    parameters[pid]['has_audio'] = True
                    break

        render(
            pout,
            'data.js',
            data=data,
            options={'minZoom': args.min_zoom, 'maxZoom': args.max_zoom})
        render(
            pout / 'index.html'.format(pid),
            'parameter.html',
            parameter=parameters[pid],
            index=False,
            audios=audios,
            data=data,
            parameters=parameters.items(),
            title=cldf.properties['dc:title'],
        )
    render(
        outdir,
        'index.html',
        parameters=parameters.items(),
        index=True,
        title=cldf.properties['dc:title'],
    )