import os
import shutil
import sys
from git import Repo
from pathlib import Path
from urllib.parse import urlparse

# ------------------------------
# FUNCTIONS
# ------------------------------

def is_python_file(path: Path) -> bool:
    """Check if a file has a .py extension."""
    return path.suffix == ".py"

def delete_non_python_files(base: Path):
    """Delete all files that are NOT .py in the given directory tree."""
    for path in base.rglob("*"):
        if path.is_file() and not is_python_file(path):
            path.unlink()
        elif path.is_dir() and not any(path.iterdir()):
            path.rmdir()

def delete_empty_dirs(base: Path):
    """Delete all empty folders, bottom-up."""
    for dir_path in sorted(base.rglob("*"), key=lambda p: -len(p.parts)):
        if dir_path.is_dir() and not any(dir_path.iterdir()):
            dir_path.rmdir()

def get_repo_name(repo_url: str) -> tuple[str, str]:
    """Extract full and short repo names from GitHub URL.

    Example:
        input:  https://github.com/user/my-repo.git
        output: ('user/my-repo', 'my-repo')
    """
    path = urlparse(repo_url).path.strip("/")
    repo_full_name = path[:-4] if path.endswith(".git") else path
    repo_short_name = repo_full_name.split("/")[-1]
    return repo_full_name, repo_short_name

def clone_and_clean(repo_url: str, root_dir: str):
    """Clone a GitHub repo, delete all non-.py files and empty folders."""
    full_name, short_name = get_repo_name(repo_url)
    dest_path = Path(root_dir) / short_name

    if dest_path.exists():
        shutil.rmtree(dest_path)  # delete existing directory

    print(f"🔄 Cloning {repo_url} into {dest_path} ...")
    Repo.clone_from(repo_url, dest_path)

    print("🧹 Deleting non-Python files ...")
    delete_non_python_files(dest_path)

    print("🧼 Removing empty directories ...")
    delete_empty_dirs(dest_path)

    print(f"✅ Cloned into: {dest_path} (from {full_name})")

# ------------------------------
# ENTRY POINT
# ------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Usage: python clone_single_repo.py <GitHub repo URL>")
        sys.exit(1)

    REPO_URL = sys.argv[1]
    ROOT_CLONE_DIR = "cloned_projects"  # parent directory for all projects

    os.makedirs(ROOT_CLONE_DIR, exist_ok=True)
    clone_and_clean(REPO_URL, ROOT_CLONE_DIR)