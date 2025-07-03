import os
import sys
import requests
from urllib.parse import urlparse

def extract_repo_full_name(github_url):
    path = urlparse(github_url).path.strip("/")
    parts = path.split("/")
    if len(parts) < 2:
        raise ValueError("Invalid GitHub URL format.")
    owner, repo = parts[:2]
    repo = repo.replace(".git", "")
    return f"{owner}/{repo}"


def get_all_tags_with_shas(repo_full_name, token=None):
    tags = []
    page = 1
    headers = {"Authorization": f"token {token}"} if token else {}
    while True:
        url = f"https://api.github.com/repos/{repo_full_name}/tags"
        print(f"🔗 Calling GitHub API: https://api.github.com/repos/{repo_full_name}/tags")
        response = requests.get(url, headers=headers, params={"per_page": 100, "page": page})
        if response.status_code != 200:
            raise Exception(f"Failed to fetch tags: {response.status_code}")
        page_tags = response.json()
        if not page_tags:
            break
        tags.extend([(t["name"], t["commit"]["sha"]) for t in page_tags])
        page += 1
    return tags[::-1]  # Oldest to newest

def get_python_files_from_sha(repo_full_name, sha, token=None):
    url = f"https://api.github.com/repos/{repo_full_name}/git/trees/{sha}?recursive=1"
    headers = {"Authorization": f"token {token}"} if token else {}
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        raise Exception(f"Failed to fetch tree for SHA {sha}")
    tree = resp.json().get('tree', [])
    return [entry['path'] for entry in tree if entry['type'] == 'blob' and entry['path'].endswith('.py')]

def save_files_list(project_name, tag_name, py_files):
    tag_folder = os.path.join("AI", "Projects-scraped", project_name, f"v{tag_name}")
    os.makedirs(tag_folder, exist_ok=True)
    output_path = os.path.join(tag_folder, "files.txt")
    with open(output_path, "w") as f:
        f.write("\n".join(py_files) + "\n")
    print(f"✅ Saved {len(py_files)} .py files for tag {tag_name} at {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Usage: python script.py <GitHub repo URL> [optional_tag]")
        sys.exit(1)

    github_url = sys.argv[1]
    tag_name_arg = sys.argv[2] if len(sys.argv) > 2 else None
    token = None  # Set your GitHub token here if needed

    try:
        repo_full_name = extract_repo_full_name(github_url)
        project_name = repo_full_name.split("/")[-1]

        if tag_name_arg:
            print(f"🔎 Getting files for specific tag: {tag_name_arg}")
            all_tags = get_all_tags_with_shas(repo_full_name, token)
            tag_dict = dict(all_tags)
            if tag_name_arg not in tag_dict:
                raise Exception(f"Tag {tag_name_arg} not found.")
            sha = tag_dict[tag_name_arg]
            py_files = get_python_files_from_sha(repo_full_name, sha, token)
            save_files_list(project_name, tag_name_arg, py_files)
        else:
            print("🔎 No tag provided. Processing all tags...")
            all_tags = get_all_tags_with_shas(repo_full_name, token)
            if not all_tags:
                print("⚠️ No tags found.")
                sys.exit(0)
            for tag_name, sha in all_tags:
                try:
                    print(f"📦 Processing tag: {tag_name}")
                    py_files = get_python_files_from_sha(repo_full_name, sha, token)
                    save_files_list(project_name, tag_name, py_files)
                except Exception as e:
                    print(f"⚠️ Skipping tag '{tag_name}' due to error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
