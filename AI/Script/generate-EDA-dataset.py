import os
import pandas as pd
import csv
import sys
from packaging.version import parse as parse_version

# Dictionary of patterns for each subtype (from classify_files.py)
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

def get_subtype(filepath):
    """
    Determine the subtype of a file based on its path pattern.
    """
    lowered = filepath.lower()
    for subtype, patterns in subtype_patterns.items():
        for pattern in patterns:
            if pattern.lower() in lowered:
                return subtype
    return "Unclassified"

def normalize_smell(smell_name):
    """
    Rename smell types to unify equivalent categories.
    """
    if smell_name in ["High Fan In", "High Fan Out"]:
        return "Excessive fan-in_fan_out"
    return smell_name

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

    # === Step 1: Get all unique smell types (after normalization) ===
    all_smells_set = set()

    for version in version_folders:
        csv_path = os.path.join(project_folder, version, "code_quality_report.csv")
        if not os.path.isfile(csv_path):
            continue
        df = pd.read_csv(csv_path)
        if "Name" in df.columns:
            smells = df["Name"].dropna().map(normalize_smell).unique()
            all_smells_set.update(smells)

    all_smells = sorted(all_smells_set)

    # === Step 2: Build dataset ===
    dataset_rows = []

    for version in version_folders:
        version_path = os.path.join(project_folder, version)
        csv_path = os.path.join(version_path, "code_quality_report.csv")

        if not os.path.isfile(csv_path):
            print(f"Warning: No code_quality_report.csv in {version_path}, skipping.")
            continue

        df = pd.read_csv(csv_path)
        df = df.dropna(subset=["File", "Name"])

        # Normalize smell names
        df['Name'] = df['Name'].map(normalize_smell)

        # Extract relative file paths
        def extract_relative_path(full_path):
            """
            Try to find the portion of the path that comes after the version directory.
            Match either with or without 'v' prefix.
            """
            for prefix in [version, version.lstrip("v")]:
                if prefix in full_path:
                    idx = full_path.find(prefix)
                    return full_path[idx + len(prefix) + 1:].replace("\\", "/")
            return None


        df['relative_file'] = df['File'].apply(lambda path: extract_relative_path(str(path)))

        # Count occurrences of each (file, smell)
        grouped = df.groupby(['relative_file', 'Name']).size().to_dict()

        # For every file × all smell types, add row with count or 0
        for file in py_files:
            subtype = get_subtype(file)  # Get subtype for the file
            for smell in all_smells:
                count = grouped.get((file, smell), 0)
                dataset_rows.append([version, file, subtype, smell, count])

    # Output dataframe with subtype column
    output_df = pd.DataFrame(dataset_rows, columns=["version", "file", "subtype", "smell", "count"])

    # Save to CSV
    output_dir = os.path.join("AI", "Dataset", "ANN-dataset")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{project_name}.csv")

    output_df.to_csv(output_path, index=False, quoting=csv.QUOTE_NONNUMERIC)
    print(f"✅ Dataset saved to: {output_path}")

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