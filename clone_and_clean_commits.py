#!/usr/bin/env python3

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

def get_all_commits(repo_full_name: str) -> list[dict]:
    commits_url = f"https://api.github.com/repos/{repo_full_name}/commits"
    commits = []
    page = 1
    while True:
        response = requests.get(commits_url, params={"per_page": 100, "page": page})
        response.raise_for_status()
        page_data = response.json()
        if not page_data:
            break
        commits.extend(page_data)
        page += 1
    return commits[::-1]  # Oldest to newest

def download_and_extract_zip(zip_url: str, extract_to: Path):
    temp_zip = extract_to / "temp_commit.zip"
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

def process_commit(repo_full_name: str, commit_sha: str, commit_index: int, root_dir: Path):
    commit_dir = root_dir / f"commit-{commit_index}"
    zipball_url = f"https://api.github.com/repos/{repo_full_name}/zipball/{commit_sha}"

    if commit_dir.exists():
        shutil.rmtree(commit_dir)
    commit_dir.mkdir(parents=True, exist_ok=True)

    print(f"⬇️ Downloading commit #{commit_index} ({commit_sha})")
    download_and_extract_zip(zipball_url, commit_dir)

    # Move nested folder content up
    subdirs = list(commit_dir.iterdir())
    if len(subdirs) == 1 and subdirs[0].is_dir():
        for item in subdirs[0].iterdir():
            shutil.move(str(item), str(commit_dir))
        subdirs[0].rmdir()

    print(f"🧹 Cleaning non-Python files in commit-{commit_index}")
    delete_non_python_files(commit_dir)
    delete_empty_dirs(commit_dir)

    print(f"🚀 Running analysis for commit-{commit_index}")
    subprocess.run(["./run_analysis.sh", str(commit_dir)], cwd=Path.cwd(), check=True)

    print(f"🧼 Cleaning folder after analysis...")
    for item in commit_dir.iterdir():
        if item.name != "code_quality_report.csv":
            if item.is_file():
                item.unlink()
            else:
                shutil.rmtree(item)
    print(f"✅ Done with commit-{commit_index}\n")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("❌ Usage: python clone_and_analyze_commits.py <GitHub repo URL>")
        sys.exit(1)

    repo_url = sys.argv[1]
    repo_full_name, short_name = get_repo_info(repo_url)
    output_root = Path.cwd() / (short_name + "_commits")
    output_root.mkdir(parents=True, exist_ok=True)

    commits = get_all_commits(repo_full_name)
    if not commits:
        print("⚠️ No commits found.")
        sys.exit(0)

    print(f"✅ Found {len(commits)} commits. Processing 1 every 50 commits.\n")

    for idx, commit in enumerate(commits):
        if idx % 50 != 0:
            continue
        sha = commit["sha"]
        try:
            process_commit(repo_full_name, sha, idx, output_root)
        except Exception as e:
            print(f"⚠️ Skipping commit-{idx} due to error: {e}\n")
