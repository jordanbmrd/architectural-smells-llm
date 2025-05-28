import os
import json
import subprocess
import ast
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
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.depends_jar = "depends.jar"
        self.output_dir = "depends_output"

    def analyze_dependencies(self) -> Dict[str, Any]:
        """Run Depends analysis on the project."""
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Run Depends analysis
        cmd = [
            "java", "-jar", self.depends_jar,
            "python",  # language
            str(self.project_path),  # input dir
            "output",  # output name
            "-d", self.output_dir  # output directory
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            # Read the JSON output
            output_file = Path(self.output_dir) / "output-file.json"
            with open(output_file, 'r') as f:
                depends_data = json.load(f)
            
            return self._process_depends_output(depends_data)
        except subprocess.CalledProcessError as e:
            print(f"Error running Depends: {e.stderr}")
            return {}
        except FileNotFoundError:
            print(f"Error: Could not find output file at {output_file}")
            return {}

    def _process_depends_output(self, depends_data: Dict) -> Dict[str, Any]:
        """Process and clean up the Depends output."""
        return {
            'files': depends_data.get('files', []),
            'dependencies': depends_data.get('dependencies', []),
            'variables': depends_data.get('variables', [])
        }

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
        
        return {
            'project_name': self.project_path.name,
            'dependencies': dependencies,
            'code_structure': code_structure
        }

def main():
    project_path = "example2"
    analyzer = ProjectAnalyzer(project_path)
    
    print("Analyzing project...")
    results = analyzer.analyze()
    
    # Save results to a JSON file
    output_file = "data/project_structure.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Analysis complete. Results saved to {output_file}")

if __name__ == "__main__":
    main() 