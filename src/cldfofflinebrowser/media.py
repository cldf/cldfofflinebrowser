import shutil
import pathlib
import collections
from urllib.request import urlretrieve
import sys

import rfc3986
from clldutils.path import md5

__all__ = ['PREFERRED_AUDIO', 'download', 'read_media_files', 'get_best_audio']

PREFERRED_AUDIO = collections.OrderedDict([
    ('audio/mpeg', '.mp3'),
    ('audio/wav', '.wav'),
    ('audio/x-wav', '.wav'),
    ('audio/ogg', '.ogg'),
])


def download(cldf, media_row, outdir, fname, media_table='media.csv', md5sum=None):
    target = pathlib.Path(outdir) / fname
    if not target.exists() or (md5sum and md5sum != md5(target)):
        url = cldf.get_row_url(media_table, media_row)
        if isinstance(url, rfc3986.URIReference):
            url = url.unsplit()
        try:  # pragma: no cover
            print(target, '<-', url, file=sys.stderr, flush=True)
            urlretrieve(url, target)
        except ValueError:
            if cldf.directory.joinpath(url).exists():
                shutil.copy(str(cldf.directory / url), str(target))
            else:  # pragma: no cover
                raise
    return target


def read_media_files(cldf, filter=None):
    """

    :param cldf:
    :param filter:
    :return: A pair of `dict`s, the first mapping media ID to media row, the second mapping form ID\
    to `list` of related media IDs.
    """
    try:
        form_ref = cldf['media.csv', 'formReference']
    except KeyError:
        form_ref = None
    form2media = collections.defaultdict(list)
    media = {}
    try:
        for r in cldf['media.csv']:
            if (filter is None) or filter(r):
                media[r['ID']] = r
                if form_ref:
                    ref = r[form_ref.name]
                    if form_ref.separator and isinstance(ref, list):
                        for rr in ref:
                            form2media[rr].append(r)
                    elif ref:
                        form2media[ref].append(r)
    except KeyError:
        pass
    return media, form2media


def get_best_audio(audios):
    """
    For offline usage, we optimize filesize over widest browser support, so only choose one audio
    file per form.
    :param audios:
    :return:
    """
    if audios:
        pref = {mtype: i for i, mtype in enumerate(PREFERRED_AUDIO)}
        return sorted(
            audios, key=lambda r: pref.get(r['mimetype'], len(pref)))[0]
    else:
        return None
