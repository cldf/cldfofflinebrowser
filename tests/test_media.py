from cldfofflinebrowser.media import get_best_audio


def test_get_best_audio():
    assert get_best_audio([]) is None
    assert get_best_audio([dict(mediaType='audio/wav'), dict(mediaType='audio/mpeg')])['mediaType'] \
           == 'audio/mpeg'
