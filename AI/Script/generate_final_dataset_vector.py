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
    "Docs": ["docs/", "README", "CONTRIBUTING", "CHANGELOG", "LICENSE", "CODE_OF_CONDUCT", "USAGE"],
    "Utils": ["scripts/", "utils/", "bin/", "tools/", "examples/", "update_deps.py"],
    "Data": ["data/", "assets/", "resources/", "templates/"],
    "UI": ["ui/", "frontend/", "webapp/", "static/", "public/"],
    "Backend": ["server/", "api/", "backend/", "services/"],
    "Build": ["build/", "dist/", "release/", "packaging/", "MANIFEST.in"],
    "Deps": ["vendor/", "third_party/", "external/", "node_modules/", "libs/", "requirements/"],
    "Docker": ["Dockerfile", "docker-compose.yml", "Dockerfile.*"],
    "Plugins": ["plugins/"]
}

# Define smell types
SMELL_TYPES = [
    "Scattered Functionality",
    "Potential Improper API Usage", 
    "Potential Redundant Abstractions",
    "Orphan Module",
    "Unstable Dependency",
    "God Object",
]

def safe_parse_version(v):
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

    # Read files.csv
    files_csv_path = os.path.join(project_folder, "files.csv")
    if not os.path.isfile(files_csv_path):
        raise FileNotFoundError(f"'files.csv' not found in {project_folder}")
    
    files_df = pd.read_csv(files_csv_path)
    files_df['file_path'] = files_df['file_path'].str.replace("\\", "/", regex=False)

    # Build metrics lookup dictionary
    metrics_dict = files_df.set_index('file_path')[['line_count', 'method_count', 'coupling_score']].to_dict('index')

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

        # Build a dict mapping file to set of smell names
        file_smells = df.groupby('relative_file')['Name'].apply(lambda x: set(x.dropna())).to_dict()

        # For each file in files.csv, construct vector row
        for file_path in files_df['file_path']:
            file_type = get_file_type(file_path)
            line_count = metrics_dict.get(file_path, {}).get('line_count', 0)
            method_count = metrics_dict.get(file_path, {}).get('method_count', 0)
            coupling_score = metrics_dict.get(file_path, {}).get('coupling_score', 0)

            smells_in_file = file_smells.get(file_path, set())
            smell_vector = [1 if smell_type in smells_in_file else 0 for smell_type in SMELL_TYPES]

            dataset_rows.append([
                version,
                file_path,
                file_type,
                line_count,
                method_count,
                coupling_score,
                str(smell_vector)
            ])

    # Define column names
    columns = ["version", "path", "file_type", "line_count", "method_count", "coupling_score", "has_smells"]

    # Output dataframe
    output_df = pd.DataFrame(dataset_rows, columns=columns)

    # Save to CSV
    output_dir = os.path.join("AI", "Dataset", "Final-dataset-vector")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{project_name}.csv")

    output_df.to_csv(output_path, index=False, quoting=csv.QUOTE_NONNUMERIC)
    print(f"✅ Vector-based dataset saved to: {output_path}")
    print("Smell types mapping:")
    for i, smell_type in enumerate(SMELL_TYPES):
        print(f"  smell_{i+1}: {smell_type}")

    return output_path

# Entry point
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python AI/Script/generate_final_dataset_vector.py <project_folder>")
        sys.exit(1)
    project_folder = sys.argv[1]
    try:
        generate_ann_dataset(project_folder)
    except Exception as e:
        print(f"❌ Error: {e}")
