# YipNET app: coyote call classifier

A web page on your own computer. Drag WAV files or a whole folder onto it. Each clip goes through YipNET's final tool
(the notebook's `best_guess_sheet`, Section 8), and the page shows:

- a progress bar (BirdNET, then the sound times and longest howl, clip by clip);
- the **batch summary** (when more than one clip is dropped): the same numbers as the spreadsheet's Summary tab;
- **clip by clip** (‹ › buttons or the ← → keys; space plays): best guess, confidence, least sure part, warning,
  longest howl, each sound's chance with its cutoff, and a spectrogram with BirdNET's Coyote score per 3-second chunk,
  each sound's chance per chunk and the sound times marked on it;
- **all results**: every column of the best-guess spreadsheet (sortable; click a row to view it), and a button to
  download the spreadsheet itself (Summary, Best guesses, How to correct, Column guide).

Nothing leaves your computer: the page runs at `http://127.0.0.1` (this computer only).

## Start it

**Easiest:** double-click `START_YipNET_Windows.bat` (Windows) or `START_YipNET_Mac.command` (Mac) in the main folder.
See the main README.

**By hand** (Python 3.11 to 3.14; Windows or an Apple-silicon Mac), from the main folder:
```
pip install -r requirements-app.txt
python demo_app/app.py
```
then open http://127.0.0.1:5000 in Chrome or Edge (folder drag-and-drop needs one of them). Another port: set the
environment variable `PORT`.

## The model

The app does not train or approximate anything. It loads the final models and functions saved by the notebook and
runs BirdNET v2.4 exactly as the notebook does. On start-up it runs the two made-up sounds in `demo_sounds/` and
compares every column with the notebook's own answers: the badge at the top right says **"Model ready · matches the
notebook"** when they agree.

| Model file | What it holds |
|---|---|
| `final_tool.pkl` (in this repository) | The trained models and functions only (0.5 MB). The "unfamiliar clip" warnings are off, because they compare new clips with the training recordings, which are not public. The "no coyote heard" warning works. |
| `final_tool_local.pkl` (made by the notebook on your own data; never committed) | The same plus the review checks on your training recordings, so every warning works. The app uses it automatically when it exists. |

## Files

| File | What it is |
|---|---|
| `app.py` | The local server: loads the model and BirdNET, runs dropped clips, writes the spreadsheet |
| `index.html` | The page |
| `final_tool.pkl` | The public model (see above) |
| `outputs/` | Spreadsheets made by the app (created on first use; never committed) |

## If something goes wrong

- *The badge says "differs from the notebook"*: the window lists the columns that differ; the usual cause is a
  `final_tool_local.pkl` saved before the models changed. Rerun the notebook's save cell, or delete that file to use
  the public model.
- *No spectrogram*: the browser could not decode that WAV; the results are still right.
- *Folder drag-and-drop does nothing*: use Chrome or Edge, or drop the WAV files themselves.
