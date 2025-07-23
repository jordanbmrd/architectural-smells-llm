#!/usr/bin/env python3
"""
Clone, clean, and analyze all tagged releases of a GitHub repo.
Keeps only Python files, generates `files.csv` and `code_quality_report.csv` per release.
Moves cleaned project to `AI/Projects-scraped/<project_name>/`.
"""

import os
import sys
import shutil
import zipfile
import subprocess
import requests
import ast
import argparse
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def get_repo_info(repo_url):
    path = urlparse(repo_url).path.strip("/")
    repo_full = path[:-4] if path.endswith(".git") else path
    short_name = repo_full.split("/")[-1]
    return repo_full, short_name

def get_all_tags(repo_full):
    tags, page = [], 1
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    while True:
        r = requests.get(f"https://api.github.com/repos/{repo_full}/tags", params={"per_page": 100, "page": page}, headers=headers)
        if r.status_code == 403:
            raise RuntimeError("GitHub rate limit exceeded. Set GITHUB_TOKEN env variable.")
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        tags.extend(data)
        page += 1
    return tags[::-1]

def download_and_extract(zip_url, dest):
    temp_zip = dest / "release.zip"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    with requests.get(zip_url, stream=True, headers=headers) as r:
        r.raise_for_status()
        with open(temp_zip, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
    with zipfile.ZipFile(temp_zip, "r") as zip_ref:
        zip_ref.extractall(dest)
    temp_zip.unlink()

def count_methods_in_file(file_path):
    """Count the number of functions and methods in a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        tree = ast.parse(content)
        method_count = 0
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                method_count += 1
        
        return method_count
    except (SyntaxError, UnicodeDecodeError, OSError):
        # If we can't parse the file, return 0
        return 0

def calculate_coupling_score(file_path):
    """Calculate coupling score based on imports and external dependencies."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        tree = ast.parse(content)
        coupling_score = 0
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                # Regular imports: import module
                coupling_score += len(node.names)
            elif isinstance(node, ast.ImportFrom):
                # From imports: from module import ...
                if node.module:  # Avoid None for relative imports like "from . import"
                    coupling_score += 1
                    # Add extra weight for specific imports
                    if node.names:
                        coupling_score += len(node.names) * 0.5
                else:
                    # Relative imports have slightly less coupling
                    coupling_score += 0.5
        
        return round(coupling_score, 1)
    except (SyntaxError, UnicodeDecodeError, OSError):
        # If we can't parse the file, return 0
        return 0.0

def count_lines_in_file(file_path):
    """Count the number of lines in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)
    except (UnicodeDecodeError, OSError):
        return 0

def clean_and_list_py_files(base_dir):
    py_files_info = []
    for path in list(base_dir.rglob("*")):
        if path.is_file() and path.suffix == ".py":
            relative_path = path.relative_to(base_dir)
            line_count = count_lines_in_file(path)
            method_count = count_methods_in_file(path)
            coupling_score = calculate_coupling_score(path)
            py_files_info.append((relative_path, line_count, method_count, coupling_score))
        elif path.is_file():
            path.unlink()
    
    # Remove empty directories
    for d in sorted(base_dir.rglob("*"), key=lambda p: -len(p.parts)):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
    
    # Write file info as CSV with headers
    with open(base_dir / "files.csv", "w") as f:
        f.write("file_path,line_count,method_count,coupling_score\n")
        for relative_path, line_count, method_count, coupling_score in sorted(py_files_info):
            f.write(f"{relative_path},{line_count},{method_count},{coupling_score}\n")

def run_analysis(release_dir):
    # Utiliser le script approprié selon l'OS
    if os.name == 'nt':  # Windows
        script = Path(__file__).parent / "run_analysis.bat"
        subprocess.run([str(script), str(release_dir)], cwd=Path(__file__).parent, check=True, shell=True)
    else:  # Unix/Linux/macOS
        script = Path(__file__).parent / "run_analysis.sh"
        subprocess.run([str(script), str(release_dir)], cwd=Path(__file__).parent, check=True)

def keep_only_outputs(release_dir):
    for item in release_dir.iterdir():
        if item.name not in {"code_quality_report.csv", "files.csv"}:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

def process_tag(repo_full, tag, root_dir):
    tag_name = tag["name"]
    print(f"🔄 Processing {tag_name}")
    release_dir = root_dir / tag_name
    if release_dir.exists():
        shutil.rmtree(release_dir)
    release_dir.mkdir(parents=True, exist_ok=True)
    zip_url = f"https://api.github.com/repos/{repo_full}/zipball/{tag_name}"
    download_and_extract(zip_url, release_dir)

    # Unwrap inner directory if needed
    contents = list(release_dir.iterdir())
    if len(contents) == 1 and contents[0].is_dir():
        for f in contents[0].iterdir():
            shutil.move(str(f), str(release_dir))
        contents[0].rmdir()

    clean_and_list_py_files(release_dir)
    run_analysis(release_dir)
    keep_only_outputs(release_dir)
    print(f"✅ Done {tag_name}\n")

def rename_dirs_with_v(root):
    for sub in root.iterdir():
        if sub.is_dir() and not sub.name.startswith("v"):
            new_path = root / f"v{sub.name}"
            if new_path.exists():
                print(f"⚠️ Cannot rename {sub.name} → v{sub.name}")
            else:
                sub.rename(new_path)

def main():
    parser = argparse.ArgumentParser(description="Clone, clean, and analyze all tagged releases of a GitHub repo")
    parser.add_argument("repo_url", help="GitHub repository URL")
    parser.add_argument("--version", help="Start processing from this version (e.g., 'v1.2.0' or '1.2.0')")
    
    args = parser.parse_args()

    repo_url = args.repo_url
    start_version = args.version
    repo_full, short_name = get_repo_info(repo_url)
    output_dir = Path.cwd() / short_name
    output_dir.mkdir(exist_ok=True)

    try:
        tags = get_all_tags(repo_full)
    except Exception as e:
        print(f"❌ Failed to fetch tags: {e}")
        sys.exit(1)

    if not tags:
        print("⚠️ No tags found.")
        sys.exit(0)

    # Filter tags if start_version is specified
    if start_version:
        start_found = False
        filtered_tags = []
        
        for tag in tags:
            tag_name = tag["name"]
            # Check if this is the starting version (with or without 'v' prefix)
            if tag_name == start_version or tag_name == f"v{start_version}" or tag_name.lstrip("v") == start_version.lstrip("v"):
                start_found = True
            
            if start_found:
                filtered_tags.append(tag)
        
        if not start_found:
            print(f"⚠️ Version '{start_version}' not found in tags.")
            print(f"Available tags: {', '.join([t['name'] for t in tags[:10]])}{'...' if len(tags) > 10 else ''}")
            sys.exit(1)
        
        tags = filtered_tags
        print(f"🎯 Starting from version {start_version} ({len(tags)} versions to process)")

    for tag in tags:
        try:
            process_tag(repo_full, tag, output_dir)
        except Exception as e:
            print(f"⚠️ Skipping {tag['name']} due to error: {e}")

    final_path = Path("AI") / "Projects-scraped" / short_name
    final_path.parent.mkdir(parents=True, exist_ok=True)
    if final_path.exists():
        shutil.rmtree(final_path)
    shutil.move(str(output_dir), str(final_path))
    rename_dirs_with_v(final_path)
    print(f"🎉 All done! Output at {final_path}")

if __name__ == "__main__":
    main()
