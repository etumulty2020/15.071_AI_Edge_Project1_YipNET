"""YipNET launcher: sets everything up the first time, then opens the app in your web browser.

You do not need to run this file yourself: double-click START_YipNET_Windows.bat (Windows) or
START_YipNET_Mac.command (Mac). Those find Python and run this file.

What it does:
1. The first time only: makes a private Python environment for YipNET and installs the packages in
   requirements-app.txt (a few minutes; about 700 MB; needs the internet). Your computer's own Python is not changed.
   The environment lives in your user folder, not next to this file, so a shared or synced copy of this folder
   (OneDrive, a ZIP) never carries one computer's setup to another, and long folder paths cannot break it:
     Windows: %LOCALAPPDATA%\\YipNET\\env      Mac: ~/Library/Application Support/YipNET/env
   Delete that folder to start over (or set the environment variable YIPNET_ENV to put it somewhere else).
2. Starts the YipNET app (demo_app/app.py) on a free port of this computer only (127.0.0.1: nothing is shared online).
3. Opens the page in your browser. The first start also downloads BirdNET (about 1 minute).
4. Keeps running until you close this window (or press Ctrl+C).
"""
import hashlib
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import venv
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
if os.environ.get('YIPNET_ENV'):
    ENV_DIR = os.environ['YIPNET_ENV']
elif os.name == 'nt':
    ENV_DIR = os.path.join(os.environ.get('LOCALAPPDATA') or os.path.expanduser('~'), 'YipNET', 'env')
elif sys.platform == 'darwin':
    ENV_DIR = os.path.expanduser('~/Library/Application Support/YipNET/env')
else:
    ENV_DIR = os.path.expanduser('~/.local/share/YipNET/env')
OLD_ENV_DIR = os.path.join(HERE, '.yipnet_env')     # where earlier versions of this launcher put it
REQUIREMENTS = os.path.join(HERE, 'requirements-app.txt')
APP = os.path.join(HERE, 'demo_app', 'app.py')
DONE_MARK = os.path.join(ENV_DIR, 'installed.txt')
SUPPORTED = ((3, 11), (3, 14))          # Python versions the pinned packages are published for (not 3.15 yet)


def say(text=''):
    print(text, flush=True)


def stop(text):
    say('\n' + '=' * 70)
    say(text)
    say('=' * 70)
    if os.name == 'nt':
        input('\nPress Enter to close this window.')
    sys.exit(1)


def env_python():
    return os.path.join(ENV_DIR, 'Scripts', 'python.exe') if os.name == 'nt' else os.path.join(ENV_DIR, 'bin', 'python')


def requirements_hash():
    return hashlib.sha256(open(REQUIREMENTS, 'rb').read()).hexdigest()


def env_works():
    """True when the environment was made on THIS computer and runs (a copy from another computer points to that
    computer's Python and fails; so does a half-finished install)."""
    try:
        cfg = open(os.path.join(ENV_DIR, 'pyvenv.cfg')).read()
        home = next(line.split('=', 1)[1].strip() for line in cfg.splitlines() if line.startswith('home'))
        if not os.path.isdir(home):
            return False
        return subprocess.call([env_python(), '-c', 'import flask, birdnet'], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=120) == 0
    except Exception:
        return False


def set_up():
    version = sys.version_info[:2]
    if not SUPPORTED[0] <= version <= SUPPORTED[1]:
        stop(f'YipNET needs Python 3.11 to 3.14; this computer used Python {version[0]}.{version[1]}.\n'
             'Install Python 3.13 from https://www.python.org/downloads/ and double-click the START file again.')
    if sys.platform == 'darwin' and platform.machine() == 'x86_64':
        stop('This Mac has an Intel processor. BirdNET\'s engine (ai-edge-litert) is only published for Macs with\n'
             'Apple silicon (M1 or later), so YipNET cannot run here. Please use a Windows PC or an Apple-silicon Mac.\n'
             '(Apple menu > About This Mac: "Chip: Apple M..." means Apple silicon.)')
    if os.path.isdir(OLD_ENV_DIR):
        #earlier launchers kept the environment inside this folder (700 MB that OneDrive syncs and ZIPs carry along)
        say(f'Removing the old setup folder {OLD_ENV_DIR} (no longer used)...')
        shutil.rmtree(OLD_ENV_DIR, ignore_errors=True)
    if os.path.exists(DONE_MARK) and open(DONE_MARK).read().strip() == requirements_hash() and env_works():
        return
    if os.path.exists(ENV_DIR) and not env_works():
        say('Found an unfinished or broken YipNET setup: making a fresh one.')
        shutil.rmtree(ENV_DIR, ignore_errors=True)
    os.makedirs(os.path.dirname(ENV_DIR), exist_ok=True)
    say('First start: setting up YipNET. This takes a few minutes (about 700 MB) and needs the internet.')
    say(f'Everything goes into {ENV_DIR} (delete that folder to start over).\n')
    runs = os.path.exists(env_python()) and subprocess.call([env_python(), '-c', 'import sys'], stdout=subprocess.DEVNULL,
                                                            stderr=subprocess.DEVNULL) == 0
    if not runs:
        venv.create(ENV_DIR, with_pip=True, clear=True)
    steps = [[env_python(), '-m', 'pip', 'install', '--upgrade', 'pip'],
             [env_python(), '-m', 'pip', 'install', '-r', REQUIREMENTS]]
    for step in steps:
        if subprocess.call(step) != 0:
            stop('Installing the packages did not work. Check the internet connection and try again.\n'
                 f'If it keeps failing, delete the folder {ENV_DIR} and double-click the START file again.')
    with open(DONE_MARK, 'w') as f:
        f.write(requirements_hash())
    say('\nSetup finished.\n')


def free_port():
    #Macs: macOS's AirPlay Receiver listens on port 5000 (and 7000), so YipNET starts at 5050 there
    first = 5050 if sys.platform == 'darwin' else 5000
    for port in range(first, 5100):
        with socket.socket() as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    stop('No free port found between 5000 and 5099.')


def main():
    os.chdir(HERE)
    set_up()
    port = free_port()
    url = f'http://127.0.0.1:{port}'
    say('Starting YipNET...')
    app = subprocess.Popen([env_python(), APP], env={**os.environ, 'PORT': str(port)}, cwd=HERE)
    for _ in range(120):                                   # wait until the page answers (up to 2 minutes)
        if app.poll() is not None:
            stop('YipNET stopped while starting; the messages above say why.')
        try:
            urllib.request.urlopen(url + '/api/status', timeout=2)
            break
        except OSError:
            time.sleep(1)
    else:
        stop('YipNET did not start within 2 minutes; the messages above say why.')
    webbrowser.open(url)
    say('\n' + '=' * 70)
    say(f'YipNET is open in your browser: {url}')
    say('The first time, the page waits about a minute while BirdNET downloads.')
    say('Drag WAV recordings (or a whole folder) onto the page to tag them.')
    say('To stop YipNET, close this window.')
    say('=' * 70 + '\n')
    try:
        app.wait()
    except KeyboardInterrupt:
        app.terminate()


if __name__ == '__main__':
    main()
