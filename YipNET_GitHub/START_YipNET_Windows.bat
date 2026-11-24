@echo off
REM YipNET: double-click this file to open the app in your browser (Windows).
REM The first time it installs what YipNET needs (a few minutes, needs the internet). Close this window to stop.
title YipNET
cd /d "%~dp0"

REM Opened from inside the ZIP without unzipping: the other files are not here
if not exist "%~dp0start_yipnet.py" (
    echo YipNET's files are not next to this START file.
    echo This usually means it was opened from inside the ZIP. Right-click the ZIP file, choose "Extract All",
    echo open the extracted folder and double-click START_YipNET_Windows.bat there.
    pause
    exit /b
)

call :find_python
if not defined PY (
    echo YipNET needs Python 3.11 to 3.14, which is not on this computer yet.
    echo.
    choice /C YN /M "Install Python 3.13 now (free, from python.org through Windows' installer)"
    if errorlevel 2 goto manual
    winget install -e --id Python.Python.3.13 --accept-package-agreements --accept-source-agreements
    call :find_python
    if not defined PY goto manual
)

echo Using Python: %PY%
if "%PY:~0,3%"=="py " (
    %PY% "%~dp0start_yipnet.py"
) else (
    "%PY%" "%~dp0start_yipnet.py"
)
pause
exit /b

:find_python
set "PY="
for %%V in (3.13 3.12 3.14 3.11) do (
    if not defined PY (
        py -%%V -c "import sys" >nul 2>&1 && set "PY=py -%%V"
    )
)
if defined PY exit /b
for %%D in (313 312 314 311) do (
    if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python%%D\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python%%D\python.exe"
    if not defined PY if exist "%ProgramFiles%\Python%%D\python.exe" set "PY=%ProgramFiles%\Python%%D\python.exe"
)
if defined PY exit /b
REM any other python on PATH (including a Microsoft Store Python), if its version fits; the Store's placeholder
REM fails this check and is skipped
for /f "delims=" %%P in ('where python 2^>nul') do (
    if not defined PY (
        "%%P" -c "import sys; sys.exit(0 if (3, 11) <= sys.version_info[:2] <= (3, 14) else 1)" >nul 2>&1 && set "PY=%%P"
    )
)
exit /b

:manual
echo.
echo Please install Python 3.13 from https://www.python.org/downloads/
echo (on the first installer screen, tick "Add python.exe to PATH"), then double-click this file again.
start "" https://www.python.org/downloads/
pause
