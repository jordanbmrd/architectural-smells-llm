import os
import json
import subprocess
import ast
import shutil
from typing import Dict, List, Any, Set
from pathlib import Path

class FunctionVisitor(ast.NodeVisitor):
    def __init__(self):
        self.functions = []
        self.classes = []
        self._current_class = None

    def visit_ClassDef(self, node):
        prev_class = self._current_class
        self._current_class = node
        
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append({
                    'name': item.name,
                    'line_number': item.lineno,
                    'args': [arg.arg for arg in item.args.args if arg.arg != 'self']
                })
        
        self.classes.append({
            'name': node.name,
            'methods': methods,
            'line_number': node.lineno
        })
        
        self._current_class = prev_class
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        if self._current_class is None:  # Only collect top-level functions
            self.functions.append({
                'name': node.name,
                'line_number': node.lineno,
                'args': [arg.arg for arg in node.args.args]
            })
        self.generic_visit(node)

class ProjectAnalyzer:
    def __init__(self, project_path: str, output_dir: str = "data"):
        self.project_path = Path(project_path)
        self.depends_jar = "./depends.jar"  # Make sure to use relative path
        self.output_dir = Path(output_dir)
        self.temp_dir = self.output_dir / "depends_temp"
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)

    def analyze_dependencies(self) -> Dict[str, Any]:
        """Run Depends analysis on the project."""
        try:
            # 1. Generate main dependencies file
            print("\n1. Generating main dependencies file...")
            cmd_deps = [
                "java", "-jar", self.depends_jar,
                "python",  # language
                str(self.project_path),  # input dir
                str(self.output_dir / "dependencies"),  # output file
                "-f", "json",  # format
                "--auto-include"  # auto include dependencies
            ]
            
            print(f"Running command: {' '.join(cmd_deps)}")
            result = subprocess.run(cmd_deps, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"Error generating dependencies: {result.stderr}")
                return {}
            
            # 2. Generate detailed dependencies
            print("\n2. Generating detailed dependencies file...")
            cmd_details = [
                "java", "-jar", self.depends_jar,
                "python",  # language
                str(self.project_path),  # input dir
                str(self.output_dir / "dependencies_details"),  # output file
                "-f", "json",  # format
                "--auto-include",  # auto include dependencies
                "--detail"  # include details
            ]
            
            print(f"Running command: {' '.join(cmd_details)}")
            result = subprocess.run(cmd_details, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"Error generating detailed dependencies: {result.stderr}")
            
            # 3. Generate dependency graph
            print("\n3. Generating dependency graph...")
            cmd_graph = [
                "java", "-jar", self.depends_jar,
                "python",  # language
                str(self.project_path),  # input dir
                str(self.output_dir / "dependency_graph"),  # output file
                "-f", "dot",  # format
                "--auto-include"  # auto include dependencies
            ]
            
            print(f"Running command: {' '.join(cmd_graph)}")
            result = subprocess.run(cmd_graph, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"Error generating dependency graph: {result.stderr}")
            
            # Verify files exist
            files_to_check = [
                ("dependencies-file.json", True),  # (filename, is_required)
                ("dependencies_details-file.json", False),
                ("dependency_graph-file.dot", False)
            ]
            
            for filename, is_required in files_to_check:
                file_path = self.output_dir / filename
                if not file_path.exists():
                    print(f"Warning: {filename} was not generated")
                    if is_required:
                        return {}
            
            # Read the main dependencies file
            with open(self.output_dir / "dependencies-file.json", 'r') as f:
                depends_data = json.load(f)
            
            if not depends_data:
                print("Warning: Dependencies file is empty")
            
            return self._process_depends_output(depends_data)
            
        except subprocess.CalledProcessError as e:
            print(f"Error running Depends: {e.stderr}")
            return {}
        except FileNotFoundError as e:
            print(f"Error: Could not find file: {e}")
            return {}
        except Exception as e:
            print(f"Error during dependency analysis: {str(e)}")
            return {}

    def _process_depends_output(self, depends_data: Dict) -> Dict[str, Any]:
        """Process and clean up the Depends output."""
        processed = {
            'files': depends_data.get('files', []),
            'dependencies': depends_data.get('dependencies', []),
            'variables': depends_data.get('variables', [])
        }
        
        # Print some debug info
        print("\nProcessed dependencies:")
        print(f"- Number of files: {len(processed['files'])}")
        print(f"- Number of dependencies: {len(processed['dependencies'])}")
        print(f"- Number of variables: {len(processed['variables'])}")
        
        return processed

    def extract_code_structure(self) -> Dict[str, Any]:
        """Extract classes and methods from Python files."""
        structure = {}
        
        for py_file in self.project_path.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                
                visitor = FunctionVisitor()
                visitor.visit(tree)
                
                file_structure = {
                    'classes': visitor.classes,
                    'functions': visitor.functions
                }
                
                relative_path = py_file.relative_to(self.project_path)
                structure[str(relative_path)] = file_structure
                
            except Exception as e:
                print(f"Error processing {py_file}: {str(e)}")
                
        return structure

    def analyze(self) -> Dict[str, Any]:
        """Perform complete analysis of the project."""
        dependencies = self.analyze_dependencies()
        code_structure = self.extract_code_structure()
        
        # Save results to JSON files            
        with open(self.output_dir / "project_structure.json", 'w') as f:
            json.dump({
                'project_name': self.project_path.name,
                'dependencies': dependencies,
                'code_structure': code_structure
            }, f, indent=2)
        
        return {
            'project_name': self.project_path.name,
            'dependencies': dependencies,
            'code_structure': code_structure
        }

def analyze_project(project_path: str, output_dir: str = "data") -> Dict[str, Any]:
    """Analyze a project at the given path."""
    analyzer = ProjectAnalyzer(project_path, output_dir)
    print(f"Analyzing project at {project_path}...")
    return analyzer.analyze()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        project_path = sys.argv[1]
        analyze_project(project_path)
    else:
        print("Please provide a project path as argument") 