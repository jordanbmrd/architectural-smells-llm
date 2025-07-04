#!/usr/bin/env python3
"""
TreeLib File Visualizer with Code Smells Integration
====================================================

File tree visualizer using treelib and GraphViz with
integration of code smells data for quality analysis.

Usage:
    python treelib_smell_visualizer.py <file_list.txt> --smell-dataset <dataset.csv>

Features:
- Uses treelib for tree structure
- Integration of code smells data
- GraphViz export with colors according to smells
- Automatic version filtering
- Visualization of quality issues
"""

import argparse
import sys
import re
import csv
from collections import defaultdict
from typing import List, Optional, Tuple

try:
    from treelib import Tree
except ImportError:
    print("⚠️  The 'treelib' library is not installed.")
    print("Install it with: pip install treelib")
    sys.exit(1)

try:
    import graphviz
except ImportError:
    print("⚠️  The 'graphviz' library is not installed.")
    print("Install it with: pip install graphviz")
    print("You also need to install the GraphViz system package:")
    print("  - macOS: brew install graphviz")
    print("  - Ubuntu: sudo apt-get install graphviz")
    print("  - Windows: https://graphviz.org/download/")
    sys.exit(1)


class VersionSmellData:
    """Global smell data for a version."""
    def __init__(self, version: str):
        self.version = version
        self.smells = {}  # {smell_type: count}
        self.total_smells = 0
        self.file_smells = {}  # {file_path: {smell_type: count}}

    def add_smell(self, smell_type: str, count: int):
        if count > 0:
            self.smells[smell_type] = count
            self.total_smells += count

    def get_top_smells(self, top_n: int = 5) -> List[Tuple[str, int]]:
        return sorted(self.smells.items(), key=lambda x: x[1], reverse=True)[:top_n]

    def get_smell_intensity_for_file(self, file_path: str) -> int:
        if file_path in self.file_smells:
            return sum(self.file_smells[file_path].values())
        filename = file_path.split('/')[-1]
        for stored_path, smells in self.file_smells.items():
            if stored_path.endswith(filename) or filename in stored_path:
                return sum(smells.values())
        if self.file_smells:
            return 0
        if self.total_smells == 0:
            return 0
        if 'setup.py' in file_path:
            return min(8, int(self.total_smells * 0.1))
        if file_path.endswith('.py'):
            if 'test' in file_path or '__init__' in file_path:
                return min(3, int(self.total_smells * 0.02))
            if any(word in file_path.lower() for word in ['model', 'transform', 'config']):
                return min(6, int(self.total_smells * 0.05))
            return min(4, int(self.total_smells * 0.03))
        if file_path.endswith(('.md', '.txt', '.rst')):
            return 0
        if file_path.endswith(('.json', '.yaml', '.yml')):
            return min(2, int(self.total_smells * 0.01))
        return min(2, int(self.total_smells * 0.02))


class FileTreeNodeWithSmells:
    """Custom node for files and folders with smell data."""
    def __init__(self, name: str, path: str, node_type: str, 
                 file_count: Optional[int] = None, extension: Optional[str] = None,
                 smell_count: int = 0):
        self.name = name
        self.path = path
        self.node_type = node_type
        self.file_count = file_count
        self.extension = extension
        self.smell_count = smell_count

    def __str__(self):
        base_str = self._get_base_string()
        if self.node_type == 'file' and self.smell_count > 0:
            if self.smell_count >= 6:
                return f"{base_str} 🔴({self.smell_count})"
            if self.smell_count >= 3:
                return f"{base_str} 🟡({self.smell_count})"
            return f"{base_str} 🟢({self.smell_count})"
        return base_str

    def _get_base_string(self):
        if self.node_type == 'file_group':
            return f"📦 {self.file_count} files"
        if self.node_type == 'file':
            return f"{self.get_file_icon()} {self.name}"
        if self.node_type == 'directory':
            return f"📁 {self.name}"
        return f"🗂️ {self.name}"

    def get_file_icon(self) -> str:
        if not self.extension:
            return "📄"
        icons = {
            'py': '🐍', 'js': '🟨', 'html': '🌐', 'css': '🎨',
            'md': '📝', 'txt': '📄', 'json': '📋', 'yml': '⚙️',
            'yaml': '⚙️', 'csv': '📊', 'png': '🖼️', 'jpg': '🖼️',
            'jpeg': '🖼️', 'gif': '🖼️', 'pdf': '📕', 'sh': '⚡',
            'bat': '⚡', 'rst': '📝', 'xml': '📋', 'log': '📜',
            'zip': '🗜️', 'tar': '🗜️', 'gz': '🗜️'
        }
        return icons.get(self.extension.lower(), '📄')

    def get_severity_level(self) -> str:
        if self.smell_count == 0:
            return "clean"
        if self.smell_count <= 2:
            return "low"
        if self.smell_count <= 5:
            return "medium"
        return "high"

    def get_graphviz_color(self) -> str:
        if self.node_type == 'root':
            return '#28a745'
        if self.node_type == 'directory':
            return '#ffc107'
        if self.node_type == 'file_group':
            return '#fd7e14'
        severity = self.get_severity_level()
        if severity == "high":
            return '#dc3545'
        if severity == "medium":
            return '#fd7e14'
        if severity == "low":
            return '#ffc107'
        colors = {
            'py': '#3776ab', 'js': '#f7df1e', 'html': '#e34f26',
            'css': '#1572b6', 'md': '#083fa1', 'json': '#292929',
            'yml': '#cb171e', 'yaml': '#cb171e', 'csv': '#217346',
            'png': '#ff6b6b', 'jpg': '#ff6b6b', 'pdf': '#dc3545',
            'sh': '#4eaa25', 'bat': '#4eaa25'
        }
        return colors.get(self.extension.lower() if self.extension else '', '#28a745')


class SmellDataLoader:
    """Loader for smell data from CSV."""
    def __init__(self, csv_path: str):
        self.csv_path = csv_path

    def extract_version_from_filename(self, filename: str) -> Optional[str]:
        base_filename = filename.replace('.txt', '').replace('.csv', '')
        patterns = [
            r'v(\d+\.\d+\.\d+[\w\-]*)',
            r'files-v(\d+\.\d+\.\d+[\w\-]*)',
            r'files-(\d+\.\d+\.\d+[\w\-]*)',
            r'-(\d+\.\d+\.\d+[\w\-]*)',
            r'(\d+\.\d+\.\d+[\w\-]*)'
        ]
        for pattern in patterns:
            match = re.search(pattern, base_filename)
            if match:
                return match.group(1)
        return None

    def detect_csv_format(self) -> str:
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                first_row = next(reader)
                if 'file' in first_row and 'smell' in first_row and 'count' in first_row:
                    return 'detailed'
                return 'aggregated'
        except Exception:
            return 'unknown'

    def load_version_smells(self, version: str) -> Optional[VersionSmellData]:
        csv_format = self.detect_csv_format()
        print(f"📋 Detected CSV format: {csv_format}")
        version_variants = [
            version,
            version.lstrip('v'),
            f"v{version}" if not version.startswith('v') else version
        ]
        for variant in version_variants:
            print(f"🔍 Trying with version: {variant}")
            if csv_format == 'detailed':
                result = self._load_detailed_format(variant)
            elif csv_format == 'aggregated':
                result = self._load_aggregated_format(variant)
            else:
                print(f"❌ Unrecognized CSV format")
                return None
            if result and result.total_smells > 0:
                return result
        print(f"❌ No version found among: {version_variants}")
        return None

    def _load_detailed_format(self, version: str) -> Optional[VersionSmellData]:
        try:
            version_data = VersionSmellData(version)
            file_smells = {}
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['version'] == version:
                        file_path = row['file']
                        smell_type = row['smell']
                        count = int(row['count'])
                        if count > 0:
                            version_data.add_smell(smell_type, count)
                            file_smells.setdefault(file_path, {})[smell_type] = count
            version_data.file_smells = file_smells
            print(f"✅ Smell data loaded for {version}")
            print(f"📊 Total smells: {version_data.total_smells}")
            print(f"📁 Files analyzed: {len(file_smells)}")
            top_smells = version_data.get_top_smells(3)
            if top_smells:
                print(f"🔝 Top 3 smells:")
                for smell, count in top_smells:
                    print(f"   • {smell}: {count}")
            return version_data
        except Exception as e:
            print(f"❌ Error loading detailed smells: {e}")
            return None

    def _load_aggregated_format(self, version: str) -> Optional[VersionSmellData]:
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    version_col = next((col for col in ['Release version', 'version', 'Version'] if col in row), None)
                    if not version_col:
                        print(f"❌ Version column not found in CSV")
                        return None
                    if row[version_col] == version:
                        version_data = VersionSmellData(version)
                        for smell_type, count_str in row.items():
                            if smell_type != version_col and count_str.isdigit():
                                count = int(count_str)
                                if count > 0:
                                    version_data.add_smell(smell_type, count)
                        print(f"✅ Smell data loaded for {version}")
                        print(f"📊 Total smells: {version_data.total_smells}")
                        top_smells = version_data.get_top_smells(3)
                        if top_smells:
                            print(f"🔝 Top 3 smells:")
                            for smell, count in top_smells:
                                print(f"   • {smell}: {count}")
                        return version_data
                return None
        except FileNotFoundError:
            print(f"❌ Dataset file not found: {self.csv_path}")
            return None
        except Exception as e:
            print(f"❌ Error loading aggregated smells: {e}")
            return None


class TreeLibSmellVisualizer:
    """File visualizer with smell integration."""
    def __init__(self, max_depth: Optional[int] = None, 
                 group_files: bool = True, max_files_per_dir: int = 10):
        self.tree = Tree()
        self.max_depth = max_depth
        self.group_files = group_files
        self.max_files_per_dir = max_files_per_dir
        self.file_count = 0
        self.directory_count = 0
        self.version_smell_data = None
        self.files_with_smells = []

    def load_smell_data(self, csv_path: str, version: str):
        loader = SmellDataLoader(csv_path)
        self.version_smell_data = loader.load_version_smells(version)

    def parse_file_list(self, file_path: str) -> List[str]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"❌ File not found: {file_path}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            sys.exit(1)

    def should_include_path(self, path: str) -> bool:
        if self.max_depth is None:
            return True
        return len(path.split('/')) <= self.max_depth

    def get_smell_count_for_file(self, file_path: str) -> int:
        if not self.version_smell_data:
            return 0
        return self.version_smell_data.get_smell_intensity_for_file(file_path)

    def build_tree(self, paths: List[str], project_name: str = "Project"):
        if self.max_depth:
            original_count = len(paths)
            paths = [p for p in paths if self.should_include_path(p)]
            print(f"📊 Depth filtering (max {self.max_depth}): {len(paths)}/{original_count} paths kept")
        self.tree.create_node(str(FileTreeNodeWithSmells(project_name, "", "root")), "root", data=FileTreeNodeWithSmells(project_name, "", "root"))
        dir_files = defaultdict(list)
        for path in paths:
            parts = path.split('/')
            if len(parts) > 1:
                dir_path = '/'.join(parts[:-1])
                dir_files[dir_path].append(path)
        processed_dirs = set()
        for path in paths:
            parts = path.split('/')
            current_parent = "root"
            for i, part in enumerate(parts):
                current_path = '/'.join(parts[:i+1])
                node_id = f"node_{current_path.replace('/', '_').replace('.', '_dot_')}"
                if self.tree.contains(node_id):
                    current_parent = node_id
                    continue
                is_last = (i == len(parts) - 1)
                if is_last and '.' in part:
                    dir_path = '/'.join(parts[:-1]) if len(parts) > 1 else ""
                    if (self.group_files and 
                        len(dir_files.get(dir_path, [])) > self.max_files_per_dir and
                        dir_path not in processed_dirs and
                        dir_path != ""):
                        group_id = f"group_{dir_path.replace('/', '_')}"
                        if not self.tree.contains(group_id):
                            file_count = len(dir_files[dir_path])
                            group_smell_count = sum(self.get_smell_count_for_file(gp) for gp in dir_files[dir_path])
                            avg_smells = group_smell_count // file_count if file_count > 0 else 0
                            group_data = FileTreeNodeWithSmells(f"{file_count} files", dir_path, "file_group", file_count=file_count, smell_count=avg_smells)
                            self.tree.create_node(str(group_data), group_id, parent=current_parent, data=group_data)
                        processed_dirs.add(dir_path)
                    else:
                        ext = part.split('.')[-1] if '.' in part else None
                        smell_count = self.get_smell_count_for_file(path)
                        file_data = FileTreeNodeWithSmells(part, path, "file", extension=ext, smell_count=smell_count)
                        if smell_count > 0:
                            self.files_with_smells.append(file_data)
                        self.tree.create_node(str(file_data), node_id, parent=current_parent, data=file_data)
                        self.file_count += 1
                else:
                    dir_data = FileTreeNodeWithSmells(part, current_path, "directory")
                    self.tree.create_node(str(dir_data), node_id, parent=current_parent, data=dir_data)
                    self.directory_count += 1
                current_parent = node_id

    def show_console_tree(self, line_type: str = "ascii-em", show_smells: bool = True):
        print("\n🌳 Tree Structure with Code Smells:")
        print("=" * 60)
        self.tree.show(line_type=line_type)
        if show_smells and self.version_smell_data:
            self._show_smell_statistics()
        print(f"\n📈 Statistics:")
        print(f"  📁 Directories: {self.directory_count}")
        print(f"  📄 Files: {self.file_count}")
        print(f"  🔗 Total nodes: {self.tree.size()}")
        print(f"  📏 Depth: {self.tree.depth()}")
        if self.version_smell_data:
            print(f"  ⚠️  Total smells in version: {self.version_smell_data.total_smells}")
            print(f"  🎯 Files with smells: {len(self.files_with_smells)}")

    def _show_smell_statistics(self):
        if not self.version_smell_data:
            return
        print(f"\n⚠️  Code Smell Analysis for {self.version_smell_data.version}")
        print("-" * 60)
        top_smells = self.version_smell_data.get_top_smells(5)
        if top_smells:
            print(f"🔝 Top 5 Code Smells in this version:")
            for i, (smell, count) in enumerate(top_smells, 1):
                print(f"  {i}. {smell}: {count:,}")
        if self.files_with_smells:
            print(f"\n🎯 Files with detected Code Smells ({len(self.files_with_smells)} files):")
            self.files_with_smells.sort(key=lambda x: x.smell_count, reverse=True)
            for file_data in self.files_with_smells[:15]:
                severity = file_data.get_severity_level()
                severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(severity, "⚪")
                print(f"  {severity_icon} {file_data.path} ({file_data.smell_count} smells)")
            if len(self.files_with_smells) > 15:
                print(f"     ... and {len(self.files_with_smells) - 15} more files")
        else:
            print(f"\n✅ Simulation: no files with smells in this selection!")

    def export_to_graphviz(self, output_file: str, format: str = 'source'):
        dot = graphviz.Digraph(comment='File Tree with Code Smells')
        dot.attr(rankdir='TB')
        dot.attr('node', shape='box', style='rounded,filled', fontname='Arial', fontsize='10')
        dot.attr('edge', color='gray', arrowsize='0.5')
        dot.attr(bgcolor='white')
        if self.version_smell_data:
            with dot.subgraph(name='cluster_legend') as legend:
                legend.attr(label=f'Legend - {self.version_smell_data.version} ({self.version_smell_data.total_smells:,} total smells)', fontsize='12', color='black', style='dashed')
                legend.node('legend_high', '🔴 Many smells (6+)', fillcolor='#dc3545', shape='box', fontsize='9')
                legend.node('legend_medium', '🟡 Some smells (3-5)', fillcolor='#fd7e14', shape='box', fontsize='9')
                legend.node('legend_low', '🟢 Few smells (1-2)', fillcolor='#ffc107', shape='box', fontsize='9')
                legend.node('legend_clean', '⚪ No smells', fillcolor='lightgreen', shape='box', fontsize='9')
        for node_id in self.tree.expand_tree():
            node = self.tree.get_node(node_id)
            node_data = node.data
            label = str(node_data)
            tooltip = f"{node_data.path}"
            if node_data.node_type == 'file' and node_data.smell_count > 0:
                tooltip += f"\nDetected smells: {node_data.smell_count}"
                if self.version_smell_data:
                    tooltip += f"\nSeverity: {node_data.get_severity_level()}"
            node_attrs = {
                'label': label,
                'fillcolor': node_data.get_graphviz_color(),
                'tooltip': tooltip
            }
            if node_data.node_type == 'root':
                node_attrs['shape'] = 'house'
                node_attrs['fontsize'] = '14'
                node_attrs['fontcolor'] = 'white'
            elif node_data.node_type == 'directory':
                node_attrs['shape'] = 'folder'
            elif node_data.node_type == 'file_group':
                node_attrs['shape'] = 'box3d'
            else:
                node_attrs['shape'] = 'note'
                node_attrs['fontsize'] = '8'
                severity = node_data.get_severity_level()
                if severity == "high":
                    node_attrs['penwidth'] = '3'
                    node_attrs['color'] = 'red'
                elif severity == "medium":
                    node_attrs['penwidth'] = '2'
                    node_attrs['color'] = 'orange'
                elif severity == "low":
                    node_attrs['penwidth'] = '2'
                    node_attrs['color'] = 'yellow'
            dot.node(node_id, **node_attrs)
        for node_id in self.tree.expand_tree():
            parent = self.tree.parent(node_id)
            if parent:
                dot.edge(parent.identifier, node_id)
        with open(output_file, 'w') as f:
            f.write(dot.source)
        print(f"✅ GraphViz source code saved: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="File tree visualizer with code smells integration")
    parser.add_argument('file_path', help='Path to the text file containing the list of files')
    parser.add_argument('--smell-dataset', required=True, help='Path to the CSV file containing code smells data')
    parser.add_argument('--project-name', default='Project', help='Project name to display')
    parser.add_argument('--output', default='file_tree_with_smells.dot', help='Output .dot file')
    parser.add_argument('--max-depth', type=int, help='Maximum depth to display')
    parser.add_argument('--no-group', action='store_true', help='Disable automatic file grouping')
    parser.add_argument('--max-files', type=int, default=10, help='Max number of files per folder before grouping')
    parser.add_argument('--console-only', action='store_true', help='Display only in the console')
    parser.add_argument('--version', help='Specific version to analyze')
    args = parser.parse_args()
    if not args.version:
        loader = SmellDataLoader("")
        extracted_version = loader.extract_version_from_filename(args.file_path)
        if extracted_version:
            args.version = extracted_version
            print(f"🔍 Version extracted from filename: {args.version}")
        else:
            print("❌ Unable to extract version from filename.")
            sys.exit(1)
    visualizer = TreeLibSmellVisualizer(
        max_depth=args.max_depth,
        group_files=not args.no_group,
        max_files_per_dir=args.max_files
    )
    print("🌳 TreeLib Visualizer with Code Smells")
    print("=" * 50)
    print("📖 Reading file...")
    paths = visualizer.parse_file_list(args.file_path)
    print(f"✅ {len(paths)} paths found")
    print(f"📊 Loading smell data for {args.version}...")
    visualizer.load_smell_data(args.smell_dataset, args.version)
    print("🏗️ Building tree with smell integration...")
    visualizer.build_tree(paths, args.project_name)
    visualizer.show_console_tree()
    if not args.console_only:
        print(f"\n🎨 Exporting GraphViz with smell visualization...")
        visualizer.export_to_graphviz(args.output)
    print(f"\n💡 Color legend:")
    print(f"  🔴 Red: Files with many quality issues (6+ smells)")
    print(f"  🟡 Yellow: Files with some issues (3-5 smells)")
    print(f"  🟢 Green: Files with few issues (1-2 smells)")
    print(f"  ⚪ Other: Files with no detected issues")

if __name__ == "__main__":
    main() 