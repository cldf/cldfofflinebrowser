import pathlib
import collections
from urllib.request import urlretrieve

import rfc3986
from clldutils.path import md5


def download(cldf, media_row, outdir, fname, media_table='media.csv', md5sum=None):
    target = pathlib.Path(outdir) / fname
    if not target.exists() or (md5sum and md5sum != md5(target)):
        url = cldf.get_row_url(media_table, media_row)
        if isinstance(url, rfc3986.URIReference):
            url = url.unsplit()
        urlretrieve(url, target)
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
    for r in cldf['media.csv']:
        if (filter is None) or filter(r):
            media[r['ID']] = r
            if form_ref:
                ref = r[form_ref.name]
                if form_ref.separator and isinstance(ref, list):
                    for rr in ref:
                        form2media[rr].append(r['ID'])
                elif ref:
                    form2media[ref].append(r['ID'])
    return media, form2media
