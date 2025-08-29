#!/usr/bin/env python3
"""
Code smell detector for GitHub repositories using Mistral AI with Pydantic validation
Enforces structured JSON output format with confidence scoring:
{
  "smell_type": "Cyclic Dependency",
  "evidence": "Class A imports Class B which imports Class A", 
  "severity": "High",
  "confidence_score": 0.9
}
"""

import os
import sys
import requests
import argparse
import dotenv
import base64
import json
import re
import time
import hashlib
from urllib.parse import urlparse
from typing import List, Dict, Optional

# Pydantic imports for data validation
from pydantic import BaseModel, Field, field_validator, ValidationError

dotenv.load_dotenv()


class CodeSmellIssue(BaseModel):
    """Structured output for code smell issues with confidence scoring"""
    smell_type: str = Field(description="Type of code smell detected")
    evidence: str = Field(description="Concrete evidence of the code smell from the codebase")
    severity: str = Field(description="Severity level: High, Medium, or Low")
    confidence_score: float = Field(
        description="Numeric confidence score between 0.0 and 1.0 indicating certainty of detection",
        ge=0.0, le=1.0
    )
    
    @field_validator('severity')
    @classmethod
    def validate_severity(cls, v):
        if v not in ['High', 'Medium', 'Low']:
            raise ValueError('Severity must be High, Medium, or Low')
        return v
    
    @field_validator('confidence_score')
    @classmethod
    def validate_confidence_score(cls, v):
        if not isinstance(v, (int, float)):
            raise ValueError('confidence_score must be a number')
        if not 0.0 <= v <= 1.0:
            raise ValueError('confidence_score must be between 0.0 and 1.0')
        return float(v)
    
    @field_validator('smell_type')
    @classmethod
    def validate_smell_type(cls, v):
        valid_types = [
            'Scattered Functionality', 
            'Cross-File Dependency', 
            'Code Duplication',
            'Cyclic Dependency', 
            'God Object',
            'Poor Architecture'
        ]
        if v not in valid_types:
            raise ValueError(f'smell_type must be one of: {", ".join(valid_types)}')
        return v


class CodeAnalysisReport(BaseModel):
    """Structured output for complete analysis report as list of issues"""
    issues: List[CodeSmellIssue] = Field(description="List of detected code smell issues")
    
    def rank_by_confidence(self, descending: bool = True) -> List[CodeSmellIssue]:
        """Return issues ranked by confidence score"""
        return sorted(self.issues, key=lambda x: x.confidence_score, reverse=descending)
    
    def filter_by_confidence(self, min_confidence: float = 0.0, max_confidence: float = 1.0) -> List[CodeSmellIssue]:
        """Filter issues by confidence score range"""
        return [issue for issue in self.issues 
                if min_confidence <= issue.confidence_score <= max_confidence]
    
    def filter_by_severity(self, severities: List[str]) -> List[CodeSmellIssue]:
        """Filter issues by severity levels"""
        return [issue for issue in self.issues if issue.severity in severities]
    
    def get_high_confidence_issues(self, threshold: float = 0.8) -> List[CodeSmellIssue]:
        """Get issues above confidence threshold"""
        return self.filter_by_confidence(min_confidence=threshold)


class GitHubAnalyzer:
    def __init__(self, api_key, github_token=None):
        self.api_key = api_key
        self.github_token = github_token
        self.api_url = "https://api.mistral.ai/v1/chat/completions"
        self.github_api_url = "https://api.github.com"
        
        self.max_files = 100
        self.max_file_size = 50000
        self.min_files_for_analysis = 1
        self.excluded_extensions = {'.md', '.txt', '.json', '.xml', '.yml', '.yaml', '.lock', '.log'}
        
        # Common framework patterns to ignore
        self.framework_patterns = {
            'torch.', 'tensorflow.', 'np.', 'pd.', 'plt.', 'cv2.',
            'React.', 'Vue.', 'angular.', '$.',
            'console.', 'window.', 'document.',
            'System.', 'String.', 'Math.', 'Date.',
            'self.', 'super().', '__init__', '__str__', '__repr__'
        }
        




    def validate_github_url(self, url: str) -> bool:
        """Validate GitHub URL format using regex"""
        pattern = r"https://github\.com/[\w\-\.]+/[\w\-\.]+(?:\.git)?/?$"
        return re.match(pattern, url) is not None

    def parse_github_url(self, repo_url):
        # Validate URL format first
        if not self.validate_github_url(repo_url):
            raise ValueError("Invalid GitHub URL format")
            
        if repo_url.endswith('.git'):
            repo_url = repo_url[:-4]
            
        parsed = urlparse(repo_url)
        if parsed.netloc != 'github.com':
            raise ValueError("URL must be a GitHub repository")
            
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) != 2:
            raise ValueError("Invalid GitHub repository URL format")
            
        return path_parts[0], path_parts[1]
        
    def get_github_headers(self):
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'CodeAnalyzer/1.0'
        }
        if self.github_token:
            headers['Authorization'] = f'token {self.github_token}'
        return headers

    def validate_repository(self, owner, repo):
        print("Checking repository...")
        
        url = f"{self.github_api_url}/repos/{owner}/{repo}"
        headers = self.get_github_headers()
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                return False, f"Repository not accessible: {response.status_code}"
            
            repo_info = response.json()
            repo_size = repo_info.get('size', 0)
            if repo_size > 50000:
                return False, f"Repository too large ({repo_size}KB)"
            
            language = repo_info.get('language', 'Unknown')
            supported_languages = {'Python', 'JavaScript', 'TypeScript', 'Java', 'C++', 'C#', 'Go', 'Ruby', 'PHP'}
            if language not in supported_languages:
                print(f"Warning: '{language}' may have limited support")
            
            print(f"Repository OK - Size: {repo_size}KB, Language: {language}")
            return True, repo_info
            
        except Exception as e:
            return False, f"Error: {str(e)}"

    def get_repository_tree(self, owner, repo, path=""):
        url = f"{self.github_api_url}/repos/{owner}/{repo}/contents/{path}"
        headers = self.get_github_headers()
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                return []
        except:
            return []
    
    def get_file_content(self, owner, repo, file_path):
        url = f"{self.github_api_url}/repos/{owner}/{repo}/contents/{file_path}"
        headers = self.get_github_headers()
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                file_data = response.json()
                if file_data.get('encoding') == 'base64':
                    return base64.b64decode(file_data['content']).decode('utf-8')
                else:
                    return file_data.get('content', '')
            return None
        except:
            return None

    def is_framework_function(self, function_name):
        for pattern in self.framework_patterns:
            if function_name.startswith(pattern):
                return True
        return False

    def read_code_files_from_github(self, owner, repo, extensions=['.py', '.js', '.java', '.cpp', '.cs', '.ts', '.go', '.rb', '.php']):
        code_files = {}
        file_count = 0
        
        print("Reading files...")
        
        def explore_directory(path="", depth=0):
            nonlocal file_count
            
            if depth > 10 or file_count >= self.max_files:
                return
                
            items = self.get_repository_tree(owner, repo, path)
            
            # Sort items for deterministic processing order
            sorted_items = sorted(items, key=lambda x: (x['type'], x['name']))
            
            for item in sorted_items:
                if item['type'] == 'dir':
                    if item['name'] not in ['.git', 'node_modules', '__pycache__', '.venv', 'venv', 
                                          '.github', 'dist', 'build', 'target', 'bin', 'obj']:
                        explore_directory(item['path'], depth + 1)
                elif item['type'] == 'file':
                    file_name = item['name']
                    file_size = item.get('size', 0)
                    
                    if any(file_name.endswith(ext) for ext in self.excluded_extensions):
                        continue
                    
                    if any(file_name.endswith(ext) for ext in extensions):
                        if file_size > self.max_file_size:
                            continue
                        
                        content = self.get_file_content(owner, repo, item['path'])
                        if content and len(content.split('\n')) > 10:
                            code_files[item['path']] = content
                            file_count += 1
                            if file_count % 10 == 0:
                                print(f"Read {file_count} files...")
        
        explore_directory()
        print(f"Found {file_count} code files")
        return code_files

    def extract_function_calls_and_dependencies(self, content):
        lines = content.split('\n')
        function_calls = []
        imports = []
        class_methods = []
        
        for line in lines:
            stripped = line.strip()
            
            if not stripped or stripped.startswith('#'):
                continue
            
            if stripped.startswith('import ') or stripped.startswith('from '):
                import_line = stripped[:80]
                if not any(framework in import_line.lower() for framework in 
                          ['torch', 'tensorflow', 'numpy', 'pandas', 'matplotlib', 'requests']):
                    imports.append(import_line)
            
            method_calls = re.findall(r'(\w+\.[\w_]+)\s*\(', stripped)
            for call in method_calls:
                if not self.is_framework_function(call):
                    function_calls.append(call)
            
            func_calls = re.findall(r'(?<!\w)([a-zA-Z_]\w*)\s*\(', stripped)
            keywords = {'if', 'for', 'while', 'print', 'len', 'str', 'int', 'float', 'bool', 
                       'list', 'dict', 'range', 'enumerate', 'open', 'append', 'get'}
            
            func_calls = [call for call in func_calls if call not in keywords and len(call) > 2]
            function_calls.extend(func_calls)
            
            if stripped.startswith('def ') and 'self' in stripped:
                method_match = re.match(r'def\s+(\w+)', stripped)
                if method_match and not method_match.group(1).startswith('__'):
                    class_methods.append(stripped[:60])
        
        filtered_calls = [call for call in set(function_calls) if not self.is_framework_function(call)]
        
        return {
            'imports': sorted(list(set(imports)))[:5],
            'function_calls': sorted(filtered_calls)[:15],
            'class_methods': sorted(list(set(class_methods)))[:8]
        }

    def create_detailed_summary(self, code_files):
        summary = ["=== CODE ANALYSIS ===\n"]
        
        # Sort files deterministically by path for consistent ordering
        sorted_files = sorted(code_files.items(), key=lambda x: x[0])
        
        for path, content in sorted_files[:20]:
            lines = content.split('\n')
            file_name = path.split('/')[-1]
            
            summary.append(f"File: {file_name}")
            summary.append(f"Lines: {len(lines)}")
            
            classes = []
            functions = []
            
            for line in lines[:100]:
                stripped = line.strip()
                if stripped.startswith('class '):
                    classes.append(stripped[:50])
                elif stripped.startswith('def '):
                    functions.append(stripped[:50])
            
            if classes:
                summary.append(f"Classes: {', '.join(classes[:3])}")
            if functions:
                summary.append(f"Functions: {', '.join(functions[:5])}")
            
            deps = self.extract_function_calls_and_dependencies(content)
            
            if deps['imports']:
                sorted_imports = sorted(deps['imports'])
                summary.append(f"Imports: {', '.join(sorted_imports)}")
            if deps['function_calls']:
                sorted_calls = sorted(deps['function_calls'])
                summary.append(f"Calls: {', '.join(sorted_calls[:8])}")
                
            summary.append("")
        
        return '\n'.join(summary)[:15000]

    def analyze_cross_file_concerns(self, code_files):
        concerns_summary = ["\n=== CROSS-FILE ANALYSIS ===\n"]
        
        call_map = {}
        definition_map = {}
        class_map = {}
        
        for file_path, content in code_files.items():
            deps = self.extract_function_calls_and_dependencies(content)
            lines = content.split('\n')
            
            for line in lines:
                stripped = line.strip()
                
                if stripped.startswith('def ') and not stripped.startswith('def __'):
                    func_match = re.match(r'def\s+(\w+)', stripped)
                    if func_match:
                        func_name = func_match.group(1)
                        if not func_name.startswith('_'):
                            definition_map[func_name] = file_path
                
                if stripped.startswith('class '):
                    class_match = re.match(r'class\s+(\w+)', stripped)
                    if class_match:
                        class_name = class_match.group(1)
                        class_map[class_name] = file_path
            
            for call in deps['function_calls']:
                if not self.is_framework_function(call) and len(call) > 2:
                    base_func = call.split('.')[-1] if '.' in call else call
                    if base_func not in call_map:
                        call_map[base_func] = []
                    call_map[base_func].append(file_path)
        
        # Find cross-file concerns
        concerns = []
        for func_name, calling_files in call_map.items():
            unique_files = list(set(calling_files))
            if len(unique_files) >= 3:
                concerns.append({
                    'function': func_name,
                    'files': unique_files,
                    'score': len(unique_files) * len(calling_files)
                })
        
        concerns.sort(key=lambda x: x['score'], reverse=True)
        
        # Find duplicate classes
        class_dups = []
        class_counts = {}
        for class_name, file_path in class_map.items():
            if class_name not in class_counts:
                class_counts[class_name] = []
            class_counts[class_name].append(file_path)
        
        for class_name, files in class_counts.items():
            if len(files) > 1:
                class_dups.append({'class': class_name, 'files': files})
        
        if concerns:
            concerns_summary.append("Cross-file functions:")
            for concern in concerns[:5]:
                file_names = sorted([f.split('/')[-1] for f in concern['files'][:3]])
                concerns_summary.append(f"• {concern['function']}() in {', '.join(file_names)}")
        
        if class_dups:
            concerns_summary.append("\nDuplicate classes:")
            for dup in class_dups[:3]:
                file_names = sorted([f.split('/')[-1] for f in dup['files']])
                concerns_summary.append(f"• {dup['class']} in {', '.join(file_names)}")
        
        return '\n'.join(concerns_summary)[:3000]



    def call_mistral_api_with_validation(self, prompt, repo_info, max_retries=3):
        """API call with Pydantic validation for structured JSON output"""
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        
        # Enhanced payload with structured output requirements
        payload = {
            "model": "devstral-medium-2507",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4000,
            "temperature": 0.0,
            "random_seed": 42
        }
        
        for attempt in range(max_retries):
            try:
                print(f"Analyzing with Pydantic validation... (attempt {attempt + 1})")
                
                response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
                
                if response.status_code == 200:
                    result = response.json()
                    content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                    
                    if content:
                        try:
                            # Parse JSON content
                            json_content = self._extract_json_from_content(content)
                            if json_content is None:
                                raise ValueError("No valid JSON found in response")
                            
                            # Validate with Pydantic
                            validated_output = CodeAnalysisReport(**json_content)
                            return self._format_validated_output(validated_output, repo_info)
                            
                        except (json.JSONDecodeError, ValidationError, ValueError) as validation_error:
                            print(f"Pydantic validation failed: {validation_error}")
                            print("Raw content:", content[:200], "...")
                            if attempt < max_retries - 1:
                                print("Retrying with Pydantic validation...")
                                continue
                            else:
                                return f"Validation failed after {max_retries} attempts: {validation_error}"
                
                if response.status_code == 429:
                    wait_time = 2 ** attempt
                    print(f"Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    return f"Error: {str(e)}"
        
        return "Analysis failed after retries"

    def _extract_json_from_content(self, content: str) -> Optional[Dict]:
        """Extract JSON object from LLM response content"""
        try:
            # Try to parse the entire content as JSON first
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # Look for JSON object in the content
        json_pattern = r'\{.*\}'
        matches = re.findall(json_pattern, content, re.DOTALL)
        
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        
        return None

    def _format_validated_output(self, validated_output: CodeAnalysisReport, repo_info):
        """Format the validated Pydantic output"""
        return {
            "pydantic_validated": True,
            "structured_data": validated_output.model_dump(),
            "repository_info": repo_info
        }



    def analyze_scattered_functionality(self, repo_url):
        try:
            owner, repo = self.parse_github_url(repo_url)
            print(f"Analyzing {owner}/{repo}")
            
            is_valid, repo_info = self.validate_repository(owner, repo)
            if not is_valid:
                return f"Error: {repo_info}"
            
            code_files = self.read_code_files_from_github(owner, repo)
            
            if not code_files:
                return "No code files found"
            
            if len(code_files) < self.min_files_for_analysis:
                return f"Not enough files ({len(code_files)}) for analysis"
            
            summary = self.create_detailed_summary(code_files)
            concerns = self.analyze_cross_file_concerns(code_files)
            
            # Create content hash for deterministic analysis
            content_hash = hashlib.md5((summary + concerns).encode()).hexdigest()[:8]
            
            prompt = f"""Analyze this codebase for code smells and return a JSON response with the exact structure specified.

Content hash: {content_hash} (for consistency - analyze the same way each time)

{summary}

{concerns}

ANALYZE THE RAW CODE ABOVE TO DETECT:

1. **Scattered Functionality**: Classes with same names in multiple files, functions called from many files
2. **Cross-File Dependency**: Functions/classes used across many files inappropriately  
3. **Code Duplication**: Similar code patterns repeated across files
4. **Cyclic Dependency**: Look at import statements for circular dependencies:
   - File A imports File B AND File B imports File A (direct cycle)
   - File A → File B → File C → File A (indirect cycle)
   - Focus on business logic modules, ignore framework imports
5. **God Object**: Large classes that do too much:
   - Classes with 15+ methods (High severity) or 10-14 methods (Medium)
   - Classes spanning 200+ lines (High) or 100-199 lines (Medium)
   - Classes with many different responsibilities
6. **Poor Architecture**: General design issues

SEVERITY RULES:
- High: 4+ files affected OR complex cycles OR large god objects
- Medium: 2-3 files affected OR simple cycles OR medium god objects  
- Low: minor issues, potential improvements

CONFIDENCE SCORING (0.0-1.0):
- 0.9-1.0: Very clear evidence, multiple concrete examples, unambiguous smell
- 0.7-0.8: Strong evidence, clear patterns, minor ambiguity
- 0.5-0.6: Moderate evidence, some uncertainty, potential false positive
- 0.3-0.4: Weak evidence, high uncertainty, might be acceptable design
- 0.0-0.2: Very uncertain, likely false positive, unclear evidence

CONFIDENCE FACTORS:
+ Multiple concrete examples (+0.2)
+ Clear violation of best practices (+0.2)
+ Measurable metrics (file count, method count) (+0.1)
+ Direct impact on maintainability (+0.1)
- Framework/library patterns (-0.2)
- Single occurrence (-0.1)
- Subjective assessment (-0.1)

REQUIRED: Return ONLY a valid JSON object in this EXACT format:

{{
  "issues": [
    {{
      "smell_type": "Cyclic Dependency",
      "evidence": "Class A imports Class B which imports Class A",
      "severity": "High",
      "confidence_score": 0.9
    }},
    {{
      "smell_type": "God Object", 
      "evidence": "UserManager class has 18 methods and handles authentication, validation, database operations, and email sending",
      "severity": "High",
      "confidence_score": 0.85
    }}
  ]
}}

Valid smell_type values: "Scattered Functionality", "Cross-File Dependency", "Code Duplication", "Cyclic Dependency", "God Object", "Poor Architecture"
Valid severity values: "High", "Medium", "Low"
Valid confidence_score: 0.0 to 1.0 (higher = more confident)

Return ONLY the JSON, no other text."""
            
            result = self.call_mistral_api_with_validation(prompt, repo_info)
            return result
            
        except Exception as e:
            return f"Analysis failed: {str(e)}"


def main():
    parser = argparse.ArgumentParser(description='Code smell detector with Pydantic validation for GitHub repos')
    parser.add_argument('repo_url', help='GitHub repository URL')

    parser.add_argument('--max-files', type=int, default=100, help='Max files to analyze')
    parser.add_argument('--max-file-size', type=int, default=50000, help='Max file size in bytes')
    parser.add_argument('--min-files', type=int, default=1, help='Min files for analysis')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--structured-output', action='store_true', help='Output structured JSON report')
    parser.add_argument('--min-confidence', type=float, default=0.0, help='Minimum confidence score to display (0.0-1.0)')
    parser.add_argument('--sort-by-confidence', action='store_true', help='Sort results by confidence score (descending)')
    parser.add_argument('--high-confidence-only', action='store_true', help='Show only high confidence issues (>= 0.8)')
    
    args = parser.parse_args()
    
    api_key = os.getenv('MISTRAL_API_KEY')
    if not api_key:
        print("Error: Need Mistral API key")
        print("Set MISTRAL_API_KEY environment variable in .env file")
        sys.exit(1)
    
    github_token = os.getenv('GITHUB_TOKEN')
    
    if not args.repo_url.startswith('https://github.com/'):
        print("Error: Invalid GitHub URL")
        sys.exit(1)
    
    analyzer = GitHubAnalyzer(api_key, github_token)
    analyzer.max_files = args.max_files
    analyzer.max_file_size = args.max_file_size
    analyzer.min_files_for_analysis = args.min_files
    
    if args.verbose:
        print(f"Config: max_files={analyzer.max_files}, max_size={analyzer.max_file_size}")
        print("Pydantic validation initialized successfully")
    
    print("Starting analysis with Pydantic validation...")
    report = analyzer.analyze_scattered_functionality(args.repo_url)
    
    print("\nResults:")
    print("=" * 50)
    
    if isinstance(report, dict) and 'structured_data' in report:
        structured = report['structured_data']
        
        # Create analysis report object for filtering and ranking
        analysis_report = None
        if 'issues' in structured:
            try:
                analysis_report = CodeAnalysisReport(issues=structured['issues'])
            except Exception as e:
                print(f"Warning: Could not create analysis report object: {e}")
        
        # Apply filtering and sorting
        display_issues = structured.get('issues', [])
        if analysis_report:
            # Apply confidence filtering
            if args.high_confidence_only:
                display_issues = analysis_report.get_high_confidence_issues()
            elif args.min_confidence > 0.0:
                display_issues = analysis_report.filter_by_confidence(min_confidence=args.min_confidence)
            
            # Apply sorting
            if args.sort_by_confidence:
                display_issues = sorted(display_issues, key=lambda x: x.confidence_score, reverse=True)
        
        if args.structured_output:
            # Output structured JSON
            output_data = structured.copy()
            if analysis_report and (args.high_confidence_only or args.min_confidence > 0.0 or args.sort_by_confidence):
                # Convert back to dict format for JSON output
                output_data['issues'] = [
                    {
                        'smell_type': issue.smell_type,
                        'evidence': issue.evidence,
                        'severity': issue.severity,
                        'confidence_score': issue.confidence_score
                    } if hasattr(issue, 'confidence_score') else issue
                    for issue in display_issues
                ]
            print(json.dumps(output_data, indent=2))
        else:
            # Output formatted text
            if report.get('pydantic_validated'):
                print("✓ Pydantic validation: PASSED")
                
                # Display filtering info
                if args.high_confidence_only:
                    print(f"📊 Filtering: Showing only high confidence issues (≥ 0.8)")
                elif args.min_confidence > 0.0:
                    print(f"📊 Filtering: Minimum confidence score: {args.min_confidence}")
                if args.sort_by_confidence:
                    print("📊 Sorted by confidence score (highest first)")
                
                print("\n" + "=" * 50)
                print("DETECTED CODE SMELLS:")
                
                if display_issues:
                    for i, issue in enumerate(display_issues, 1):
                        # Handle both dict and object formats
                        if hasattr(issue, 'smell_type'):
                            smell_type = issue.smell_type
                            evidence = issue.evidence
                            severity = issue.severity
                            confidence = getattr(issue, 'confidence_score', 'N/A')
                        else:
                            smell_type = issue.get('smell_type', 'Unknown')
                            evidence = issue.get('evidence', 'No evidence')
                            severity = issue.get('severity', 'Unknown')
                            confidence = issue.get('confidence_score', 'N/A')
                        
                        print(f"\n{i}. {smell_type} ({severity})")
                        print(f"   Evidence: {evidence}")
                        if confidence != 'N/A':
                            confidence_bar = '█' * int(confidence * 10) + '░' * (10 - int(confidence * 10))
                            print(f"   Confidence: {confidence:.2f} [{confidence_bar}]")
                else:
                    print("No code smells detected matching your criteria.")
                    
                # Count by severity and confidence
                if 'issues' in structured:
                    all_issues = structured['issues']
                    high_count = sum(1 for issue in all_issues if issue.get('severity') == 'High')
                    medium_count = sum(1 for issue in all_issues if issue.get('severity') == 'Medium')
                    low_count = sum(1 for issue in all_issues if issue.get('severity') == 'Low')
                    
                    # Calculate confidence stats
                    confidences = [issue.get('confidence_score', 0) for issue in all_issues]
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                    high_conf_count = sum(1 for c in confidences if c >= 0.8)
                    
                    print(f"\n" + "=" * 50)
                    print("SUMMARY:")
                    print(f"Total Issues Found: {len(all_issues)}")
                    print(f"Displayed Issues: {len(display_issues)}")
                    print(f"By Severity - High: {high_count}, Medium: {medium_count}, Low: {low_count}")
                    print(f"High Confidence (≥0.8): {high_conf_count}")
                    print(f"Average Confidence: {avg_confidence:.2f}")
            else:
                print("⚠ Pydantic validation: FAILED")
                print(report.get('raw_analysis', str(report)))
    else:
        print(report)
    
    print("=" * 50)
    
    # Save enhanced report
    with open("guardrails_code_smell_report.json", 'w') as f:
        if isinstance(report, dict):
            json.dump(report, f, indent=2)
        else:
            json.dump({"error": report, "repository": args.repo_url}, f, indent=2)
    
    print("\nEnhanced report saved to guardrails_code_smell_report.json")


if __name__ == "__main__":
    main()
