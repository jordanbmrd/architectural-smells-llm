#!/usr/bin/env python3
"""
Script to generate ANN training datasets:
1. Dataset with all versions except the last one.
2. Dataset with only the last version (for prediction), without the 'present_in_next_version' column.
"""

import os
import csv
import sys
from collections import defaultdict
from pathlib import Path

def parse_version(version_name):
    try:
        parts = version_name[1:].split('.')
        nums = []
        for part in parts:
            num = ''.join([c for c in part if c.isdigit()])
            nums.append(int(num) if num else 0)
        while len(nums) < 3:
            nums.append(0)
        return tuple(nums)
    except:
        return (0, 0, 0)

def clean_file_path(file_path):
    try:
        normalized = file_path.replace('\\', '/')
        parts = normalized.split('/')
        for i, part in enumerate(parts):
            if part.startswith('v') and '.' in part:
                if part.split('.')[0][1:].isdigit():
                    return '/'.join(parts[i + 1:])
        return '/'.join(parts[-3:]) if len(parts) > 2 else file_path
    except Exception as e:
        print(f"Error cleaning file path: {e}")
        return file_path

def extract_smells(csv_path, version):
    smells = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                raw_path = row.get('File', '').strip()
                smell_name = row.get('Name', '').strip()
                module_class = row.get('Module/Class', '').strip()
                severity = row.get('Severity', '').strip().lower()

                if raw_path and smell_name and raw_path.lower() != "unknown":
                    cleaned_path = clean_file_path(raw_path)
                    cleaned_path = cleaned_path.replace(" ", "")
                    mod_class = module_class.replace(" ", "") if module_class else ""
                    name = smell_name.replace(" ", "")
                    smell_id = f"{cleaned_path}/{mod_class}/{name}" if mod_class else f"{cleaned_path}//{name}"
                    smells.append({
                        'version': version,
                        'file_path': cleaned_path,
                        'smell_type': smell_name,
                        'smell_id': smell_id,
                        'severity': severity
                    })
    except FileNotFoundError:
        print(f"File not found: {csv_path}")
    except Exception as e:
        print(f"Error reading {csv_path}: {e}")
    return smells

def collect_smell_data(versions_dir):
    all = []
    version_map = defaultdict(set)
    versions_dir = Path(versions_dir)

    folders = [f for f in versions_dir.iterdir() if f.is_dir() and f.name.startswith('v')]
    sorted_versions = sorted(folders, key=lambda x: parse_version(x.name))

    if len(sorted_versions) == 0:
        return [], {}, []

    for v in sorted_versions[:-1]:  # all but last
        report = v / "code_quality_report.csv"
        if report.exists():
            print(f"📥 Processing {v.name}")
            smells = extract_smells(report, v.name)
            all.extend(smells)
            for s in smells:
                version_map[v.name].add(s['smell_id'])
            print(f"  → {len(smells)} smells")
        else:
            print(f"⚠️ No report found for {v.name}")

    return all, version_map, [v.name for v in sorted_versions]

def remove_duplicates(smells):
    seen = set()
    unique = []
    for s in smells:
        key = (s['version'], s['smell_id'])
        if key not in seen:
            seen.add(key)
            unique.append(s)
    print(f"🧹 Removed duplicates. {len(smells) - len(unique)} duplicates found.")
    return unique

def enrich_smells(smells, version_map, sorted_versions):
    idx = {v: i for i, v in enumerate(sorted_versions)}
    enriched = []
    for s in smells:
        v = s['version']
        sid = s['smell_id']
        i = idx.get(v, -1)

        prev_count = sum(1 for j in range(i) if sid in version_map.get(sorted_versions[j], set()))
        next_present = sid in version_map.get(sorted_versions[i+1], set()) if i < len(sorted_versions) - 1 else False

        enriched.append({
            **s,
            'version_count': prev_count,
            'next_version_present': 1 if next_present else 0
        })
    return enriched

def write_dataset(file_path, data, last_version=False):
    try:
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'version',
                'file_path',
                'smell_type',
                'smell_id',
                'severity',
                'version_count'
            ]
            if not last_version:
                fieldnames.append('next_version_present')

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                line = {k: row[k] for k in fieldnames}
                writer.writerow(line)

        print(f"✅ Dataset saved: {file_path}")
    except Exception as e:
        print(f"❌ Failed to write dataset: {e}")

def extract_last_version_data(last_version_folder):
    report = last_version_folder / "code_quality_report.csv"
    if not report.exists():
        print(f"⚠️ No report for last version: {last_version_folder.name}")
        return []

    smells = extract_smells(report, last_version_folder.name)
    seen = set()
    unique = []
    for s in smells:
        key = s['smell_id']
        if key not in seen:
            seen.add(key)
            unique.append({
                **s,
                'version_count': 0  # placeholder if needed
            })
    print(f"📘 Last version {last_version_folder.name} → {len(unique)} smells")
    return unique

def main():
    if len(sys.argv) != 2:
        print("Usage: python generate_ann_dataset.py <versions_folder>")
        sys.exit(1)

    project_path = Path(sys.argv[1])
    project_name = project_path.name
    output_dir = Path("AI/Dataset/ANN-Dataset") / project_name
    output_dir.mkdir(parents=True, exist_ok=True)

    print("🚀 Starting dataset generation")
    all_smells, version_map, sorted_versions = collect_smell_data(project_path)
    if not all_smells:
        print("❌ No smells found. Aborting.")
        return

    all_smells = remove_duplicates(all_smells)
    enriched = enrich_smells(all_smells, version_map, sorted_versions)
    dataset_path = output_dir / f"{project_name}_Dataset.csv"
    write_dataset(dataset_path, enriched)

    last_version_folder = project_path / sorted_versions[-1]
    last_version_data = extract_last_version_data(last_version_folder)
    last_version_path = output_dir / f"{project_name}_LastVersion.csv"
    write_dataset(last_version_path, last_version_data, last_version=True)

    print("🎉 All datasets generated successfully.")

if __name__ == "__main__":
    main()
