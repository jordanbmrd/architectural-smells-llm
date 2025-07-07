#!/usr/bin/env python3
"""
Clone, clean, and analyze all tagged releases of a GitHub repo.
Keeps only Python files, generates `files.txt` and `code_quality_report.csv` per release.
Moves cleaned project to `AI/Projects-scraped/<project_name>/`.
"""

import os
import sys
import shutil
import zipfile
import subprocess
import requests
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

def clean_and_list_py_files(base_dir):
    py_files = []
    for path in list(base_dir.rglob("*")):
        if path.is_file() and path.suffix == ".py":
            py_files.append(path.relative_to(base_dir))
        elif path.is_file():
            path.unlink()
    for d in sorted(base_dir.rglob("*"), key=lambda p: -len(p.parts)):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
    with open(base_dir / "files.txt", "w") as f:
        f.write("\n".join(str(p) for p in sorted(py_files)))

def run_analysis(release_dir):
    script = Path(__file__).parent / "run_analysis.sh"
    subprocess.run([str(script), str(release_dir)], cwd=Path(__file__).parent, check=True)

def keep_only_outputs(release_dir):
    for item in release_dir.iterdir():
        if item.name not in {"code_quality_report.csv", "files.txt"}:
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
    if len(sys.argv) != 2:
        print("Usage: python clone_and_clean_releases.py <GitHub repo URL>")
        sys.exit(1)

    repo_url = sys.argv[1]
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
