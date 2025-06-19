#!/usr/bin/env python3
"""
Script to consolidate code quality reports from all versions
into a single CSV file with specified metrics, and split into training and test sets.
"""

import os
import sys
import csv
import re
from collections import defaultdict
from pathlib import Path

def count_smells_by_type(csv_file_path):
    smell_counts = defaultdict(int)
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                smell_name = row.get('Name', '').strip()
                if smell_name:
                    smell_counts[smell_name] += 1
    except FileNotFoundError:
        print(f"File not found: {csv_file_path}")
    except Exception as e:
        print(f"Error reading {csv_file_path}: {e}")
    return smell_counts

def map_smells_to_columns(smell_counts):
    column_mapping = {
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
        'Excessive fan-in_fan-out': smell_counts.get('High Fan-in', 0) + smell_counts.get('High Fan-out', 0),
        'Large file sizes': smell_counts.get('Long File', 0) + smell_counts.get('High Lines of Code (LOC)', 0),
        'Complex conditional structures': smell_counts.get('Too Many Branches', 0),
        'Orphan modules': smell_counts.get('Orphan Module', 0)
    }
    return column_mapping

def parse_version(version_name):
    version_name = version_name.lstrip('v')
    parts = re.split(r'[.-]', version_name)
    return tuple(int(p) if p.isdigit() else 0 for p in parts)

def analyze_versions(target_dir):
    versions_data = []
    versions_dir = Path(target_dir)

    if not versions_dir.exists():
        print(f"The directory {versions_dir} does not exist!")
        return versions_data

    version_folders = [f for f in versions_dir.iterdir() if f.is_dir() and f.name.startswith('v')]
    version_folders = sorted(version_folders, key=lambda f: parse_version(f.name))

    for version_folder in version_folders:
        version_name = version_folder.name
        csv_file = version_folder / "code_quality_report.csv"

        if csv_file.exists():
            print(f"Analyzing version {version_name}...")

            smell_counts = count_smells_by_type(csv_file)
            column_data = map_smells_to_columns(smell_counts)
            row_data = {'Release version': version_name}
            row_data.update(column_data)

            versions_data.append(row_data)

            total_smells = sum(smell_counts.values())
            print(f"  - Total smells detected: {total_smells}")
            print(f"  - Smell breakdown: {dict(smell_counts)}")
        else:
            print(f"No code_quality_report.csv found for {version_name}")

    return versions_data

def write_csv(data, output_file):
    if not data:
        print(f"No data for {output_file}")
        return

    fieldnames = [
        'Release version',
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
        'Excessive fan-in_fan-out',
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

    # Nom de X = nom du dossier cible
    X = Path(target_dir).name

    # Dossier de sortie : training-testing-set/X
    output_dir = Path("first-LSTM-model/training-testing-set") / X
    output_dir.mkdir(parents=True, exist_ok=True)

    # Définir les chemins de sortie
    dataset_file = output_dir / f"{X}_Dataset.csv"
    training_file = output_dir / f"{X}_Training_Set.csv"
    test_file = output_dir / f"{X}_Test_Set.csv"

    print("🔍 Consolidating code quality reports")
    print("=" * 50)

    versions_data = analyze_versions(target_dir)

    if versions_data:
        write_csv(versions_data, dataset_file)
        split_idx = int(len(versions_data) * 0.8)
        training_data = versions_data[:split_idx]
        test_data = versions_data[split_idx:]

        write_csv(training_data, training_file)
        write_csv(test_data, test_file)

        print("\n📈 Summary:")
        print(f"  - Total versions: {len(versions_data)}")
        print(f"  - Training set: {len(training_data)}")
        print(f"  - Test set: {len(test_data)}")
    else:
        print("❌ No data to consolidate!")

if __name__ == "__main__":
    main()
