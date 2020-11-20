# cldfofflinebrowser

Provides a cldfbench plugin to create offline-browseable representations
of the data in a CLDF dataset.

[![Build Status](https://github.com/cldf/cldfofflinebrowser/workflows/tests/badge.svg)](https://github.com/cldf/cldfofflinebrowser/actions?query=workflow%3Atests)
[![codecov](https://codecov.io/gh/cldf/cldfofflinebrowser/branch/main/graph/badge.svg)](https://codecov.io/gh/cldf/cldfofflinebrowser)
[![PyPI](https://img.shields.io/pypi/v/cldfofflinebrowser.svg)](https://pypi.org/project/cldfofflinebrowser)


## FAQ

**Q:** How to add sound files and transcriptions to an offline dataset?

**A:** If you want to make a new sound file and transcription browseable in an offline version:
1. Determine relevant language (`LID`) and parameter (`PID`) (aka concept) IDs.
2. Copy the sound file to `./parameter-<PID>/<LID>.mp3`.
3. Add a corresponding row to `cldf/media.csv`.
4. Add a row to `cldf/forms.csv`.
5. Re-run `cldfbench offline.create ...`.
