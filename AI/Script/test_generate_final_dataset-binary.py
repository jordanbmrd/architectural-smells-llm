import os
import pandas as pd
import csv
import sys
from packaging.version import parse as parse_version

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

        # Build a set of files with at least one smell
        smelly_files = set(df['relative_file'].dropna().unique())

        # For each file, check if it has at least one smell
        for file in py_files:
            has_smell = 1 if file in smelly_files else 0
            dataset_rows.append([version, file, has_smell])

    # Output dataframe
    output_df = pd.DataFrame(dataset_rows, columns=["version", "file", "has_smell"])

    # Save to CSV
    output_dir = os.path.join("AI", "Dataset", "Final-dataset-binary")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{project_name}.csv")

    output_df.to_csv(output_path, index=False, quoting=csv.QUOTE_NONNUMERIC)
    print(f"✅ Simplified dataset saved to: {output_path}")

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
