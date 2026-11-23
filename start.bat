@echo off
setlocal
set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"

where py >nul 2>nul
if errorlevel 1 (
  echo Python Launcher was not found. Install Python 3.10 or newer and enable the Python Launcher.
  pause
  exit /b 1
)
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js was not found. Install Node.js 20.19+ or 22.12+, then reopen this window.
  pause
  exit /b 1
)
where npm >nul 2>nul
if errorlevel 1 (
  echo npm was not found. Reinstall Node.js with npm included.
  pause
  exit /b 1
)

if not exist "%BACKEND%\.venv\Scripts\python.exe" (
  echo Creating the local Python environment...
  py -3 -m venv "%BACKEND%\.venv"
  if errorlevel 1 goto :failed
)
if not exist "%BACKEND%\.venv\.dependencies-installed" (
  echo Installing Flask dependencies...
  "%BACKEND%\.venv\Scripts\python.exe" -m pip install -r "%BACKEND%\requirements.txt"
  if errorlevel 1 goto :failed
  type nul > "%BACKEND%\.venv\.dependencies-installed"
)
if not exist "%FRONTEND%\node_modules\vite\bin\vite.js" (
  echo Installing frontend dependencies...
  pushd "%FRONTEND%"
  call npm ci
  if errorlevel 1 (
    popd
    goto :failed
  )
  popd
)

set "PYTHON=%BACKEND%\.venv\Scripts\python.exe"
echo Starting Prepwise. Close this window to stop the application.
pushd "%FRONTEND%"
call npm run dev
set "APP_EXIT=%ERRORLEVEL%"
popd
if not "%APP_EXIT%"=="0" (
  echo The application stopped with an error. Review the messages above.
  pause
)
exit /b %APP_EXIT%

:failed
echo Setup failed. Check that Python, Node.js and an internet connection for first-time package installation are available.
pause
exit /b 1
