#!/bin/bash

PYTHON_PATH=$(which python3)
PYTHON_VERSION=$($PYTHON_PATH --version)

echo "🧪 Python utilisé : $PYTHON_PATH (version $PYTHON_VERSION)"

# First check if config file exists in root directory
if [ ! -f "code_quality_config.yaml" ]; then
    echo "Error: code_quality_config.yaml not found in root directory"
    exit 1
fi

cd versions_to_analyze

for version in */; do
    if [ -d "$version" ]; then
        echo "Analyzing $version..."
        cd "$version"
        # Copy config file from root if it doesn't exist in this directory
        if [ ! -f "code_quality_config.yaml" ]; then
            cp ../../code_quality_config.yaml .
        fi
        analyze_code_quality ./
        cd ..
    fi
done