"""
Functionality related to media file access.
"""
import pathlib
import shutil
import collections
from urllib.request import urlretrieve
from typing import Any, Optional

__all__ = ['PREFERRED_AUDIO', 'download', 'get_best_audio']

PREFERRED_AUDIO = collections.OrderedDict([
    ('audio/mpeg', '.mp3'),
    ('audio/wav', '.wav'),
    ('audio/x-wav', '.wav'),
    ('audio/ogg', '.ogg'),
])


def download(cldf, target, url) -> pathlib.Path:
    """Retrieve a media file from a CLDF dataset, copying it or downloading."""
    if not target.exists():
        if cldf.directory.joinpath(url).exists():
            shutil.copy(cldf.directory / url, target)
        else:  # pragma: no cover
            urlretrieve(url, target)
    return target


def get_best_audio(audios: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """
    For offline usage, we optimize filesize over widest browser support, so only choose one audio
    file per form.
    :param audios:
    :return:
    """
    if audios:
        pref = {mtype: i for i, mtype in enumerate(PREFERRED_AUDIO)}
        return sorted(audios, key=lambda r: pref.get(r['mediaType'], len(pref)))[0]
    return None
