import csv
import sys
import os

# Mapping des patterns de sous-types
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

def detect_subtype(file_path):
    if not file_path:
        return "Unclassified"
    lowered = file_path.lower()
    for subtype, patterns in subtype_patterns.items():
        for pattern in patterns:
            if pattern in lowered:
                return subtype
    return "Unclassified"

def main():
    if len(sys.argv) != 3:
        print("Usage: python filter_and_tag_subtype.py <input_csv> <target_version>")
        sys.exit(1)

    input_csv = sys.argv[1]
    target_version = sys.argv[2]

    # Nom du projet = nom du fichier sans extension
    project_name = os.path.splitext(os.path.basename(input_csv))[0]
    output_dir = "AI/EDA/multiple-linear-regression-3"
    output_csv = os.path.join(output_dir, f"{project_name}.csv")

    os.makedirs(output_dir, exist_ok=True)

    with open(input_csv, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        required_fields = ["version", "file", "has_smell"]

        if not all(field in reader.fieldnames for field in required_fields):
            print(f"Erreur : le fichier CSV doit contenir les colonnes : {required_fields}")
            sys.exit(1)

        rows_to_write = []

        for row in reader:
            if row["version"] == target_version:
                file_path = row["file"]
                smell_count = row["has_smell"]
                subtype = detect_subtype(file_path)

                rows_to_write.append({
                    "version": target_version,
                    "file_path": file_path,
                    "smell_count": smell_count,
                    "subtype": subtype
                })

    with open(output_csv, mode='w', newline='', encoding='utf-8') as outfile:
        fieldnames = ["version", "file_path", "smell_count", "subtype"]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_to_write)

    print(f"{len(rows_to_write)} lignes écrites dans {output_csv}")

if __name__ == "__main__":
    main()
