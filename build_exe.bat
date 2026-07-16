@echo off
REM PDF Maker — Build standalone Windows executable
REM ================================================
REM Prerequisites:
REM   pip install pyinstaller
REM   pip install -r requirements.txt
REM
REM Output:
REM   dist\PDFMaker\PDFMaker.exe   (standalone folder)
REM   dist\PDFMaker-1.0.0.zip      (zipped archive for release)

echo.
echo ============================================================
echo  PDF Maker — PyInstaller Build
echo ============================================================
echo.

REM Clean previous build
if exist build rmdir /s /q build
if exist dist\PDFMaker rmdir /s /q dist\PDFMaker

REM Run PyInstaller
pyinstaller pdfmaker.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller build failed.
    pause
    exit /b 1
)

REM Zip the output folder
echo.
echo Zipping dist\PDFMaker ...
powershell -command "Compress-Archive -Path 'dist\PDFMaker' -DestinationPath 'dist\PDFMaker-1.0.0.zip' -Force"

echo.
echo ============================================================
echo  Build complete!
echo  Executable : dist\PDFMaker\PDFMaker.exe
echo  Archive    : dist\PDFMaker-1.0.0.zip
echo ============================================================
echo.
pause
