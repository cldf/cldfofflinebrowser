# cldfofflinebrowser

Provides a cldfbench plugin to create offline-browseable representations
of the data in a CLDF dataset.


## FAQ

**Q:** How to add sound files and transcriptions to an offline dataset?

**A:** If you want to make a new sound file and transcription browseable in an offline version:
1. Determine relevant language (`LID`) and parameter (`PID`) (aka concept) IDs.
2. Copy the sound file to `./parameter-<PID>/<LID>.mp3`.
3. Add a corresponding row to `cldf/media.csv`.
4. Add a row to `cldf/forms.csv`.
5. Re-run `cldfbench offline.create ...`.
