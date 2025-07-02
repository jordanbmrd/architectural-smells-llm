#!/usr/bin/env python3

"""
This script automates the collection and cleaning of source code
from all tagged releases of a public GitHub repository.

It performs the following steps for each release (tag):
1. Downloads the source code archive via the GitHub API.
2. Extracts and normalizes the folder structure.
3. Removes all non-Python files and empty directories.
4. Runs a static analysis script (`run_analysis.sh`) to generate a code quality report.
5. Cleans the folder by keeping only the generated report (`code_quality_report.csv`).
6. Repeats the process for all tags (from oldest to newest).
7. Finally, moves the cleaned project folder to `AI/Projects-scraped/<project_name>/`.

Usage:
    python clone_and_clean_releases.py <GitHub repo URL>

Example:
    python clone_and_clean_releases.py https://github.com/pytorch/pytorch.git
"""

import os
import sys
import requests
import shutil
import zipfile
import subprocess
from pathlib import Path
from urllib.parse import urlparse

def is_python_file(path: Path) -> bool:
    return path.suffix == ".py"

def delete_non_python_files(base: Path):
    for path in base.rglob("*"):
        if path.is_file() and not is_python_file(path):
            path.unlink()
        elif path.is_dir() and not any(path.iterdir()):
            path.rmdir()

def delete_empty_dirs(base: Path):
    for dir_path in sorted(base.rglob("*"), key=lambda p: -len(p.parts)):
        if dir_path.is_dir() and not any(dir_path.iterdir()):
            dir_path.rmdir()

def get_repo_info(repo_url: str) -> tuple[str, str]:
    path = urlparse(repo_url).path.strip("/")
    repo_full_name = path[:-4] if path.endswith(".git") else path
    repo_short_name = repo_full_name.split("/")[-1]
    return repo_full_name, repo_short_name

def get_all_tags(repo_full_name: str) -> list[dict]:
    tags_url = f"https://api.github.com/repos/{repo_full_name}/tags"
    tags = []
    page = 1
    while True:
        response = requests.get(tags_url, params={"per_page": 100, "page": page})
        response.raise_for_status()
        page_data = response.json()
        if not page_data:
            break
        tags.extend(page_data)
        page += 1
    return tags[::-1]  # From oldest to newest

def download_and_extract_zip(zip_url: str, extract_to: Path):
    temp_zip = extract_to / "temp_release.zip"
    try:
        with requests.get(zip_url, stream=True) as r:
            r.raise_for_status()
            content_type = r.headers.get("Content-Type", "")
            if "zip" not in content_type and "octet-stream" not in content_type:
                raise ValueError(f"Unexpected content type: {content_type}")

            with open(temp_zip, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        with zipfile.ZipFile(temp_zip, "r") as zip_ref:
            zip_ref.extractall(extract_to)
    except requests.HTTPError as e:
        print(f"❌ HTTP error while downloading {zip_url}: {e}")
        raise
    except ValueError as e:
        print(f"❌ Invalid content while downloading {zip_url}: {e}")
        raise
    except zipfile.BadZipFile:
        print(f"❌ Failed to unzip file: {temp_zip} is not a valid zip archive.")
        raise
    finally:
        if temp_zip.exists():
            temp_zip.unlink()

def process_tag(repo_full_name: str, tag: dict, root_dir: Path):
    tag_name = tag["name"]
    release_dir = root_dir / tag_name
    zipball_url = f"https://api.github.com/repos/{repo_full_name}/zipball/{tag_name}"

    if release_dir.exists():
        shutil.rmtree(release_dir)
    release_dir.mkdir(parents=True, exist_ok=True)

    print(f"⬇️ Downloading tag {tag_name}")
    download_and_extract_zip(zipball_url, release_dir)

    # Move content of nested folder to root
    subdirs = list(release_dir.iterdir())
    if len(subdirs) == 1 and subdirs[0].is_dir():
        for item in subdirs[0].iterdir():
            shutil.move(str(item), str(release_dir))
        subdirs[0].rmdir()

    print(f"🧹 Cleaning non-Python files in {tag_name}")
    delete_non_python_files(release_dir)
    delete_empty_dirs(release_dir)

    print(f"🚀 Running analysis for {tag_name}")
    subprocess.run([str(Path(__file__).parent / "run_analysis.sh"), str(release_dir)], cwd=Path(__file__).parent, check=True)

    print(f"🧼 Cleaning folder after analysis...")
    for item in release_dir.iterdir():
        if item.name != "code_quality_report.csv":
            if item.is_file():
                item.unlink()
            else:
                shutil.rmtree(item)
    print(f"✅ Done with {tag_name}\n")

def ensure_dirs_start_with_v(project_path: Path):
    for subdir in project_path.iterdir():
        if subdir.is_dir() and not subdir.name.startswith("v"):
            new_name = "v" + subdir.name
            new_path = project_path / new_name
            if new_path.exists():
                print(f"⚠️ Cannot rename {subdir.name} to {new_name} because it already exists.")
                continue
            print(f"✏️ Renaming {subdir.name} to {new_name}")
            subdir.rename(new_path)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("❌ Usage: python clone_and_clean_releases.py <GitHub repo URL>")
        sys.exit(1)

    repo_url = sys.argv[1]
    repo_full_name, short_name = get_repo_info(repo_url)
    output_root = Path.cwd() / short_name
    output_root.mkdir(parents=True, exist_ok=True)

    tags = get_all_tags(repo_full_name)
    if not tags:
        print("⚠️ No tags/releases found.")
        sys.exit(0)

    # Optional: skip old versions until a specific tag is reached
    start_from_tag = "1.45.1.dev20250511"
    start_processing = True

    for tag in tags:
        tag_name = tag["name"]
        if not start_processing:
            if tag_name == start_from_tag:
                start_processing = True
            else:
                print(f"⏭️ Skipping {tag_name}")
                continue

        try:
            process_tag(repo_full_name, tag, output_root)
        except Exception as e:
            print(f"⚠️ Skipping tag {tag_name} due to error: {e}\n")

    # Move processed project folder into final destination
    final_destination = Path("AI") / "Projects-scraped" / short_name
    final_destination.parent.mkdir(parents=True, exist_ok=True)

    if final_destination.exists():
        print(f"🗑️ Removing existing folder: {final_destination}")
        shutil.rmtree(final_destination)

    print(f"📦 Moving {output_root} to {final_destination}")
    shutil.move(str(output_root), str(final_destination))

    # ✅ Vérifie et renomme les dossiers si nécessaire
    ensure_dirs_start_with_v(final_destination)

    print(f"✅ Project folder moved and cleaned successfully!")
