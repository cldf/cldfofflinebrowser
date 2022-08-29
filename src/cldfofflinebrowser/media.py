import shutil
import pathlib
import collections
from urllib.request import urlretrieve

import rfc3986
from clldutils.path import md5

__all__ = ['PREFERRED_AUDIO', 'download', 'get_best_audio']

PREFERRED_AUDIO = collections.OrderedDict([
    ('audio/mpeg', '.mp3'),
    ('audio/wav', '.wav'),
    ('audio/x-wav', '.wav'),
    ('audio/ogg', '.ogg'),
])


def download(cldf, media_row, outdir, fname, media_table, md5sum=None):
    target = pathlib.Path(outdir) / fname
    if not target.exists() or (md5sum and md5sum != md5(target)):
        url = cldf.get_row_url(media_table, media_row)
        if isinstance(url, rfc3986.URIReference):
            url = url.unsplit()
        try:  # pragma: no cover
            urlretrieve(url, target)
        except ValueError:
            if cldf.directory.joinpath(url).exists():
                shutil.copy(str(cldf.directory / url), str(target))
            else:  # pragma: no cover
                raise
    return target


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
            audios, key=lambda r: pref.get(r['mediaType'], len(pref)))[0]
    else:
        return None
