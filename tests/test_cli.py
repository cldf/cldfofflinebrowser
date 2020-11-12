import pathlib

from cldfbench.__main__ import main


def test_create(tmpdir):
    main(['offline.create', str(pathlib.Path(__file__).parent / 'dataset' / 'dataset.py'), '--outdir', str(tmpdir)])
