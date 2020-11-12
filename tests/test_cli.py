import pathlib

from cldfbench.__main__ import main


def test_create(tmpdir):
    out = pathlib.Path(str(tmpdir))
    ds = pathlib.Path(__file__).parent / 'dataset' / 'dataset.py'
    main(['offline.create', str(ds), '--outdir', str(out)])
    assert not out.joinpath('parameter-1', 'ask.wav').exists()
    main(['offline.create', str(ds), '--outdir', str(out), '--with-audio'])
    assert out.joinpath('parameter-1', 'ask.wav').exists()
