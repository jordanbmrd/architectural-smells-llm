import requests
import sys
from urllib.parse import urlparse
import os

def extract_repo_full_name(github_url):
    """Extract 'owner/repo' from a GitHub URL."""
    parsed_url = urlparse(github_url)
    path_parts = parsed_url.path.strip('/').split('/')
    if len(path_parts) < 2:
        raise ValueError("Invalid GitHub URL.")
    return f"{path_parts[0]}/{path_parts[1]}"

def get_first_release(repo_full_name, token=None):
    """Get the tag name and commit SHA of the first release."""
    url = f"https://api.github.com/repos/{repo_full_name}/releases"
    headers = {"Authorization": f"token {token}"} if token else {}
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        raise Exception("Failed to fetch releases.")
    releases = resp.json()
    if not releases:
        raise Exception("No releases found.")
    first_release = sorted(releases, key=lambda r: r['created_at'])[0]
    tag_name = first_release['tag_name']

    # Fetch the commit SHA corresponding to the tag
    tag_url = f"https://api.github.com/repos/{repo_full_name}/git/refs/tags/{tag_name}"
    tag_resp = requests.get(tag_url, headers=headers)
    if tag_resp.status_code != 200:
        raise Exception("Failed to fetch tag reference.")
    tag_data = tag_resp.json()

    # If the tag is annotated, we may need to resolve it
    object_data = tag_data.get('object', {})
    if object_data.get('type') == 'tag':
        annotated_tag_url = object_data['url']
        tag_obj = requests.get(annotated_tag_url, headers=headers).json()
        return tag_name, tag_obj.get('object', {}).get('sha')
    return tag_name, object_data.get('sha')

def get_python_files_from_commit(repo_full_name, sha, token=None):
    """Return a list of .py files from a given commit SHA."""
    url = f"https://api.github.com/repos/{repo_full_name}/git/trees/{sha}?recursive=1"
    headers = {"Authorization": f"token {token}"} if token else {}
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        raise Exception("Failed to fetch tree.")
    tree = resp.json().get('tree', [])
    py_files = [entry['path'] for entry in tree if entry['type'] == 'blob' and entry['path'].endswith('.py')]
    return py_files

def list_python_files_from_first_release(github_url, token=None):
    repo_full_name = extract_repo_full_name(github_url)
    print(f" full name: {repo_full_name}")
    _, sha = get_first_release(repo_full_name, token=token)
    print(f"SHA of first release: {sha}")
    py_files = get_python_files_from_commit(repo_full_name, sha, token=token)
    print(f"Found {len(py_files)} Python files.")
    return '\n'.join(py_files)



# Exemple d’utilisation :
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <github_repo_url>")
        sys.exit(1)

    github_url = sys.argv[1]
    token = None  # ou remplace par ton token GitHub ici

    try:
        repo_full_name = extract_repo_full_name(github_url)
        project_name = repo_full_name.split('/')[-1]

        result = list_python_files_from_first_release(github_url, token)

        # Créer le dossier si nécessaire
        output_dir = os.path.join("AI", "Projects-scraped", project_name)
        os.makedirs(output_dir, exist_ok=True)

        # Écrire le fichier
        output_path = os.path.join(output_dir, "files.txt")
        with open(output_path, "w") as f:
            f.write(result + "\n")

        print(f"Python files written to: {output_path}")

    except Exception as e:
        print(f"Error: {e}")

