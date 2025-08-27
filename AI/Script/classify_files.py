import requests
import re
import matplotlib.pyplot as plt
from collections import Counter
import csv
import sys

# Dictionary of patterns for each subtype
subtype_patterns = {
    "Core": ["src/", "lib/", "app/", "main/", "core/"],
    "Config": ["setup.py", "setup.cfg", "pyproject.toml", "requirements", ".env", "config", "configs", "settings"],
    "Tests": ["tests/", "test/", "spec/"],
    "Docs": ["docs/", "README", "CONTRIBUTING", "CHANGELOG", "LICENSE", "CODE_OF_CONDUCT", "USAGE"],
    "Utils": ["scripts/", "utils/", "bin/", "tools/", "examples/", "update_deps.py"],
    "Data": ["data/", "assets/", "resources/", "templates/"],
    "UI": ["ui/", "frontend/", "webapp/", "static/", "public/"],
    "Backend": ["server/", "api/", "backend/", "services/"],
    "Build": ["build/", "dist/", "release/", "packaging/", "MANIFEST.in"],
    "Deps": ["vendor/", "third_party/", "external/", "node_modules/", "libs/", "requirements/"],
    "Docker": ["Dockerfile", "docker-compose.yml", "Dockerfile.*"],
    "Plugins": ["plugins/"]
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
    owner, repo = parse_github_url(url)
    files = list_repo_files(owner, repo, token)
    # Keep only Python files
    python_files = [f for f in files if f.lower().endswith('.py')]
    classified = [(f, get_subtype(f)) for f in python_files]
    for f, tag in classified:
        print(f"{f} => {tag}")
    if plot:
        plot_subtype_distribution(classified)

def classify_csv(input_csv_path, output_csv_path, plot=True):
    classified_files = []
    with open(input_csv_path, newline='', encoding='utf-8') as infile, open(output_csv_path, 'w', newline='', encoding='utf-8') as outfile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames + ['subtype']
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in reader:
            file_path = row['path']
            subtype = get_subtype(file_path)
            row['subtype'] = subtype
            writer.writerow(row)
            classified_files.append((file_path, subtype))
    
    if plot:
        plot_subtype_distribution(classified_files)

if __name__ == "__main__":
    if len(sys.argv) not in [3, 4]:
        print("Usage: python classify_files.py <input_csv_path> <output_csv_path> [--no-plot]")
        sys.exit(1)
    input_csv = sys.argv[1]
    output_csv = sys.argv[2]
    plot = True
    if len(sys.argv) == 4 and sys.argv[3] == '--no-plot':
        plot = False
    classify_csv(input_csv, output_csv, plot)
