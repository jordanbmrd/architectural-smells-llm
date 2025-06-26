import os
import json
import dotenv
import tempfile
import shutil
from pathlib import Path
import subprocess
from openai import OpenAI
from typing import Dict, List, Optional, Set, Tuple
import networkx as nx
import pydot
from analyze_project import analyze_project
from prepare_project import clone_and_clean, get_repo_name

# Load environment variables from .env file
dotenv.load_dotenv()

API_KEY = os.getenv("XAI_API_KEY")
if API_KEY is None:
    raise ValueError("XAI_API_KEY environment variable is not set in .env file")

# Initialize the OpenAI client with Grok's base URL
client = OpenAI(
    api_key=API_KEY,
    base_url="https://api.x.ai/v1"
)

def clone_repository(repo_url: str) -> str:
    """Clone a GitHub repository to the current directory and return its path."""
    # Extract repository name from URL
    repo_name = repo_url.split('/')[-1].replace('.git', '')
    repo_path = os.path.join(os.getcwd(), repo_name)
    
    # Remove directory if it already exists
    if os.path.exists(repo_path):
        shutil.rmtree(repo_path)
    
    try:
        # Clone the repository
        subprocess.run(["git", "clone", repo_url], check=True, capture_output=True, text=True)
        return repo_path
    except subprocess.CalledProcessError as e:
        print(f"Error cloning repository: {e.stderr}")
        if os.path.exists(repo_path):
            shutil.rmtree(repo_path)
        raise

def detect_cyclic_dependencies(dot_file_path: str) -> List[List[str]]:
    """
    Detect cyclic dependencies in a DOT file using NetworkX.
    
    Args:
        dot_file_path: Path to the DOT file containing the dependency graph
        
    Returns:
        List of cycles, where each cycle is a list of component names forming the cycle
    """
    try:
        # Read the DOT file using pydot
        graphs = pydot.graph_from_dot_file(dot_file_path)
        if not graphs:
            print("No graph found in DOT file")
            return []
            
        # Get the first graph (DOT files can contain multiple graphs)
        dot_graph = graphs[0]
        
        # Create a NetworkX directed graph
        graph = nx.DiGraph()
        
        # Add nodes
        for node in dot_graph.get_nodes():
            node_name = node.get_name().strip('"')
            graph.add_node(node_name)
        
        # Add edges
        for edge in dot_graph.get_edges():
            source = edge.get_source().strip('"')
            target = edge.get_destination().strip('"')
            graph.add_edge(source, target)
        
        # Find all simple cycles in the graph
        cycles = list(nx.simple_cycles(graph))
        
        # Sort cycles by length for better readability
        cycles.sort(key=len)
        
        return cycles
    except Exception as e:
        print(f"Error detecting cyclic dependencies: {e}")
        return []

def analyze_architecture_with_grok(
    dependencies_json_path: str,
    project_structure_json_path: str,
    dependency_graph_path: Optional[str] = None,
    dependencies_details_path: Optional[str] = None
) -> Optional[Dict]:
    """
    Analyze software architecture using Grok API
    
    Args:
        dependencies_json_path: Path to main dependencies JSON file
        project_structure_json_path: Path to project structure JSON file
        dependency_graph_path: Optional path to DOT file containing dependency graph
        dependencies_details_path: Optional path to detailed dependencies JSON file
    
    Returns:
        Dict containing the analysis results
    """
    
    # Detect cyclic dependencies if graph is provided
    cycles = []
    if dependency_graph_path:
        cycles = detect_cyclic_dependencies(dependency_graph_path)
        print(f"Found {len(cycles)} cyclic dependencies in the graph")
        print(cycles)
    
    # Define the architectural analysis prompt
    initial_prompt = '''
You are an expert software architect analyzing codebases for structural issues. Use the provided cyclic dependencies information and analyze the high-level dependencies and project structure to identify other potential issues.

Input Data:
1. High-level Dependencies:
   - Dependency types: Call, Import, Create, Extend, Implement, Parameter, Return, Use, Contain, Cast, Throw
   - Source→Target pairs with frequency counts

2. Project Structure (AST-derived):
   - File/Class/Method hierarchy
   - Component boundaries and interfaces

3. Pre-detected Cyclic Dependencies:
{cycles}

Analysis Tasks:

1. For each detected cycle:
   - Assess the severity based on:
     * Number of components involved
     * Types of dependencies between components
     * Whether it crosses architectural boundaries
     * Impact on maintainability and modularity
   - Suggest specific refactoring strategies
   - Identify which components should be prioritized for breaking the cycle

2. Other Architectural Issues:
   God Component:
   - High number of incoming/outgoing dependencies (>15)
   - Large file size or class count
   - Multiple unrelated responsibilities
   - High coupling with many other components

   Hub-Like Dependency:
   - Component with high fan-in and fan-out
   - Central point of communication
   - Many other components depend on it

   Unstable Dependency:
   - Stability metrics (I = Ce/(Ca+Ce))
   - Components depending on less stable ones
   - Frequent changes propagating through dependencies

   Deep/Wide Hierarchy:
   - Inheritance depth > 6 levels
   - Classes with many direct subclasses (>10)
   - Complex inheritance chains

   Ambiguous Interface:
   - Generic entry points
   - Lack of specific method signatures
   - Unclear component boundaries

   Scattered/Duplicate Functionality:
   - Similar methods across components
   - Repeated dependency patterns
   - Multiple components handling same concern

   Dense Structure:
   - High number of inter-component dependencies
   - Complex dependency graphs
   - Lack of clear architectural layers

   Modularization Issues:
   - Inappropriate boundary crossing
   - Mixed responsibilities
   - Poor separation of concerns

Provide the output in the following JSON format:
{{
    "cyclic_dependencies": [
        {{
            "cycle": ["component1", "component2", "component3"],
            "severity": "CRITICAL|MAJOR|MINOR",
            "impact_analysis": {{
                "architectural_boundaries_crossed": boolean,
                "dependency_types": ["import", "call", etc],
                "affected_functionality": "description"
            }},
            "refactoring_strategy": "detailed strategy to break the cycle",
            "priority": "HIGH|MEDIUM|LOW"
        }}
    ],
    "architectural_smells": [
        {{
            "type": "smell_type",
            "component": "affected_component_name",
            "severity": "CRITICAL|MAJOR|MINOR",
            "evidence": {{
                "metric": "metric_name",
                "value": "metric_value",
                "details": "specific_evidence_details"
            }},
            "affected_components": ["component1", "component2"],
            "recommendation": "detailed_recommendation"
        }}
    ],
    "summary": {{
        "total_issues": 0,
        "critical_issues": 0,
        "major_issues": 0,
        "minor_issues": 0,
        "total_cycles": {total_cycles},
        "largest_cycle_size": {largest_cycle_size}
    }},
    "metrics": {{
        "cyclomatic_complexity": 0.0,
        "maintainability_index": 0.0,
        "dependency_depth": 0,
        "average_component_dependencies": 0.0,
        "max_cycle_length": {max_cycle_length}
    }},
    "needs_detailed_analysis": {{
        "required": false,
        "components": [],
        "reason": "explanation_if_details_needed"
    }}
}}

Data to Analyze:
Dependencies:
{dependencies}

Project Structure:
{project_structure}

Focus on providing detailed analysis of the pre-detected cyclic dependencies and identifying other architectural issues.
Respond ONLY with the JSON structure, no additional text.
'''
    
    # Load JSON files
    with open(dependencies_json_path, 'r') as f:
        dependencies = json.load(f)
    
    with open(project_structure_json_path, 'r') as f:
        project_structure = json.load(f)
    
    # Prepare cycles information
    cycles_info = "No cyclic dependencies detected."
    total_cycles = 0
    largest_cycle_size = 0
    max_cycle_length = 0
    
    if cycles:
        cycles_info = "Detected cyclic dependencies:\n"
        for i, cycle in enumerate(cycles, 1):
            cycles_info += f"{i}. {' → '.join(cycle)} → {cycle[0]}\n"
            largest_cycle_size = max(largest_cycle_size, len(cycle))
            max_cycle_length = max(max_cycle_length, len(cycle))
        total_cycles = len(cycles)
    
    # Format the initial prompt with data
    formatted_prompt = initial_prompt.format(
        dependencies=json.dumps(dependencies, indent=2),
        project_structure=json.dumps(project_structure, indent=2),
        cycles=cycles_info,
        total_cycles=total_cycles,
        largest_cycle_size=largest_cycle_size,
        max_cycle_length=max_cycle_length
    )
    
    # Make the initial API call
    try:
        initial_response = client.chat.completions.create(
            model="grok-3-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert software architect. Always respond with valid JSON only."
                },
                {
                    "role": "user",
                    "content": formatted_prompt
                }
            ],
            response_format={ "type": "json_object" }
        )
        
        # Parse the initial response
        try:
            initial_analysis = json.loads(initial_response.choices[0].message.content)
            
            # Check if detailed analysis is needed and details file is available
            if initial_analysis.get("needs_detailed_analysis", {}).get("required", False) and dependencies_details_path:
                # Load detailed dependencies
                with open(dependencies_details_path, 'r') as f:
                    dependencies_details = json.load(f)
                
                detailed_prompt = f'''
Based on the initial analysis, perform a detailed analysis of the following components: {initial_analysis["needs_detailed_analysis"]["components"]}

Here is the detailed dependency information:
{json.dumps(dependencies_details, indent=2)}

Update your previous analysis and provide a final JSON response in the same format as before, but with more detailed findings for the specified components.
'''
                
                # Make the detailed analysis API call
                detailed_response = client.chat.completions.create(
                    model="grok-3-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert software architect. Always respond with valid JSON only."
                        },
                        {
                            "role": "user",
                            "content": formatted_prompt
                        },
                        {
                            "role": "assistant",
                            "content": initial_response.choices[0].message.content
                        },
                        {
                            "role": "user",
                            "content": detailed_prompt
                        }
                    ],
                    response_format={ "type": "json_object" }
                )
                
                # Return the detailed analysis
                return json.loads(detailed_response.choices[0].message.content)
            
            # If no detailed analysis needed or no details file available, return initial analysis
            return initial_analysis
            
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            return None
            
    except Exception as e:
        print(f"Error calling Grok API: {e}")
        return None

def analyze_architecture_from_strings(
    dependencies_json_str: str,
    project_structure_json_str: str,
) -> Optional[Dict]:
    """
    Analyze software architecture using Grok API with string inputs
    
    Returns:
        Dict containing the analysis results (same structure as analyze_architecture_with_grok)
    """
    
    prompt = '''
You are an expert software architect analyzing codebases for structural issues. Analyze the following inputs and provide a JSON response with architectural concerns.

Input Data:
1. Dependencies (from Depends tool)
2. Project Structure (AST-derived)

Provide the output in the following JSON format:
{{
    "architectural_smells": [
        {{
            "type": "smell_type",
            "component": "affected_component_name",
            "severity": "CRITICAL|MAJOR|MINOR",
            "evidence": {{
                "metric": "metric_name",
                "value": "metric_value"
            }},
            "affected_components": ["component1", "component2"],
            "recommendation": "detailed_recommendation"
        }}
    ],
    "summary": {{
        "total_issues": 0,
        "critical_issues": 0,
        "major_issues": 0,
        "minor_issues": 0
    }},
    "metrics": {{
        "cyclomatic_complexity": 0.0,
        "maintainability_index": 0.0,
        "dependency_depth": 0
    }}
}}

Data to Analyze:

Project Structure:
{project_structure}

Dependencies:
{dependencies}

Dependencies Details:
{dependencies_details}

Respond ONLY with the JSON structure, no additional text.
'''
    
    # Format the prompt with data
    formatted_prompt = prompt.format(
        dependencies=dependencies_json_str,
        project_structure=project_structure_json_str
    )
    
    # Make the API call
    try:
        response = client.chat.completions.create(
            model="grok-3-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert software architect. Always respond with valid JSON only."
                },
                {
                    "role": "user",
                    "content": formatted_prompt
                }
            ],
            response_format={ "type": "json_object" }
        )
        
        # Parse the response into JSON
        try:
            analysis_result = json.loads(response.choices[0].message.content)
            return analysis_result
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            return None
            
    except Exception as e:
        print(f"Error calling Grok API: {e}")
        return None

def main(repo_url: str):
    """Main function to analyze a GitHub repository."""
    try:
        # Step 1: Clone and clean the repository using prepare_project.py
        print(f"Cloning and cleaning repository: {repo_url}")
        clone_dir = "cloned_projects"
        os.makedirs(clone_dir, exist_ok=True)
        
        clone_and_clean(repo_url, clone_dir)
        
        # Get the repository path and create its data directory
        _, repo_name = get_repo_name(repo_url)
        repo_path = os.path.join(clone_dir, repo_name)
        output_dir = os.path.join(repo_path, "data")
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            # Step 2: Run the project analysis
            print("Running project analysis...")
            analyze_project(repo_path, output_dir)
            
            # Step 3: Run the architecture analysis
            print("Running architecture analysis...")
            response = analyze_architecture_with_grok(
                dependencies_json_path=os.path.join(output_dir, "dependencies-file.json"),
                project_structure_json_path=os.path.join(output_dir, "project_structure.json"),
                dependency_graph_path=os.path.join(output_dir, "dependency_graph-file.dot"),
                dependencies_details_path=os.path.join(output_dir, "dependencies_details-file.json")
            )
            
            if response:
                print("\nAnalysis Results:")
                print(json.dumps(response, indent=2))  # Pretty print the JSON response
                
                # Save analysis results
                with open(os.path.join(output_dir, "analysis_results.json"), 'w') as f:
                    json.dump(response, f, indent=2)
                print(f"\nAnalysis results saved to {output_dir}/analysis_results.json")
            else:
                print("Error: No analysis results were generated.")
                
        except Exception as e:
            print(f"Error during analysis: {e}")
            raise
            
    except Exception as e:
        print(f"Error during analysis: {e}")
        raise

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python agent.py <GitHub repository URL>")
        sys.exit(1)
    
    main(sys.argv[1])
