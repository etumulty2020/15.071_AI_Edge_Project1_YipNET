#!/bin/bash
# YipNET: double-click this file to open the app in your browser (Mac with Apple silicon: M1 or later).
# The first time it installs what YipNET needs (a few minutes, needs the internet). Close this window to stop.
# If double-clicking does not run it: right-click it, choose Open, then Open again (macOS asks once for files from
# the internet). If macOS says you "do not have appropriate access privileges", or it opens as text, open Terminal,
# type  bash  (with a space after it), drag this file into the Terminal window, and press Return.
cd "$(dirname "$0")" || exit 1

if [ ! -f start_yipnet.py ]; then
    echo "YipNET's files are not next to this START file. Unzip the whole download first, then double-click"
    echo "START_YipNET_Mac.command inside the unzipped folder."
    read -p "Press Return to close."
    exit 1
fi

if [ "$(uname -m)" = "x86_64" ] && [ "$(sysctl -n sysctl.proc_translated 2>/dev/null)" != "1" ]; then
    echo "This Mac has an Intel processor. BirdNET's engine (ai-edge-litert) is only published for Macs with"
    echo "Apple silicon (M1 or later), so YipNET cannot run here. Please use a Windows PC or an Apple-silicon Mac."
    read -p "Press Return to close."
    exit 1
fi

PY=""
for candidate in python3.13 python3.12 python3.14 python3.11 \
                 /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 \
                 /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 \
                 /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 \
                 /Library/Frameworks/Python.framework/Versions/3.11/bin/python3 \
                 /opt/homebrew/bin/python3 /usr/local/bin/python3 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
        if "$candidate" -c 'import sys; sys.exit(0 if (3, 11) <= sys.version_info[:2] <= (3, 14) else 1)' 2>/dev/null; then
            PY="$candidate"
            break
        fi
    fi
done

if [ -z "$PY" ]; then
    echo "YipNET needs Python 3.11 to 3.14, which is not on this Mac yet (Python 3.15 is too new for it)."
    echo "Opening the download page: under 'Stable Releases', download the latest Python 3.13 or 3.14"
    echo "'macOS 64-bit universal2 installer', install it, then double-click this file again."
    open "https://www.python.org/downloads/macos/"
    read -p "Press Return to close."
    exit 1
fi

echo "Using Python: $PY"
"$PY" start_yipnet.py
