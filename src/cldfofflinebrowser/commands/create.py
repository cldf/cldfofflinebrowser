"""

"""
import shutil
import pathlib
import collections

from tqdm import tqdm
from cldfbench.cli_util import add_dataset_spec, get_dataset

import cldfofflinebrowser
from cldfofflinebrowser.osmtiles import TileList
from cldfofflinebrowser.template import render
from cldfofflinebrowser import media


def register(parser):
    parser.add_argument('--outdir', default='offline')
    add_dataset_spec(parser)
    parser.add_argument('--min-zoom', default=1, type=int)
    parser.add_argument('--max-zoom', default=10, type=int)


def run(args):
    ds = get_dataset(args)
    data = {
        'concepts': collections.OrderedDict(),
        'languages': {},
        'forms': collections.defaultdict(dict),
    }
    cldf = ds.cldf_reader()
    audio = {r['ID']: r for r in cldf['media.csv'] if r['mimetype'] == 'audio/mpeg'}

    outdir = pathlib.Path(args.outdir)
    if not outdir.exists():
        outdir.mkdir()

    for sub in ['audio', 'tiles', 'static']:
        sub = outdir / sub
        if not sub.exists():
            sub.mkdir()

    for p in pathlib.Path(cldfofflinebrowser.__file__).parent.joinpath('static').iterdir():
        shutil.copy(str(p), str(outdir / 'static' / p.name))

    for p in cldf.iter_rows('ParameterTable', 'id', 'name'):
        data['concepts'][p['id']] = p['name']

    coords = []
    for p in cldf.iter_rows('LanguageTable', 'latitude', 'longitude', 'id', 'name'):
        for c in ['Latitude', 'Longitude']:
            if c in p:
                del p[c]
        coords.append((p['latitude'], p['longitude']))
        p['latitude'] = float(p['latitude'])
        p['longitude'] = float(p['longitude'])
        data['languages'][p['ID']] = p

    tiles = TileList(outdir / 'tiles' / 'tilelist.yaml')
    tiles.create(coords, args.max_zoom, minzoom=args.min_zoom)
    missing = tiles.prune()
    if missing:
        args.log.info('Must download {} tiles'.format(missing))
        tiles.download()

    audios = []
    for form in tqdm(cldf.iter_rows('FormTable', 'languageReference', 'parameterReference', 'form')):
        data['forms'][form['parameterReference']][form['languageReference']] = {
            'form': form['form'],
            'audio_id': None,
        }
        for aid in form['Audio_Files']:
            if aid in audio:
                try:
                    fname = media.download(
                        cldf,
                        audio[aid],
                        outdir / 'audio',
                        '{}_{}.mp3'.format(form['parameterReference'], form['languageReference']))
                    data['forms'][form['parameterReference']][form['languageReference']]['audio_id'] = fname.stem
                    audios.append((fname.stem, 'audio/{}'.format(fname.name)))
                    break
                except ValueError:
                    pass

    render(outdir, 'data.js', data=data, options={'minZoom': args.min_zoom, 'maxZoom': args.max_zoom})
    render(outdir, 'index.html', audios=audios, concepts=data['concepts'].items())
