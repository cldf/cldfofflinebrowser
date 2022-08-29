import pathlib

from cldfbench.__main__ import main


def test_create(tmpdir):
    out = pathlib.Path(str(tmpdir)) / 'offline'
    ds = pathlib.Path(__file__).parent / 'dataset' / 'dataset.py'
    main(['offline.create', str(ds), '--outdir', str(out)])
    assert not out.joinpath('parameter-1', 'ask.wav').exists()
    assert out.joinpath('tiles', '0', '0', '0.png').is_file()

    main(['offline.create', str(ds), '--outdir', str(out), '--with-audio'])
    assert out.joinpath('parameter-1', 'ask.wav').exists()

    main(['offline.create', str(ds), '--outdir', str(out.parent / 'o'), '--include', '5'])
    assert not out.parent.joinpath('o', 'parameter-1').exists()


def test_custom_names(tmpdir):
    out = pathlib.Path(str(tmpdir)) / 'offline'
    ds = pathlib.Path(__file__).parent / 'dataset-custom-names' / 'dataset.py'
    main(['offline.create', str(ds), '--outdir', str(out), '--with-audio'])
    assert out.joinpath('parameter-1', 'ask.wav').exists()
