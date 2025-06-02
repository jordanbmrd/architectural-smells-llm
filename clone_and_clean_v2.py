#!/usr/bin/env python3
"""
GitHub Repository Tag Downloader and Python File Extractor

This script downloads all tags from a specified GitHub repository and extracts only
the Python files from each tag. It's useful for analyzing the evolution of Python
code across different versions of a project.

Usage:
    python clone_and_clean_v2.py <GitHub repo URL> <output dir>

Example:
    python clone_and_clean_v2.py https://github.com/user/repo ./output
"""

import os
import sys
import requests
import shutil
import zipfile
from pathlib import Path
from urllib.parse import urlparse

def is_python_file(path: Path) -> bool:
    """Check if a given file path corresponds to a Python file.
    
    Args:
        path (Path): Path object representing the file to check
        
    Returns:
        bool: True if the file has a .py extension, False otherwise
    """
    return path.suffix == ".py"

def delete_non_python_files(base: Path):
    """Recursively delete all non-Python files from a directory.
    
    Args:
        base (Path): Base directory to start the deletion from
    """
    for path in base.rglob("*"):
        if path.is_file() and not is_python_file(path):
            path.unlink()
        elif path.is_dir() and not any(path.iterdir()):
            path.rmdir()

def delete_empty_dirs(base: Path):
    """Remove all empty directories in the given path.
    
    Args:
        base (Path): Base directory to start the cleanup from
    """
    for dir_path in sorted(base.rglob("*"), key=lambda p: -len(p.parts)):
        if dir_path.is_dir() and not any(dir_path.iterdir()):
            dir_path.rmdir()

def get_repo_info(repo_url: str) -> tuple[str, str]:
    """Extract repository information from a GitHub URL.
    
    Args:
        repo_url (str): GitHub repository URL
        
    Returns:
        tuple[str, str]: A tuple containing (full_repo_name, short_repo_name)
    """
    path = urlparse(repo_url).path.strip("/")
    repo_full_name = path[:-4] if path.endswith(".git") else path
    repo_short_name = repo_full_name.split("/")[-1]
    return repo_full_name, repo_short_name

def get_all_tags(repo_full_name: str) -> list[dict]:
    """Fetch all tags from a GitHub repository using GitHub's API.
    
    Args:
        repo_full_name (str): Full repository name in format 'owner/repo'
        
    Returns:
        list[dict]: List of tag objects containing tag information
    """
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
    return tags

def download_and_extract_zip(zip_url: str, extract_to: Path):
    """Download and extract a zip file from a given URL.
    
    Args:
        zip_url (str): URL of the zip file to download
        extract_to (Path): Directory where the zip contents should be extracted
    """
    temp_zip = extract_to / "temp_release.zip"
    with requests.get(zip_url, stream=True) as r:
        r.raise_for_status()
        with open(temp_zip, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    with zipfile.ZipFile(temp_zip, "r") as zip_ref:
        zip_ref.extractall(extract_to)
    os.remove(temp_zip)

def process_tag(repo_full_name: str, tag: dict, root_dir: Path):
    """Process a single repository tag by downloading, extracting, and cleaning files.
    
    This function:
    1. Downloads the tag's zipball
    2. Extracts it to the specified directory
    3. Moves files from nested directory to root
    4. Removes non-Python files
    5. Cleans up empty directories
    
    Args:
        repo_full_name (str): Full repository name in format 'owner/repo'
        tag (dict): Tag information dictionary
        root_dir (Path): Root directory where tag contents should be stored
    """
    tag_name = tag["name"]
    zipball_url = f"https://api.github.com/repos/{repo_full_name}/zipball/{tag_name}"
    release_dir = (root_dir / tag_name).resolve()

    if release_dir.exists():
        shutil.rmtree(release_dir)

    release_dir.mkdir(parents=True, exist_ok=True)
    print(f"⬇️ Downloading tag {tag_name} to {release_dir}")
    download_and_extract_zip(zipball_url, release_dir)

    # Move contents from nested folder up
    subdirs = list(release_dir.iterdir())
    print(f"📁 Extracted subfolders: {[str(p) for p in subdirs]}")
    if len(subdirs) == 1 and subdirs[0].is_dir():
        extracted_root = subdirs[0]
        for item in extracted_root.iterdir():
            shutil.move(str(item), str(release_dir))
        extracted_root.rmdir()

    print("🧹 Cleaning non-Python files ...")
    delete_non_python_files(release_dir)
    delete_empty_dirs(release_dir)
    print(f"✅ Tag {tag_name} processed at {release_dir}")


# ------------------------------
# ENTRY POINT
# ------------------------------
if __name__ == "__main__":
    # Validate command line arguments
    if len(sys.argv) < 3:
        print("❌ Usage: python clone_all_tags.py <GitHub repo URL> <output dir>")
        sys.exit(1)

    # Get command line arguments
    REPO_URL = sys.argv[1]
    OUTPUT_DIR = Path(sys.argv[2])

    # Validate output directory exists
    if not OUTPUT_DIR.exists():
        print(f"❌ Output directory does not exist: {OUTPUT_DIR}")
        sys.exit(1)

    # Setup target directory for the repository
    repo_full_name, short_name = get_repo_info(REPO_URL)
    TARGET_DIR = OUTPUT_DIR / short_name
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    # Fetch and process all tags
    tags = get_all_tags(repo_full_name)

    if not tags:
        print("⚠️ No tags found for this repository.")
        sys.exit(0)

    # Process each tag sequentially
    for tag in tags:
        process_tag(repo_full_name, tag, TARGET_DIR)
