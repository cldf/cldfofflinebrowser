from cldfofflinebrowser.media import get_best_audio


def test_get_best_audio():
    assert get_best_audio([]) is None
    assert get_best_audio([dict(mimetype='audio/wav'), dict(mimetype='audio/mpeg')])['mimetype'] \
           == 'audio/mpeg'
