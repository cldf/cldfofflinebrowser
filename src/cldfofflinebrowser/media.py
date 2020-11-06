import pathlib
from urllib.request import urlretrieve

from clldutils.path import md5


def download(cldf, media_row, outdir, fname, media_table='media.csv', md5sum=None):
    target = pathlib.Path(outdir) / fname
    if not target.exists() or (md5sum and md5sum != md5(target)):
        urlretrieve(cldf.get_row_url(media_table, media_row), target)
    return target
