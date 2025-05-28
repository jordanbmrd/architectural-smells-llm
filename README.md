# Python Project Analyzer

This tool analyzes Python projects to extract:
1. Project dependencies using Depends
2. Class and method definitions using AST parsing

## Prerequisites

- Python 3.7+
- Java Runtime Environment (JRE) for running Depends
- The Depends JAR file in the same directory

## Setup

1. Install the required Python packages:
```bash
pip install -r requirements.txt
```

2. Make sure `depends.jar` is in the same directory as `analyze_project.py`

## Usage

1. Place your Python project in a directory named `test-project`
2. Run the analyzer:
```bash
python analyze_project.py
```

The script will:
1. Analyze dependencies using Depends
2. Extract class and method definitions
3. Save the results in `project_analysis.json`

## Output Format

The output JSON file contains:
- `project_name`: Name of the analyzed project
- `dependencies`: Dependencies found by Depends
  - `files`: List of analyzed files
  - `dependencies`: Inter-file dependencies
  - `variables`: Variable usage information
- `code_structure`: AST-based code structure
  - File paths as keys
  - For each file:
    - `classes`: List of classes with their methods
    - `functions`: List of top-level functions

The output is optimized for further processing by LLMs. 