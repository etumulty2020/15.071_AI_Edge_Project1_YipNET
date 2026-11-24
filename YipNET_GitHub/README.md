# YipNET: a coyote call classifier built on BirdNET

Sophie Rosado, Colt Hermesch, Erin Tumulty · MIT Sloan 15.071 The AI Edge, Fall 2026 · Project 1

YipNET tags coyote recordings for a wildlife research group studying coyotes in the Northeast US. For each audio clip it
gives the **mix of sounds** (Howl, Bark, Yip-Yap, Chorus, Whine, Growl, Group = more than one coyote), a **calibrated
confidence**, **when** each sound happens, and the **longest continuous howl**, written to a spreadsheet that volunteers
can sort, check and correct.

## Quick start: open the app (no coding needed)

Works on Windows 10/11 and on Macs with Apple silicon (M1 or later). Intel Macs cannot run it (BirdNET's engine is not
published for them).

1. Download this repository: the green **Code** button, then **Download ZIP**. **Unzip it first** (double-click the ZIP
   on a Mac; on Windows right-click it and choose **Extract All**). The START file does not work from inside the ZIP.
2. Open the unzipped folder and double-click:
   - **Windows:** `START_YipNET_Windows.bat`. If Windows shows "Windows protected your PC", click **More info**, then
     **Run anyway**.
   - **Mac:** `START_YipNET_Mac.command`. If macOS blocks it ("cannot be opened", "Apple could not verify",
     "do not have appropriate access privileges", or it opens as text), do this once instead: open **Terminal**
     (Command + Space, type Terminal, Return), type `cd ` (with a space), drag the unzipped YipNET folder into the
     Terminal window, press Return, then paste this line and press Return:

     ```
     xattr -dr com.apple.quarantine . ; chmod +x START_YipNET_Mac.command ; bash START_YipNET_Mac.command
     ```

     After that, double-clicking `START_YipNET_Mac.command` works.
3. **The first time only**, it installs what YipNET needs into a private folder in your user account (Windows:
   `%LOCALAPPDATA%\YipNET`; Mac: `~/Library/Application Support/YipNET`): about 3 to 5 minutes and 700 MB, with
   internet. If Python (the free programming language YipNET runs on) is missing, it offers to install it (Windows) or
   opens the download page (Mac: install Python 3.13 or 3.14, then double-click the START file again). Python 3.15 is
   too new for some of YipNET's packages.
4. Your browser opens the YipNET page. The first time, wait about a minute until the badge at the top right says
   **Model ready** (BirdNET downloads once).
5. **Drag WAV recordings, or a whole folder, onto the page.** You see each clip's best guess, when each sound happens
   and a spectrogram you can play, and a button downloads the spreadsheet. Try the two made-up sounds in `demo_sounds/`
   first: both get the warning "no coyote heard" (a tone and white noise are not coyotes).
6. To stop YipNET, close the black window. Next time, step 2 opens it in seconds.

Everything runs on your own computer; no recording is uploaded anywhere.

**If it does not start**, the black window says why. Common fixes:
- *"files are not next to this START file"*: unzip the download first and run the START file inside the unzipped folder.
- *"needs Python 3.11 to 3.14"*: install Python 3.13 from python.org (Windows: tick **Add python.exe to PATH**).
- *Mac: blocked, "do not have appropriate access privileges", or it opens as text*: use the Terminal line in step 2.
- *"Installing the packages did not work"*: check the internet connection (some school or office networks block
  downloads), then double-click the START file again; it picks up where it stopped.
- *The page does not open by itself*: open the address shown in the black window (for example http://127.0.0.1:5000,
  or http://127.0.0.1:5050 on a Mac) in Chrome or Edge.

## Method

1. **BirdNET v2.4 (frozen)** cuts each clip into 3-second chunks and gives each chunk a 1,024-number embedding and a
   Coyote score. BirdNET is not retrained.
2. **Coyote moments:** each clip is summarized by the chunks scoring at least 25% of its highest Coyote score (mean +
   max of their embeddings, plus 5 calling numbers: 2,053 features).
3. **One L2-regularized logistic regression per sound**, regularization strength chosen on held-back clips, **Platt
   calibration** on out-of-fold predictions, **per-sound cutoffs** chosen on out-of-fold predictions, and the most likely
   valid mix as the best guess. The mix's confidence is recalibrated on out-of-fold training mixes.
4. **Chunk tags:** 256 hand-tagged 3-second chunks (which sounds are in those 3 seconds) are added as extra training
   rows; each chunk always stays on the same side of a split as its clip.
5. **Validation:** grouped cross-validation (a recorder's night, or a whole recorder, is never on both sides). Model
   selection uses 6 splits (3 seeds, each grouped by recorder + night and by recorder only); the chunk-tag comparison
   in the Results table uses 5 folds of one split (Section 10). Every setting is chosen on training clips only; the two
   test sets are scored only after the model is locked.

## Results

| Measure (best guess = whole mix exactly right) | Training, held out (Section 10, 5 folds) | Test #1 (181 new clips) | Test #2 (180 new clips) |
|---|---|---|---|
| Model without chunk tags | 62.6% | **66.9%** (95% range 59.7 to 73.3%) | **63.3%** (56.1 to 70.0%) |
| Final tool (with chunk tags; the app) | 63.2% | 66.3% | 61.7% |
| Baseline: always "Howl" | | 57.5% | 56.7% |

The chunk tags do not change whole-clip accuracy (differences within chance on both tests). The final tool uses them
because they find more Yip-Yaps (Test #2: 6 of 14 against 2) and make the confidence more honest (Test #2: stated 63.0%,
right 61.7%; without: 67.8% and 63.3%), so reviewing the clips under 50% confidence catches more wrong guesses (32 of
69 against 25 of 66). Pure howls are right about 90% of the time; mixes are hard (Howl + Bark at most 1 in 4). All test
clips but two come from recorders also in training, so the tests measure new recordings, not new places. Tagging 181
clips takes about 5 minutes on a laptop CPU.

On the 6 splits used for model selection, the model without chunk tags is exactly right for 61.9% of training clips
held out (Section 8); the 5-fold numbers above come from Section 10's with-and-without comparison.

## Tried and not kept

- **Other clip summaries:** averaging every chunk of the clip, and that average plus BirdNET's species scores. The
  coyote moments predicted the main call best (Section 3).
- **Decision trees and random forests** for the howl-only question: no gain over logistic regression.
- **Per-sound cutoffs chosen by the best F1 for each sound:** caught far more Bark and Yip-Yap, but with many false
  alarms and fewer exactly right best guesses. The cutoffs in use maximize whole-mix accuracy instead (Section 8).
- **One main call per clip** (Sections 4 and 5): right for 67% of clips, below the 76% from always saying "Howl", so
  the final tool predicts every sound in the clip instead.

## What is in this repository

| File | What it is |
|---|---|
| `START_YipNET_Windows.bat`, `START_YipNET_Mac.command` | Double-click to open the app (they run `start_yipnet.py`) |
| `start_yipnet.py` | Sets up the private environment the first time, starts the app, opens the browser |
| `demo_app/` | The app (`app.py`, `index.html`) and the public model `final_tool.pkl`: the trained models only (see `demo_app/README.md`) |
| `demo_sounds/` | Two synthetic sounds (a tone and white noise) the app uses to check itself; no field recordings |
| `YipNET.ipynb` | The full notebook: data, features, models, validation, both tests, the chunk tags, the final tool |
| `requirements-app.txt` | Exact packages for the app (installed by the START files) |
| `requirements.txt` | Packages for the notebook (Python 3.13) |
| `LICENSE` | MIT License for the team's code (see License and credits) |

## Reproduce the notebook (needs the data)

The recordings, label spreadsheets and recorder locations belong to the research group and are **not public**; this
repository holds code and the trained model only. To rerun the notebook on the data (or on your own):

1. Python 3.13: `pip install -r requirements.txt` (BirdNET downloads its model on first use).
2. Put the data next to the notebook. The notebook's first section, **"Your data: where to put it"**, lists every file
   and folder, and its first code cell checks them and names anything missing:

   | Path | Contents |
   |---|---|
   | `labels_train.xlsx` | One row per training clip: `Original File`, `Call Type`, `Secondary Call Type`, `Third Call Type`, `Group`, `ARU or Location`, `Date` |
   | `audio/` | The training WAV files named in `Original File` (`RECORDER-YYYYMMDD_HHMMSS.wav`) |
   | `labels_test1.xlsx`, `Test_Audio_Files/` | The test labels (same columns) and WAV files |
   | `chunk_tags_pilot_2026-11-20_2.xlsx` (optional) | The tagged 3-second chunks; without it, the final tool is the model without chunk tags |
   | `test2/` (optional) | Test #2 labels (`labels_test2.xlsx`) and WAVs (`Test_2_Audio_Files/`); without it, Section 11 is skipped |

3. Open `YipNET.ipynb` and **Restart and Run All** (about an hour on a laptop; the first run also caches BirdNET's
   output in `birdnet_features.npz`). Outputs are written next to the notebook and never overwrite an existing file:
   - Section 9: `TEST_best_guesses_YYYY-MM-DD.xlsx` and the training-vs-test comparison (model without chunk tags)
   - Section 10: the chunk-tag check (with and without the tags, held out); `MAKE_CHUNK_SHEET = True` also writes a
     blank `chunk_tags_training_YYYY-MM-DD.xlsx` for tagging more chunks
   - Section 11: `TEST2_best_guesses_YYYY-MM-DD.xlsx` and both models on both tests
   - End: `demo_app/final_tool_local.pkl` (the full final tool, used by the app instead of the public model; never
     committed) and `best_guesses_YYYY-MM-DD.xlsx`

`.gitignore` is an allow-list: only the files in the table above can be committed, so recordings, spreadsheets,
caches and `final_tool_local.pkl` cannot be pushed by accident.

## Improving the model

Volunteers fill the **Corrected tag** column of a best-guess sheet; `learn_from_corrections(...)` reports the real
accuracy on the checked clips and retrains. Section 10 does the same for individual 3-second chunks and reports, held
out, whether training on chunk tags improves the chunk-level and clip-level guesses (with 256 tagged chunks: chunks
exactly right 35.5% against 17.6%; whole clips unchanged).

## License and credits

- **Our code** (the notebook, the app, the launchers) is released under the [MIT License](LICENSE).
- **BirdNET** is made by the K. Lisa Yang Center for Conservation Bioacoustics at the Cornell Lab of Ornithology and
  Chemnitz University of Technology. The BirdNET code (`pip install birdnet`, https://github.com/birdnet-team/birdnet)
  is MIT-licensed. The **BirdNET acoustic model v2.4 is licensed CC BY-NC-SA 4.0 (non-commercial)**: educational and
  research use is allowed; commercial use needs permission from the BirdNET team.
- **The trained model file** (`demo_app/final_tool.pkl`) is built on BirdNET v2.4's output, so it inherits the same
  **non-commercial** restriction (CC BY-NC-SA 4.0); the MIT License does not cover it.
- Citation: Kahl, S., Wood, C. M., Eibl, M., & Klinck, H. (2021). BirdNET: A deep learning solution for avian
  diversity monitoring. *Ecological Informatics*, 61, 101236.
- AI STATEMENT: AI was used to take psuedo code written by the students and convert it into the executable python code within the Jupyter notebook. All design decisions regarding the final model were made by the students.



