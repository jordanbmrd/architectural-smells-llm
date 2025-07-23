@echo off
setlocal

:: Récupère le dossier de la release passé en argument
set RELEASE_DIR=%1

if "%RELEASE_DIR%"=="" (
    echo ❌ Usage: run_analysis.bat ^<release_dir^>
    exit /b 1
)

if not exist "%RELEASE_DIR%" (
    echo ❌ Error: directory '%RELEASE_DIR%' does not exist
    exit /b 1
)

:: Affiche la version de Python utilisée
where python >nul 2>&1
if %errorlevel% == 0 (
    set PYTHON_CMD=python
) else (
    where python3 >nul 2>&1
    if %errorlevel% == 0 (
        set PYTHON_CMD=python3
    ) else (
        echo ❌ Python not found in PATH
        exit /b 1
    )
)

for /f "tokens=*" %%i in ('%PYTHON_CMD% --version') do set PYTHON_VERSION=%%i
echo 🧪 Python utilisé : %PYTHON_CMD% (version %PYTHON_VERSION%)

:: Vérifie la présence du fichier de config dans le dossier de la release
set CONFIG_FILE=%RELEASE_DIR%\code_quality_config.yaml
if not exist "%CONFIG_FILE%" (
    echo ⚠️ config file not found in release dir, copying default
    copy code_quality_config.yaml "%CONFIG_FILE%" >nul
)

:: Exécution de l'analyse dans le dossier de la release
echo 🔍 Analyzing code in %RELEASE_DIR%
analyze_code_quality "%RELEASE_DIR%"

:: Supposons que analyze_code_quality crée son output dans le dossier courant,
:: on déplace le fichier résultant dans le dossier de la release s'il n'y est pas déjà
if exist "code_quality_report.csv" if not exist "%RELEASE_DIR%\code_quality_report.csv" (
    move code_quality_report.csv "%RELEASE_DIR%\" >nul
)

endlocal 