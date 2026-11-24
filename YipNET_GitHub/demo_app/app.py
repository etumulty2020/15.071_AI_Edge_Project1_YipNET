"""YipNET: coyote call classifier, demo app.

A small web page on this computer. Drag WAV files or a folder onto the page; each clip goes
through the notebook's final tool (Section 8, best_guess_sheet) and the page shows every column of the best-guess
spreadsheet, a summary of the batch, and a spectrogram of each clip with its sound times.

The model is the notebook's own: the final models and functions saved by the cell "Save the final tool for the demo
app" in YipNET.ipynb (demo_app/final_tool.pkl). Only the steps that tie them together
are written here, copied from best_guess_sheet; on start-up the app runs the two made-up sounds and checks that it
gives exactly the notebook's answers.

The public copy of final_tool.pkl holds only the trained models and functions. The "unfamiliar clip" warning compares
new clips with the training recordings' BirdNET numbers, which belong to the research group, so that part is left out
("checks" is None) and the warning column then reports only "no coyote heard". A final_tool.pkl saved by the notebook
on the team's own data includes the checks, and the app uses them.

Easiest start: double-click START_YipNET_Windows.bat (or START_YipNET_Mac.command); it installs what is needed and
opens the page in the browser. By hand, from the project folder:
    pip install -r requirements-app.txt        (once)
    python demo_app/app.py
then open http://127.0.0.1:5000
"""
import datetime
import os
import pickle
import queue
import re
import shutil
import sys
import tempfile
import threading
import time
import traceback
import uuid

import numpy as np
import pandas as pd

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(APP_DIR)
#the public model (trained models only), or the full one the notebook saves on your own data (never committed)
BUNDLE_FILE = os.path.join(APP_DIR, 'final_tool.pkl')
if os.path.exists(os.path.join(APP_DIR, 'final_tool_local.pkl')):
    BUNDLE_FILE = os.path.join(APP_DIR, 'final_tool_local.pkl')
OUTPUT_DIR = os.path.join(APP_DIR, 'outputs')
#clips sent to BirdNET at a time; 1 gives the smoothest progress bar (the notebook sends a whole folder at once,
#which gives the same numbers for each clip)
BIRDNET_BATCH = 1
#the columns that compare with the training labels: not shown in the demo
LABEL_COLUMNS = ['Labels in the spreadsheet', 'Match with labels (%)', 'Model added', 'Model missed']


class Tool:
    """The notebook's final tool, loaded once."""

    def __init__(self):
        self.state = 'starting'          # starting, loading, checking, ready, error
        self.message = 'Starting'
        self.error = None
        self.check = None                # result of the start-up check against the notebook
        self.b = None
        self.f = None
        self.model = None

    # --- loading -----------------------------------------------------------------------------------------------
    def load(self):
        try:
            self.state, self.message = 'loading', 'Loading the final models saved by the notebook'
            if not os.path.exists(BUNDLE_FILE):
                raise RuntimeError(f'{BUNDLE_FILE} not found. Run the notebook through the cell "Save the final tool '
                                   f'for the demo app" first.')
            try:
                import cloudpickle  # noqa: F401  (needed to read functions saved from a notebook)
            except ImportError:
                raise RuntimeError('cloudpickle is not installed: run  pip install -r requirements-app.txt  (or use '
                                   'START_YipNET_Windows.bat / START_YipNET_Mac.command, which install everything)')
            with open(BUNDLE_FILE, 'rb') as f:
                self.b = pickle.load(f)
            self.f = self.b['functions']
            self.T = self.b['TAGS']

            self.message = 'Loading BirdNET (the first run downloads it)'
            import birdnet
            load = self.b['birdnet load']
            self.model = birdnet.load(*load['args'], **load['kwargs'])
            species = list(self.model.species_list)
            self.KEPT_INDEX = {short: species.index(name) for short, name in self.b['KEPT_SPECIES'].items()}
            assert self.model.get_segment_size_s() == self.b['CHUNK_SECONDS']

            self.state, self.message = 'checking', 'Checking the app against the notebook on the made-up sounds'
            self.check = self.self_check()
            self.state = 'ready'
            self.message = 'Ready'
        except Exception as e:
            traceback.print_exc()
            self.state, self.error = 'error', str(e)
            self.message = 'Could not load the model'

    def birdnet_batch(self, paths):
        """Copied unchanged from the notebook (Section 2): BirdNET's embedding and Coyote score for every chunk."""
        model, KEPT_INDEX = self.model, self.KEPT_INDEX
        encoded = model.encode(paths)
        predicted = model.predict(paths, top_k=None, default_confidence_threshold=0.0)
        enc_row = {os.path.basename(str(p)): i for i, p in enumerate(encoded.inputs)}
        pred_row = {os.path.basename(str(p)): i for i, p in enumerate(predicted.inputs)}

        results = []
        for path in paths:
            name = os.path.basename(path)
            i, j = enc_row[name], pred_row[name]
            chunks = ~encoded.embeddings_masked[i, :, 0]                  # the chunks that hold real audio
            emb = encoded.embeddings[i][chunks].astype('float16')
            ids, probs = predicted.species_ids[j][chunks], predicted.species_probs[j][chunks]
            scores = {short: np.where(ids == index, probs, 0).max(1) for short, index in KEPT_INDEX.items()}
            results.append((emb, scores))
        return results

    def self_check(self):
        """Run the made-up sounds through the app and compare with the notebook's best_guess_sheet('demo_sounds')."""
        folder = os.path.join(PROJECT_DIR, self.b['reference folder'])
        ref = self.b['reference'].drop(columns=[c for c in LABEL_COLUMNS if c in self.b['reference']])
        if not os.path.isdir(folder):
            return {'ok': None, 'note': f'{folder} not found: check skipped'}
        paths = sorted(os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith('.wav'))
        out, _ = self.analyze(paths)
        out = out[ref.columns]
        problems = []
        for col in ref.columns:
            for a, b, name in zip(ref[col], out[col], ref['File']):
                same = (a == b) or (pd.isna(a) and pd.isna(b))
                if not same:
                    try:
                        same = abs(float(a) - float(b)) < 1e-6
                    except (TypeError, ValueError):
                        pass
                if not same:
                    problems.append(f'{name}, {col}: notebook {a!r}, app {b!r}')
        if problems:
            print('START-UP CHECK: the app differs from the notebook:\n  ' + '\n  '.join(problems))
        else:
            print(f'Start-up check: the app matches the notebook on {len(ref)} made-up sounds, every column.')
        return {'ok': not problems, 'clips': len(ref), 'columns': len(ref.columns), 'problems': problems[:20]}

    # --- the final tool, as in best_guess_sheet ---------------------------------------------------------------
    def analyze(self, paths, progress=lambda done, stage, name: None):
        """Every clip's row of the best-guess sheet (least confident first), and the details the page draws."""
        import soundfile as sf
        f, T, model, fq = self.f, self.T, self.b['model'], self.b['checks']
        n = len(paths)

        #BirdNET output for each clip
        new_clips = []
        for start in range(0, n, BIRDNET_BATCH):
            batch = paths[start:start + BIRDNET_BATCH]
            progress(start, 'BirdNET', os.path.basename(batch[0]))
            new_clips += self.birdnet_batch(batch)
        progress(n, 'Best guesses', '')

        #best_guess_sheet, from here on (labels left out)
        summary = f['coyote_moments'](new_clips)
        P = model['chance'](summary)
        mix, raw = f['best_mix'](P, model.get('cutoffs'))
        confidence = model['recal'](raw)
        sure = np.where(mix == 1, P, 1 - P)
        weakest = sure.argmin(1)
        times, loose_times, howls = [], [], []
        for k, ((emb, scores), m, p) in enumerate(zip(new_clips, mix, paths)):
            progress(n + k, 'Sound times and longest howl', os.path.basename(p))
            times.append(f['sound_times'](emb, scores['coyote'], m, model))
            loose_times.append(f['sound_times'](emb, scores['coyote'], m, model, chance=self.b['LOOSE_TIME_CHANCE']))
            #the longest howl is measured only inside the clip's Howl stretches (30% sound times), as in the notebook
            howls.append(f['howl_columns'](m[T.index('Howl')] == 1, p, f['howl_spans'](emb, scores['coyote'], model)))
        #the "unfamiliar" checks need the training recordings' BirdNET numbers; the public model leaves them out (None)
        if fq is None:
            unfamiliar = np.zeros(n, dtype=bool)
        else:
            unfamiliar = fq['clip_nearest'].kneighbors(fq['novelty_scaler'].transform(summary))[0][:, 0] > fq['clip_cutoff']
        warnings, odd_chunks = [], []
        for (emb, scores), odd in zip(new_clips, unfamiliar):
            odd_k = (np.array([], dtype=int) if fq is None else
                     np.flatnonzero(fq['chunk_nearest'].kneighbors(emb.astype('float32'))[0][:, 0] > fq['chunk_cutoff']))
            odd_seconds = [f['seconds_label'](k) for k in odd_k]
            odd_chunks.append(odd_k)
            warnings.append('no coyote heard' if scores['coyote'].max() < self.b['NO_COYOTE_BELOW']
                            else 'whole clip unfamiliar' if odd
                            else f"unidentified at {', '.join(odd_seconds)}" if odd_seconds else '')
        out = pd.DataFrame({'File': [os.path.basename(p) for p in paths],
                            'Clip length (s)': [round(sf.info(p).duration, 1) for p in paths],
                            'Best guess': [f['mix_name'](m) for m in mix],
                            'Confidence (%)': np.round(100 * confidence),
                            'Least sure part': [f"{T[w]} {'present' if m[w] else 'absent'} ({s[w]:.0%} sure)"
                                                for w, m, s in zip(weakest, mix, sure)],
                            **{f"{t} chance (%)": np.round(100 * P[:, j]) for j, t in enumerate(T)},
                            self.b['STRICT_TIMES_COL']: times, self.b['LOOSE_TIMES_COL']: loose_times,
                            'Longest howl (s)': [h[0] for h in howls], 'Longest howl starts': [h[1] for h in howls],
                            'Longest howl pitch (Hz)': [h[2] for h in howls],
                            'Warning': warnings, self.b['CORRECTED_COL']: ''})

        #what the page draws (not in the sheet): each chunk's Coyote score, the coyote moments, each sound's chance
        #in each chunk (the numbers behind the sound times) and the unidentified chunks
        details = []
        for (emb, scores), odd_k in zip(new_clips, odd_chunks):
            coyote = scores['coyote']
            chunk_P = model['chance'](f['chunk_summaries'](emb, coyote))
            details.append({'chunk_seconds': float(self.b['CHUNK_SECONDS']), 'coyote': np.round(coyote, 4).tolist(),
                            'moments': f['coyote_chunks'](coyote).astype(int).tolist(),
                            'chunk_chance': {t: np.round(chunk_P[:, j], 4).tolist() for j, t in enumerate(T)},
                            'unidentified': [int(k) for k in odd_k]})

        keep = np.argsort(confidence, kind='stable')                  # least confident first, as in the sheet
        out = out.iloc[keep].reset_index(drop=True)
        progress(2 * n, 'Done', '')
        return out, ([details[k] for k in keep], summary[keep], keep)


# --- the batch summary, as on the sheet's Summary tab (its live formulas, worked out here) -------------------------
def _hm(hours):
    """Hours as '6 h 42 min', as the sheet's Summary writes them."""
    minutes = int(round(hours * 60, 6))
    return f"{minutes // 60} h {minutes % 60} min"


def batch_summary(out, b):
    n = len(out)
    conf = out['Confidence (%)'].astype(float)
    length = out['Clip length (s)'].astype(float)
    warn = out['Warning'].fillna('').astype(str)
    total_h = length.sum() / 3600

    def stats(s):
        s = pd.to_numeric(s, errors='coerce').dropna()
        return None if s.empty else {'mean': s.mean(), 'median': s.median(), 'min': s.min(), 'max': s.max()}

    def top(share):
        k = max(1, int(round(share * n)))
        h = length.iloc[:k].sum() / 3600
        return {'clips': k, 'time': _hm(h), 'pct': h / total_h if total_h else None}

    bands = []
    for lo, hi, name in b['SHEET_BANDS']:
        inside = pd.Series(True, index=out.index)
        if lo is not None:
            inside &= conf >= lo
        if hi is not None:
            inside &= conf < hi
        bands.append({'band': name, 'clips': int(inside.sum()), 'pct': inside.mean(),
                      'confidence': conf[inside].mean() if inside.any() else None,
                      'time': _hm(length[inside].sum() / 3600)})
    counts = out['Best guess'].value_counts()
    mixes = sorted(counts.index, key=lambda m: (-counts[m], m))
    padded = ' + ' + out['Best guess'] + ' + '
    howl_s = pd.to_numeric(out['Longest howl (s)'], errors='coerce')
    howl_txt = out['Longest howl (s)'].astype(str)
    warn_rows = []
    for name, test in [('no coyote heard', warn == 'no coyote heard'), ('whole clip unfamiliar', warn == 'whole clip unfamiliar'),
                       ('unidentified chunk', warn.str.startswith('unidentified')), ('Any warning', warn != '')]:
        warn_rows.append({'warning': name, 'clips': int(test.sum()), 'time': _hm(length[test].sum() / 3600)})
    return {
        'overview': {'clips': n, 'warning': int((warn != '').sum()), 'no_coyote': int((warn == 'no coyote heard').sum()),
                     'confidence': stats(conf), 'conf80': int((conf >= 80).sum()), 'conf50': int((conf < 50).sum())},
        'listening': {'total_h': total_h, 'total_hm': _hm(total_h), 'total_s': length.sum(), 'length': stats(length),
                      'top20': top(0.2), 'top50': top(0.5),
                      'warning': {'clips': int((warn != '').sum()), 'time': _hm(length[warn != ''].sum() / 3600),
                                  'pct': (length[warn != ''].sum() / 3600 / total_h) if total_h else None}},
        'bands': bands,
        'mixes': [{'mix': m, 'clips': int(counts[m]), 'pct': counts[m] / n,
                   'confidence': conf[out['Best guess'] == m].mean()} for m in mixes],
        'sounds': [{'sound': t, 'mean': out[f'{t} chance (%)'].mean(), 'n50': int((out[f'{t} chance (%)'] >= 50).sum()),
                    'guessed': int(padded.str.contains(f' + {t} + ', regex=False).sum())} for t in b['TAGS']],
        'howl': {'guessed': int(padded.str.contains(' + Howl + ', regex=False).sum()), 'measured': int(howl_s.notna().sum()),
                 'none': int(howl_txt.str.startswith('Howl guessed').sum()),
                 'no_howl': int((howl_txt == 'No howl detected').sum()),
                 'seconds': stats(howl_s), 'pitch': stats(out['Longest howl pitch (Hz)']),
                 'atleast': {s: int((howl_s >= s).sum()) for s in (5, 10, 20)}},
        'warnings': warn_rows,
    }


# --- jobs ---------------------------------------------------------------------------------------------------------
TOOL = Tool()
JOBS = {}
WORK = queue.Queue()


def _plain(v):
    if isinstance(v, (np.floating, float)):
        return None if np.isnan(v) else float(v)
    if isinstance(v, np.integer):
        return int(v)
    return v


def _new_sheet_name():
    stem = os.path.join(OUTPUT_DIR, f"best_guesses_{datetime.date.today():%Y-%m-%d}")
    name, k = f"{stem}.xlsx", 1
    while os.path.exists(name) or os.path.exists(os.path.splitext(name)[0] + '_birdnet.npz'):
        k += 1
        name = f"{stem}_{k}.xlsx"
    return name


def run_job(job):
    started = time.time()
    n = len(job['paths'])

    def progress(done, stage, name):
        job.update(done=done, total=2 * n, stage=stage, current=name, elapsed=time.time() - started)

    try:
        while TOOL.state not in ('ready', 'error'):
            job.update(stage=TOOL.message, state='waiting')
            time.sleep(0.5)
        if TOOL.state == 'error':
            raise RuntimeError(TOOL.error)
        job['state'] = 'running'
        out, (details, summary, _) = TOOL.analyze(job['paths'], progress)
        b = TOOL.b
        #the spreadsheet, exactly as the notebook writes it (Summary, Best guesses, How to correct, Column guide),
        #with the clips' BirdNET numbers beside it so learn_from_corrections can use the corrected sheet
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        sheet = _new_sheet_name()
        b['functions']['write_best_guess_workbook'](out, sheet, b['HOW_TO_CORRECT'], 'Batch summary')
        np.savez_compressed(os.path.splitext(sheet)[0] + '_birdnet.npz', files=out['File'].values, summary=summary)
        shown = out.drop(columns=[b['CORRECTED_COL']])
        rows = [{c: _plain(v) for c, v in r.items()} for r in shown.to_dict('records')]
        job.update(state='done', columns=list(shown.columns), rows=rows, details=details,
                   ids=[job['ids'][r['File']] for r in rows],
                   summary=_json_ready(batch_summary(out, b)) if n > 1 else None,
                   sheet=sheet, elapsed=time.time() - started)
    except Exception as e:
        traceback.print_exc()
        job.update(state='error', error=str(e))
    finally:
        shutil.rmtree(job['folder'], ignore_errors=True)


def _json_ready(x):
    if isinstance(x, dict):
        return {str(k): _json_ready(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_json_ready(v) for v in x]
    return _plain(x)


def worker():
    while True:
        run_job(WORK.get())


# --- the web page -------------------------------------------------------------------------------------------------
def create_app():
    from flask import Flask, jsonify, request, send_file, send_from_directory

    app = Flask(__name__, static_folder=None)
    app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 ** 3

    @app.get('/')
    def index():
        return send_from_directory(APP_DIR, 'index.html')

    @app.get('/api/status')
    def status():
        info = {'state': TOOL.state, 'message': TOOL.message, 'error': TOOL.error, 'check': TOOL.check}
        if TOOL.b is not None:
            b = TOOL.b
            info.update(tags=b['TAGS'], saved=b['saved'], training_clips=b['training clips'],
                        cutoffs={t: round(float(c), 2) for t, c in zip(b['TAGS'], b['model']['cutoffs'])})
        return jsonify(info)

    @app.post('/api/analyze')
    def analyze():
        files = request.files.getlist('files')
        ids = request.form.getlist('ids')
        folder = tempfile.mkdtemp(prefix='coyote_demo_')
        paths, id_of, skipped = [], {}, []
        for file, file_id in zip(files, ids):
            name = os.path.basename(file.filename.replace('\\', '/'))
            if not name.lower().endswith('.wav'):
                skipped.append(name)
                continue
            stem, ext = os.path.splitext(name)
            k = 1
            while name in id_of:                      # the same file name in two dropped folders
                k += 1
                name = f"{stem} ({k}){ext}"
            path = os.path.join(folder, name)
            file.save(path)
            paths.append(path)
            id_of[name] = file_id
        if not paths:
            shutil.rmtree(folder, ignore_errors=True)
            return jsonify({'error': 'No WAV files in what was dropped.', 'skipped': skipped}), 400
        job_id = uuid.uuid4().hex[:12]
        JOBS[job_id] = {'id': job_id, 'state': 'queued', 'paths': sorted(paths), 'ids': id_of, 'folder': folder,
                        'done': 0, 'total': 2 * len(paths), 'stage': 'Waiting', 'current': '', 'elapsed': 0,
                        'skipped': skipped}
        WORK.put(JOBS[job_id])
        return jsonify({'job': job_id, 'clips': len(paths), 'skipped': skipped})

    @app.get('/api/job/<job_id>')
    def job_status(job_id):
        job = JOBS.get(job_id)
        if job is None:
            return jsonify({'error': 'unknown job'}), 404
        keys = ['state', 'done', 'total', 'stage', 'current', 'elapsed', 'error', 'skipped']
        if job['state'] == 'done':
            keys += ['columns', 'rows', 'details', 'ids', 'summary']
        reply = {k: job.get(k) for k in keys}
        if job['state'] == 'done':
            reply['sheet'] = os.path.basename(job['sheet'])
        return jsonify(reply)

    @app.get('/api/job/<job_id>/sheet')
    def sheet(job_id):
        job = JOBS.get(job_id)
        if not job or job.get('state') != 'done':
            return jsonify({'error': 'not ready'}), 404
        return send_file(job['sheet'], as_attachment=True, download_name=os.path.basename(job['sheet']))

    return app


def main():
    os.chdir(PROJECT_DIR)                 # the notebook's working directory (demo_sounds/ and paths as there)
    threading.Thread(target=TOOL.load, daemon=True).start()
    threading.Thread(target=worker, daemon=True).start()
    port = int(os.environ.get('PORT', 5000))
    print(f'\nYipNET demo: open http://127.0.0.1:{port} in a browser (Ctrl+C to stop)\n')
    create_app().run(host='127.0.0.1', port=port, debug=False, use_reloader=False, threaded=True)


if __name__ == '__main__':
    main()
