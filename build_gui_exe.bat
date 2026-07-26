@echo off
REM Build script for VNDB-GUI using PyInstaller

echo [1/4] Upgrading pip and checking dependencies...
python -m pip install --upgrade pip
pip install pyinstaller customtkinter requests

echo.
set "SCRIPT_DIR=%~dp0"
set "BUILD_DIR=%SCRIPT_DIR%build\pyinstaller"
set "VERSION_FILE=%BUILD_DIR%\version.txt"
set "VERSION_SUFFIX="
if not "%VNDB_GUI_VERSION%"=="" set "VERSION_SUFFIX=-%VNDB_GUI_VERSION%"
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"
set "BUNDLE_VERSION=%VNDB_GUI_VERSION%"
if "%BUNDLE_VERSION%"=="" set "BUNDLE_VERSION=dev"
> "%VERSION_FILE%" echo %BUNDLE_VERSION%

echo [2/4] Locating DLL and UI dependencies...
FOR /F "tokens=*" %%g IN ('python -c "import os, customtkinter; print(os.path.dirname(customtkinter.__file__))"') do (SET CTK_PATH=%%g)

if "%CTK_PATH%"=="" (
    echo ERROR: Could not find customtkinter library path!
    pause
    exit /b 1
)

echo Found customtkinter at: %CTK_PATH%

echo.
echo [3/4] Building VNDB-GUI...
if not exist release mkdir release
pyinstaller --onefile --windowed --clean ^
  --name VNDB-GUI%VERSION_SUFFIX% ^
  --distpath release ^
  --workpath "%BUILD_DIR%" ^
  --specpath "%BUILD_DIR%" ^
  --paths src ^
  --add-data "%CTK_PATH%;customtkinter" ^
  --add-data "%VERSION_FILE%;." ^
  src\gui.py

echo.
echo [4/4] Finalizing build...
if exist release\VNDB-GUI%VERSION_SUFFIX%.exe (
  echo ========================================================
  echo  SUCCESS! Built: release\VNDB-GUI%VERSION_SUFFIX%.exe
  echo ========================================================
) else (
  echo ERROR: Build failed. Check the logs above.
)