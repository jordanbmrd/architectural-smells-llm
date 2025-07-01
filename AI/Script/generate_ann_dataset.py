#!/usr/bin/env python3
"""
Script to generate the final dataset with the essential columns
for training the ANN model.
"""

import os
import csv
import glob
import sys
import re
from collections import defaultdict
from pathlib import Path

def parse_version(version_name):
    """Parse a version to allow correct numeric sorting."""
    try:
        version_parts = version_name[1:].split('.')
        numeric_parts = []
        for part in version_parts:
            numeric_part = ''
            for char in part:
                if char.isdigit():
                    numeric_part += char
                else:
                    break
            numeric_parts.append(int(numeric_part) if numeric_part else 0)
        while len(numeric_parts) < 3:
            numeric_parts.append(0)
        return tuple(numeric_parts)
    except:
        return (0, 0, 0)

def clean_file_path(file_path):
    """Clean the file path to keep only the part after the version."""
    try:
        normalized_path = file_path.replace('\\', '/')
        parts = normalized_path.split('/')
        version_index = -1
        for i, part in enumerate(parts):
            if part.startswith('v') and '.' in part:
                version_part = part.split('.')[0][1:]
                if version_part.isdigit():
                    version_index = i
        if version_index >= 0 and version_index < len(parts) - 1:
            return '/'.join(parts[version_index + 1:])
        else:
            if len(parts) > 2:
                return '/'.join(parts[-3:])
            else:
                return file_path
    except Exception as e:
        print(f"Error in clean_file_path: {e}")
        return file_path

def extract_smells_from_csv(csv_file_path, version):
    """Extracts all individual smells from a CSV file."""
    smells = []
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                file_path_raw = row.get('File', '').strip()
                smell_name = row.get('Name', '').strip()
                module_class = row.get('Module/Class', '').strip()
                severity = row.get('Severity', '').strip().lower()

                if file_path_raw and smell_name and file_path_raw.strip().lower() != "unknown":
                    file_path = clean_file_path(file_path_raw)
                    if str(file_path).startswith('<function'):
                        file_path = file_path_raw
                    clean_file_path_no_spaces = file_path.replace(" ", "")
                    clean_module_class = module_class.replace(" ", "") if module_class else ""
                    clean_smell_name = smell_name.replace(" ", "")
                    if clean_module_class:
                        smell_id = f"{clean_file_path_no_spaces}/{clean_module_class}/{clean_smell_name}"
                    else:
                        smell_id = f"{clean_file_path_no_spaces}//{clean_smell_name}"
                    smell_data = {
                        'version': version,
                        'file_path': file_path,
                        'type_of_smell': smell_name,
                        'id_smell': smell_id,
                        'severity': severity
                    }
                    smells.append(smell_data)
    except FileNotFoundError:
        print(f"File not found: {csv_file_path}")
    except Exception as e:
        print(f"Error reading {csv_file_path}: {e}")
    return smells

def collect_all_smells_data(versions_directory):
    """Collects all smell data from all versions, but includes only all except the last for dataset generation."""
    all_smells = []
    version_smells_map = defaultdict(set)
    versions_dir = Path(versions_directory)

    if not versions_dir.exists():
        print(f"Directory {versions_dir} does not exist!")
        return [], {}, []

    version_folders = [f for f in versions_dir.iterdir() if f.is_dir() and f.name.startswith('v')]
    sorted_versions = sorted(version_folders, key=lambda x: parse_version(x.name))

    for version_folder in sorted_versions:
        version_name = version_folder.name
        csv_file = version_folder / "code_quality_report.csv"
        if csv_file.exists():
            smells = extract_smells_from_csv(csv_file, version_name)
            for smell in smells:
                version_smells_map[version_name].add(smell['id_smell'])
            # We only want to include all smells except the last version in the dataset
            if version_folder != sorted_versions[-1] or len(sorted_versions) == 1:
                print(f"Collecting data for version {version_name}...")
                all_smells.extend(smells)
                print(f"  - {len(smells)} smells detected")
        else:
            print(f"No code_quality_report.csv found for {version_name}")

    return all_smells, version_smells_map, [v.name for v in sorted_versions]


def remove_duplicate_smell_ids_within_version(all_smells):
    """Removes duplicates based on (version, smell_id), keeping the first occurrence."""
    seen_version_smell_ids = set()
    unique_smells = []
    duplicates_count = 0

    for smell in all_smells:
        version_smell_key = (smell['version'], smell['id_smell'])
        if version_smell_key not in seen_version_smell_ids:
            seen_version_smell_ids.add(version_smell_key)
            unique_smells.append(smell)
        else:
            duplicates_count += 1

    print(f"🔄 Duplicates removed within each version: {duplicates_count} duplicated smells")
    print(f"📊 Unique smells kept: {len(unique_smells)}")
    return unique_smells

def calculate_version_counts_and_next_version_presence(all_smells, version_smells_map, sorted_versions):
    """Calculates how many previous versions each smell appeared in and if it appears in the next version."""
    version_index = {version: i for i, version in enumerate(sorted_versions)}
    enriched_smells = []
    for smell in all_smells:
        current_version = smell['version']
        smell_id = smell['id_smell']
        current_index = version_index.get(current_version, -1)
        count_previous_versions = 0
        if current_index > 0:
            for i in range(current_index):
                previous_version = sorted_versions[i]
                if smell_id in version_smells_map.get(previous_version, set()):
                    count_previous_versions += 1
        present_in_next = False
        if current_index >= 0 and current_index < len(sorted_versions) - 1:
            next_version = sorted_versions[current_index + 1]
            present_in_next = smell_id in version_smells_map.get(next_version, set())
        enriched_smell = smell.copy()
        enriched_smell['count_versions_appears'] = count_previous_versions
        enriched_smell['present_in_next_version'] = 1 if present_in_next else 0
        enriched_smells.append(enriched_smell)
    return enriched_smells

def generate_final_dataset(enriched_smells, output_file):
    """Generate the final dataset in the recommended format."""
    if not enriched_smells:
        print("No data to write!")
        return

    fieldnames = [
        'version',
        'file_path', 
        'smell_type',
        'smell_id',
        'severity',
        'version_count',
        'next_version_present'
    ]

    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for smell in enriched_smells:
                row = {
                    'version': smell['version'],
                    'file_path': smell['file_path'],
                    'smell_type': smell['type_of_smell'],
                    'smell_id': smell['id_smell'],
                    'severity': smell['severity'],
                    'version_count': smell['count_versions_appears'],
                    'next_version_present': smell['present_in_next_version']
                }
                writer.writerow(row)

        print(f"\n✅ Final dataset generated: {output_file}")
        print(f"📊 {len(enriched_smells)} smell records")
        versions = set(smell['version'] for smell in enriched_smells)
        smell_types = set(smell['type_of_smell'] for smell in enriched_smells)
        print(f"📈 Dataset statistics:")
        print(f"  - Versions analyzed: {len(versions)}")
        print(f"  - Unique smell types: {len(smell_types)}")
        print(f"  - Smells present in next version: {sum(1 for s in enriched_smells if s['present_in_next_version'])}")

    except Exception as e:
        print(f"❌ Error generating dataset: {e}")

def generate_last_version_dataset(last_version, versions_dir, output_path):
    """Generates a dataset for the last version only, without the 'next_version_present' column."""
    version_folder = versions_dir / last_version
    csv_file = version_folder / "code_quality_report.csv"

    if not csv_file.exists():
        print(f"❌ No code_quality_report.csv found for last version {last_version}")
        return

    print(f"\n📦 Generating dataset for last version: {last_version}")
    smells = extract_smells_from_csv(csv_file, last_version)

    if not smells:
        print("⚠️ No smells found in last version.")
        return

    output_file = output_path / f"{output_path.name}_LastVersion.csv"
    fieldnames = [
        'version',
        'file_path', 
        'smell_type',
        'smell_id',
        'severity',
        'version_count'
    ]

    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for smell in smells:
                row = {
                    'version': smell['version'],
                    'file_path': smell['file_path'],
                    'smell_type': smell['type_of_smell'],
                    'smell_id': smell['id_smell'],
                    'severity': smell['severity'],
                    'version_count': 0  # Default or placeholder
                }
                writer.writerow(row)

        print(f"✅ Last version dataset saved: {output_file}")
        print(f"📊 Smells in last version: {len(smells)}")
    except Exception as e:
        print(f"❌ Error writing last version dataset: {e}")


def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python script.py <versions_folder>")
        print("Example: python script.py tensorflow")
        sys.exit(1)

    versions_directory = sys.argv[1]

    print("🚀 Generating the final dataset for the ANN model")
    print("=" * 60)
    print(f"📁 Versions folder: {versions_directory}")

    print("\n🔍 Step 1: Collecting data...")
    all_smells, version_smells_map, sorted_versions = collect_all_smells_data(versions_directory)
    if not all_smells:
        print("❌ No data found!")
        return

    print("\n🧹 Step 2: Removing duplicates within each version...")
    all_smells = remove_duplicate_smell_ids_within_version(all_smells)

    print("\n📊 Step 3: Calculating metrics...")
    enriched_smells = calculate_version_counts_and_next_version_presence(
        all_smells, version_smells_map, sorted_versions
    )

    versions_directory = sys.argv[1]
    project_name = Path(versions_directory).name
    output_path = Path("AI/Dataset/ANN-Dataset") / project_name
    output_path.mkdir(parents=True, exist_ok=True)

    print("\n💾 Step 4: Generating final dataset...")
    dataset_file = output_path / f"{project_name}_Dataset.csv"
    generate_final_dataset(enriched_smells, dataset_file)



    print("\n🧩 Step 5: Generating last version dataset...")

    generate_last_version_dataset(sorted_versions[-1], Path(versions_directory), output_path)


    print("\n🎉 Process completed successfully!")

if __name__ == "__main__":
    main()