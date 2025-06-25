#!/usr/bin/env python3
"""
Script to consolidate code quality reports from all versions
into a single CSV file with smell counts per file per version,
and split into training and test sets.
"""

import os
import sys
import csv
import re
from collections import defaultdict
from pathlib import Path

def count_smells_per_file(csv_file_path):
    """
    Return a dict:
        { file_path: {smell_name: count, ...} }
    """
    file_smells = defaultdict(lambda: defaultdict(int))
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                file_path = row.get('File', '').strip()
                smell_name = row.get('Name', '').strip()
                if file_path and smell_name:
                    file_smells[file_path][smell_name] += 1
    except FileNotFoundError:
        print(f"File not found: {csv_file_path}")
    except Exception as e:
        print(f"Error reading {csv_file_path}: {e}")
    return file_smells

def map_smells_to_columns(smell_counts):
    """
    Map raw smell names to consolidated smell types.
    """
    return {
        'Hub-like dependencies': smell_counts.get('Hub-like Dependency', 0),
        'Scattered functionality': smell_counts.get('Scattered Functionality', 0),
        'Cyclic dependencies': smell_counts.get('Cyclic Dependency', 0),
        'God objects': smell_counts.get('God Object', 0),
        'Unstable dependencies': smell_counts.get('Unstable Dependency', 0),
        'Improper API usage': smell_counts.get('Potential Improper API Usage', 0),
        'Redundant abstractions': smell_counts.get('Potential Redundant Abstractions', 0),
        'High cyclomatic complexity': smell_counts.get('High Cyclomatic Complexity', 0),
        'Deep inheritance trees': 0,  # Not detected
        'High coupling': smell_counts.get('High Response for a Class (RFC)', 0),
        'Low cohesion': smell_counts.get('High Lack of Cohesion of Methods (LCOM)', 0),
        'Excessive fan-in_fan_out': smell_counts.get('High Fan-in', 0) + smell_counts.get('High Fan-out', 0),
        'Large file sizes': smell_counts.get('Long File', 0) + smell_counts.get('High Lines of Code (LOC)', 0),
        'Complex conditional structures': smell_counts.get('Too Many Branches', 0),
        'Orphan modules': smell_counts.get('Orphan Module', 0)
    }

def parse_version(version_name):
    version_name = version_name.lstrip('v')
    parts = re.split(r'[.-]', version_name)
    return tuple(int(p) if p.isdigit() else 0 for p in parts)

def analyze_versions(target_dir):
    """
    Returns a list of rows: one per (version, file)
    """
    all_data = []
    versions_dir = Path(target_dir)

    if not versions_dir.exists():
        print(f"The directory {versions_dir} does not exist!")
        return all_data

    # Rename folders if necessary
    for folder in versions_dir.iterdir():
        if folder.is_dir() and not folder.name.startswith('v'):
            new_name = f"v{folder.name}"
            new_path = folder.parent / new_name
            print(f"Renaming '{folder.name}' to '{new_name}'")
            folder.rename(new_path)

    version_folders = [f for f in versions_dir.iterdir() if f.is_dir() and f.name.startswith('v')]
    version_folders = sorted(version_folders, key=lambda f: parse_version(f.name))

    for version_folder in version_folders:
        version_name = version_folder.name
        csv_file = version_folder / "code_quality_report.csv"

        if csv_file.exists():
            print(f"Analyzing version {version_name}...")
            file_smells = count_smells_per_file(csv_file)

            for file_path, smell_counts in file_smells.items():
                row_data = {
                    'Release version': version_name,
                    'File path': file_path
                }
                row_data.update(map_smells_to_columns(smell_counts))
                all_data.append(row_data)

            print(f"  - Files processed: {len(file_smells)}")
        else:
            print(f"No code_quality_report.csv found for {version_name}")

    return all_data

def write_csv(data, output_file):
    if not data:
        print(f"No data for {output_file}")
        return

    fieldnames = [
        'Release version',
        'File path',
        'Hub-like dependencies',
        'Scattered functionality',
        'Cyclic dependencies',
        'God objects',
        'Unstable dependencies',
        'Improper API usage',
        'Redundant abstractions',
        'High cyclomatic complexity',
        'Deep inheritance trees',
        'High coupling',
        'Low cohesion',
        'Excessive fan-in_fan_out',
        'Large file sizes',
        'Complex conditional structures',
        'Orphan modules'
    ]

    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
        print(f"✅ File generated: {output_file} ({len(data)} rows)")
    except Exception as e:
        print(f"❌ Error writing {output_file}: {e}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py <directory_to_process>")
        sys.exit(1)

    target_dir = sys.argv[1]

    X = Path(target_dir).name
    output_dir = Path("first-LSTM-model/training-testing-set-count-files") / X
    output_dir.mkdir(parents=True, exist_ok=True)

    dataset_file = output_dir / f"{X}_Dataset.csv"
    training_file = output_dir / f"{X}_Training_Set.csv"
    test_file = output_dir / f"{X}_Test_Set.csv"

    print("🔍 Consolidating code quality reports by file")
    print("=" * 50)

    data = analyze_versions(target_dir)

    if data:
        write_csv(data, dataset_file)
        split_idx = int(len(data) * 0.8)
        training_data = data[:split_idx]
        test_data = data[split_idx:]

        write_csv(training_data, training_file)
        write_csv(test_data, test_file)

        print("\n📈 Summary:")
        print(f"  - Total file-version rows: {len(data)}")
        print(f"  - Training set: {len(training_data)}")
        print(f"  - Test set: {len(test_data)}")
    else:
        print("❌ No data to consolidate!")

if __name__ == "__main__":
    main()
