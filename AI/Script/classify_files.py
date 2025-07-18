import requests
import re
import matplotlib.pyplot as plt
from collections import Counter
import os
from dotenv import load_dotenv

load_dotenv()

# Dictionary of patterns for each subtype
subtype_patterns = {
    "Core": ["src/", "lib/", "app/", "main/", "core/"],
    "Config": ["setup.py", "setup.cfg", "pyproject.toml", "requirements", ".env", "config", "configs", "settings"],
    "Tests": ["tests/", "test/", "spec/"],
    "Docs": ["docs/", "README", "CONTRIBUTING", "CHANGELOG", "LICENSE"],
    "Utils": ["scripts/", "utils/", "bin/", "tools/", "examples/"],
    "Data": ["data/", "assets/", "resources/", "templates/"],
    "UI": ["ui/", "frontend/", "webapp/", "static/", "public/"],
    "Backend": ["server/", "api/", "backend/", "services/"],
    "Build": ["build/", "dist/", "release/", "packaging/", "MANIFEST.in"],
    "Deps": ["vendor/", "third_party/", "external/", "node_modules/", "libs/"]
}

def get_subtype(filepath):
    lowered = filepath.lower()
    for subtype, patterns in subtype_patterns.items():
        for pattern in patterns:
            if pattern.lower() in lowered:
                return subtype
    return "Unclassified"

def parse_github_url(url):
    m = re.match(r'https?://github.com/([^/]+)/([^/]+)', url)
    if not m:
        raise ValueError("Invalid GitHub URL.")
    return m.group(1), m.group(2).replace('.git', '')

def list_repo_files(owner, repo, token=None):
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    for branch in ["main", "master"]:
        r = requests.get(f"https://api.github.com/repos/{owner}/{repo}/branches/{branch}", headers=headers)
        if r.status_code == 200:
            sha = r.json()["commit"]["commit"]["tree"]["sha"]
            break
    else:
        raise Exception("Unable to detect the main branch (main/master).")
    tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{sha}?recursive=1"
    r = requests.get(tree_url, headers=headers)
    if r.status_code != 200:
        raise Exception("Unable to retrieve the Git tree.")
    tree = r.json()["tree"]
    return [item["path"] for item in tree if item["type"] == "blob"]

def plot_subtype_distribution(classified_files):
    subtype_counts = Counter([subtype for _, subtype in classified_files])
    subtypes = list(subtype_counts.keys())
    counts = [subtype_counts[s] for s in subtypes]

    plt.figure(figsize=(10, 6))
    plt.barh(subtypes, counts, color='skyblue')
    for i, v in enumerate(counts):
        plt.text(v + max(counts)*0.01, i, str(v), va='center', fontsize=8)
    plt.xlabel('Number of files')
    plt.ylabel('Subtype')
    plt.title('Distribution of files by subtype')
    plt.tight_layout()
    plt.show()

def classify_repo(url, token=None, plot=True):
    if token is None:
        token = os.getenv("GITHUB_TOKEN")
    owner, repo = parse_github_url(url)
    files = list_repo_files(owner, repo, token)
    # Keep only Python files
    python_files = [f for f in files if f.lower().endswith('.py')]
    classified = [(f, get_subtype(f)) for f in python_files]
    for f, tag in classified:
        print(f"{f} => {tag}")
    if plot:
        plot_subtype_distribution(classified)

if __name__ == "__main__":
    repo_url = input("Enter the GitHub repo URL: ")
    classify_repo(repo_url)
