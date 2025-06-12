#!/bin/bash

# Dossiers
INPUT_DIR="../transformers"
OUTPUT_DIR="../PyExamine"
ANALYZER="analyze_code_quality"

# Créer le dossier de sortie s'il n'existe pas
mkdir -p "$OUTPUT_DIR"

# Parcours de tous les sous-dossiers
for dir in "$INPUT_DIR"/*; do
    if [ -d "$dir" ]; then
        repo_name=$(basename "$dir")
		cd INPUT_DIR
        echo "🔍 Analyse de $repo_name ..."
        cd ../../python_smells_detector-main
        $ANALYZER "$dir" --type architectural

        echo "✅ Résultat sauvegardé dans $output_csv"
    fi
done
