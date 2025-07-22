import os
import pandas as pd
import csv
import sys
from packaging.version import parse as parse_version

# Define subtype patterns
subtype_patterns = {
    "Core": ["src/", "lib/", "app/", "main/", "core/"],
    "Config": ["setup.py", "setup.cfg", "pyproject.toml", "requirements", ".env", "config", "configs", "settings"],
    "Tests": ["tests/", "test/", "spec/"],
    "Docs": ["docs/", "README", "CONTRIBUTING", "CHANGELOG", "LICENSE"],
    "Utils": ["scripts/", "utils/", "bin/", "tools/", "examples/"],
    "Data": ["data/", "assets/", "resources/", "templates/"],
    "UI": ["ui/", "frontend/", "webapp/", "static/", "public/"],
    "Backend": ["server/", "api/", "backend/", "services/"],
    "Build": ["build/", "dist/", "release/", "packaging/", "MANIFEST.in"],
    "Deps": ["vendor/", "third_party/", "external/", "node_modules/", "libs/"]
}

# Define smell types
SMELL_TYPES = [
    "Hub-like dependencies",
    "Scattered functionality", 
    "Cyclic dependencies",
    "God objects",
    "Unstable dependencies",
    "Improper API usage",
    "Redundant abstractions",
    "Orphan Module"
]

def safe_parse_version(v):
    """
    Try to parse the version using packaging.version.
    If it fails, return a dummy version that places it at the end.
    """
    try:
        v_clean = v.lstrip('v')
        return parse_version(v_clean)
    except:
        return parse_version("9999.9999.9999")

def get_file_type(filepath):
    lowered = filepath.lower()
    for subtype, patterns in subtype_patterns.items():
        for pattern in patterns:
            if pattern.lower() in lowered:
                return subtype
    return "Unclassified"

def generate_ann_dataset(project_folder):
    project_name = os.path.basename(os.path.normpath(project_folder))

    # Read files.txt
    files_txt_path = os.path.join(project_folder, "files.txt")
    if not os.path.isfile(files_txt_path):
        raise FileNotFoundError(f"'files.txt' not found in {project_folder}")
    
    with open(files_txt_path, "r") as f:
        py_files = [line.strip() for line in f if line.strip()]
    py_files_set = set(py_files)

    # Find and sort version folders
    version_folders = sorted(
        [name for name in os.listdir(project_folder)
         if os.path.isdir(os.path.join(project_folder, name)) and name != "__pycache__"],
        key=lambda v: safe_parse_version(v)
    )

    dataset_rows = []

    for version in version_folders:
        version_path = os.path.join(project_folder, version)
        csv_path = os.path.join(version_path, "code_quality_report.csv")

        if not os.path.isfile(csv_path):
            print(f"Warning: No code_quality_report.csv in {version_path}, skipping.")
            continue

        df = pd.read_csv(csv_path)
        df = df.dropna(subset=["File", "Name"])

        # Extract relative file paths
        def extract_relative_path(full_path):
            for prefix in [version, version.lstrip("v")]:
                if prefix in full_path:
                    idx = full_path.find(prefix)
                    return full_path[idx + len(prefix) + 1:].replace("\\", "/")
            return None

        df['relative_file'] = df['File'].apply(lambda path: extract_relative_path(str(path)))

        # Group by file and collect unique smell types for each file
        file_smells = df.groupby('relative_file')['Name'].apply(lambda x: set(x.dropna())).to_dict()

        # For each file, create a binary vector for each smell type
        for file in py_files:
            file_type = get_file_type(file)
            
            # Get smells for this file (empty set if no smells)
            smells_in_file = file_smells.get(file, set())
            
            # Create binary vector for each smell type
            smell_vector = []
            for smell_type in SMELL_TYPES:
                has_this_smell = 1 if smell_type in smells_in_file else 0
                smell_vector.append(has_this_smell)
            
            # Create row: [version, file, file_type, smell_vector_as_string]
            dataset_rows.append([version, file, file_type, str(smell_vector)])

    # Create column names
    columns = ["version", "path", "file-type", "has_smells"]

    # Output dataframe
    output_df = pd.DataFrame(dataset_rows, columns=columns)

    # Save to CSV
    output_dir = os.path.join("AI", "Dataset", "Final-dataset")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{project_name}.csv")

    output_df.to_csv(output_path, index=False, quoting=csv.QUOTE_NONNUMERIC)
    print(f"✅ Vector-based dataset saved to: {output_path}")
    print(f"Smell types mapping:")
    for i, smell_type in enumerate(SMELL_TYPES):
        print(f"  smell_{i+1}: {smell_type}")

    return output_path

# Entry point
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python AI/Script/test_generate_ann_dataset.py <project_folder>")
        sys.exit(1)

    project_folder = sys.argv[1]

    try:
        generate_ann_dataset(project_folder)
    except Exception as e:
        print(f"❌ Error: {e}")
