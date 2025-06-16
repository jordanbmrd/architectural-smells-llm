#!/bin/bash

# Récupère le dossier de la release passé en argument
RELEASE_DIR="$1"

if [ -z "$RELEASE_DIR" ]; then
    echo "❌ Usage: ./run_analysis.sh <release_dir>"
    exit 1
fi

if [ ! -d "$RELEASE_DIR" ]; then
    echo "❌ Error: directory '$RELEASE_DIR' does not exist"
    exit 1
fi

# Affiche la version de Python utilisée
PYTHON_PATH=$(which python3)
PYTHON_VERSION=$($PYTHON_PATH --version)
echo "🧪 Python utilisé : $PYTHON_PATH (version $PYTHON_VERSION)"

# Vérifie la présence du fichier de config dans le dossier de la release
CONFIG_FILE="$RELEASE_DIR/code_quality_config.yaml"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "⚠️ config file not found in release dir, copying default"
    cp ./code_quality_config.yaml "$CONFIG_FILE"
fi

# Exécution de l'analyse dans le dossier de la release
echo "🔍 Analyzing code in $RELEASE_DIR"
analyze_code_quality "$RELEASE_DIR"

# Supposons que analyze_code_quality crée son output dans le dossier courant,
# on déplace le fichier résultant dans le dossier de la release s’il n’y est pas déjà
if [ -f "code_quality_report.csv" ] && [ ! -f "$RELEASE_DIR/code_quality_report.csv" ]; then
    mv code_quality_report.csv "$RELEASE_DIR/"
fi
