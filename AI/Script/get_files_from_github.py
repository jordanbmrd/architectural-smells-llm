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

def get_commit_sha_from_tag(repo_full_name, tag_name, token=None):
    """Get the commit SHA corresponding to a specific tag."""
    headers = {"Authorization": f"token {token}"} if token else {}

    tag_url = f"https://api.github.com/repos/{repo_full_name}/git/refs/tags/{tag_name}"
    tag_resp = requests.get(tag_url, headers=headers)
    if tag_resp.status_code != 200:
        raise Exception(f"Failed to fetch tag reference for '{tag_name}'.")
    tag_data = tag_resp.json()

    object_data = tag_data.get('object', {})
    if object_data.get('type') == 'tag':
        annotated_tag_url = object_data['url']
        tag_obj = requests.get(annotated_tag_url, headers=headers).json()
        return tag_obj.get('object', {}).get('sha')
    return object_data.get('sha')

def get_first_release_sha(repo_full_name, token=None):
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
    sha = get_commit_sha_from_tag(repo_full_name, tag_name, token)
    return tag_name, sha

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

# Main script
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <github_repo_url> [tag_name]")
        sys.exit(1)

    github_url = sys.argv[1]
    tag_name = sys.argv[2] if len(sys.argv) > 2 else None
    token = None  # Optional: set your GitHub token here

    try:
        repo_full_name = extract_repo_full_name(github_url)
        project_name = repo_full_name.split('/')[-1]

        if tag_name:
            print(f"🔎 Getting files for tag: {tag_name}")
            sha = get_commit_sha_from_tag(repo_full_name, tag_name, token)
            final_tag_name = tag_name
        else:
            print("🔎 Getting files from first release")
            tag_name, sha = get_first_release_sha(repo_full_name, token)
            final_tag_name = tag_name  # from first release

        py_files = get_python_files_from_commit(repo_full_name, sha, token)
        print(f"✅ Found {len(py_files)} Python files.")

        # Create output directory if needed
        output_dir = os.path.join("AI", "Projects-scraped", project_name)
        os.makedirs(output_dir, exist_ok=True)

        # Write to file: files-<release>.txt
        output_filename = f"files-{final_tag_name}.txt"
        output_path = os.path.join(output_dir, output_filename)

        with open(output_path, "w") as f:
            f.write("\n".join(py_files) + "\n")

        print(f"📁 Python files written to: {output_path}")

    except Exception as e:
        print(f"❌ Error: {e}")
