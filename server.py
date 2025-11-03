import xml.etree.ElementTree as ET
import os 
import glob
import subprocess
import re
import sys
from fastmcp import FastMCP

mcp = FastMCP("Final Project Test Thing")

@mcp.tool
def run_pmd_analysis(project_path: str) -> dict:
    """
    Runs 'mvn pmd:check' to find code smells and bad practices.
    Returns a summary of violations found by parsing the pmd.xml report.
    """
    try:
        # Run the full command. This will generate the pmd.xml report.
        # We don't care about the exit code, as we will parse the
        # generated XML report directly.
        subprocess.run(
            ["mvn", "clean", "install", "pmd:check"], 
            cwd=project_path, 
            capture_output=True, 
            text=True
        )
        
        # --- NEW LOGIC ---
        # Now, always look for and parse the report.
        pmd_report_path = os.path.join(project_path, "target", "pmd.xml")
        
        if not os.path.exists(pmd_report_path):
            return {"error": "PMD ran but the pmd.xml report was not found."}

        # Parse the report
        tree = ET.parse(pmd_report_path)
        root = tree.getroot()
        violations = []

        # PMD XML format: <file name="..."> <violation ...>
        for file_elem in root.findall('file'):
            file_name = file_elem.get('name')
            for violation in file_elem.findall('violation'):
                violations.append({
                    "file": file_name,
                    "line": violation.get('beginline'),
                    "rule": violation.get('rule'),
                    "priority": violation.get('priority'),
                    "description": violation.text.strip()
                })

        if not violations:
             return {"status": "PMD analysis passed. No violations found."}

        return {
            "status": f"PMD analysis found {len(violations)} total violations.",
            "violations_summary": violations[:20] # Return the first 20
        }

    except ET.ParseError:
        return {"error": "Failed to parse pmd.xml report."}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool
def generate_bva_test_cases(param_name: str, param_type: str, function_name: str, constraints: str = "") -> list:
    """
    Enhanced BVA generator aware of Java types and argument roles.
    """
    JAVA_INT_MAX = 2147483647
    JAVA_INT_MIN = -2147483648

    values = []

    # Detect default/fallback parameter name
    if "default" in param_name.lower():
        # For default values, only vary near 0
        return [0, 1, -1]

    # String used for numeric parsing?
    if param_type == "String" and ("toint" in function_name.lower() or "parse" in function_name.lower()):
        return [
            None, "", " ",
            "0", "1", "-1",
            str(JAVA_INT_MAX), str(JAVA_INT_MIN),
            str(JAVA_INT_MAX + 1), str(JAVA_INT_MIN - 1),
            "abc"
        ]

    if param_type in ("int", "long"):
        values.extend([0, 1, -1, JAVA_INT_MAX, JAVA_INT_MIN])

    elif param_type == "String":
        values.extend([None, "", " ", "a" * 1000])

    elif param_type == "boolean":
        return [True, False]

    # Constraint parsing (optional, unchanged)
    constraints = constraints.lower()
    numbers = [int(n) for n in re.findall(r'\b\d+\b', constraints)]
    
    for num in numbers:
        values.extend([num - 1, num, num + 1])

    return list(dict.fromkeys(values))


@mcp.tool
def get_quality_dashboard(project_path: str) -> dict:
    """
    Parses both Surefire and JaCoCo reports to generate a 
    comprehensive quality metrics dashboard.
    """
    surefire_dir = os.path.join(project_path, "target", "surefire-reports")
    jacoco_report = os.path.join(project_path, "target", "jacoco-report", "jacoco.xml")

    # --- 1. Parse Surefire Reports (Test Results) ---
    total_tests = 0
    total_failures = 0
    total_errors = 0
    total_skipped = 0
    
    if os.path.exists(surefire_dir):
        report_files = glob.glob(os.path.join(surefire_dir, "TEST-*.xml"))
        for report_file in report_files:
            try:
                tree = ET.parse(report_file)
                root = tree.getroot() # <testsuite>
                total_tests += int(root.get('tests', 0))
                total_failures += int(root.get('failures', 0))
                total_errors += int(root.get('errors', 0))
                total_skipped += int(root.get('skipped', 0))
            except ET.ParseError:
                pass # Skip malformed XML

    total_passed = total_tests - (total_failures + total_errors + total_skipped)

    # --- 2. Parse JaCoCo Report (Coverage) ---
    line_coverage = 0.0
    branch_coverage = 0.0
    method_coverage = 0.0

    if os.path.exists(jacoco_report):
        try:
            tree = ET.parse(jacoco_report)
            root = tree.getroot() # <report>
            
            # Find the main <counter> elements for the whole project
            for counter in root.findall('counter'):
                counter_type = counter.get('type')
                missed = int(counter.get('missed', 0))
                covered = int(counter.get('covered', 0))
                total = missed + covered
                
                percentage = (covered / total) * 100 if total > 0 else 100.0
                
                if counter_type == 'LINE':
                    line_coverage = round(percentage, 2)
                elif counter_type == 'BRANCH':
                    branch_coverage = round(percentage, 2)
                elif counter_type == 'METHOD':
                    method_coverage = round(percentage, 2)
        except ET.ParseError:
            pass # Skip malformed XML

    # --- 3. Assemble the Dashboard ---
    return {
        "test_run_summary": {
            "total_tests": total_tests,
            "passed": total_passed,
            "failures": total_failures,
            "errors": total_errors,
            "skipped": total_skipped
        },
        "code_coverage_summary": {
            "line_coverage_percent": line_coverage,
            "branch_coverage_percent": branch_coverage,
            "method_coverage_percent": method_coverage
        }
    }

@mcp.tool
def run_maven_test(project_path: str) -> str:
    """
    Runs 'mvn clean test' in the specified project directory.
    This will run all tests and generate new JaCoCo and Surefire reports.
    Returns a simple status: 'BUILD SUCCESS' or 'BUILD FAILURE'.
    """
    if not os.path.isdir(os.path.join(project_path, "src")):
        return "Error: This does not look like a Maven project directory."

    try:
        result = subprocess.run(
            ["mvn", "clean", "verify"], 
            cwd=project_path, 
            capture_output=True, 
            text=True
        )
        
        output = result.stdout + "\n" + result.stderr

        # Check for the final build status
        if "[INFO] BUILD SUCCESS" in output:
            return "BUILD SUCCESS"
        elif "[INFO] BUILD FAILURE" in output:
            return "BUILD FAILURE: Build failed to compile."
        else:
            return "BUILD FAILURE: Build did not complete. Check logs."

    except Exception as e:
        return f"An unexpected error occurred while running mvn: {str(e)}"

@mcp.tool
def write_file_content(file_path: str, content: str) -> str:
    """
    Writes the given content to the specified file, overwriting the existing content.
    Use 'read_file_content' first if you need to append.
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote content to {file_path}"
    except Exception as e:
        return f"Error writing to file: {str(e)}"

@mcp.tool
def git_status(project_path: str) -> str:
    """Runs 'git status --porcelain' in the specified project directory."""
    try:
        # Run the git status command
        result = subprocess.run(
            ["git", "status", "--porcelain"], 
            cwd=project_path, 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        if not result.stdout:
            return "Git status is clean. No changes to commit."
        
        return f"Git status:\n{result.stdout.strip()}"

    except subprocess.CalledProcessError as e:
        # This will now correctly report if it's not a git repo
        return f"Error running git status: {e.stderr}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

@mcp.tool
def git_add_all(project_path: str) -> str:
    """Runs 'git add .' in the specified project directory to stage all changes."""
    try:
        subprocess.run(
            ["git", "add", "."], 
            cwd=project_path, 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        status_result = subprocess.run(
            ["git", "status", "--porcelain"], 
            cwd=project_path, 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        staged_files = [line for line in status_result.stdout.strip().split('\n') if line.startswith(('M', 'A', 'D', 'R', 'C'))]
        
        if not staged_files:
            return "No changes were staged. Working directory might be clean."

        return f"Successfully staged changes:\n{status_result.stdout.strip()}"

    except subprocess.CalledProcessError as e:
        return f"Error running git add: {e.stderr}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

@mcp.tool
def git_commit(project_path: str, message: str) -> str:
    """Commits staged changes with a provided message."""
    if not message:
        return "Error: A commit message is required."
        
    try:
        result = subprocess.run(
            ["git", "commit", "-m", message], 
            cwd=project_path, 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        return f"Commit successful:\n{result.stdout.strip()}"

    except subprocess.CalledProcessError as e:
        return f"Error running git commit: {e.stderr}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

@mcp.tool
def git_push(project_path: str, remote: str = "origin") -> str:
    """Pushes local commits to the specified remote."""
    try:
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=project_path,  # Fixed a typo here from 'project_T'
            capture_output=True,
            text=True,
            check=True
        )
        current_branch = branch_result.stdout.strip()

        if not current_branch:
            return "Error: Could not determine the current branch."

        result = subprocess.run(
            ["git", "push", remote, current_branch],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )
        
        return f"Push successful:\n{result.stdout.strip()}\n{result.stderr.strip()}"

    except subprocess.CalledProcessError as e:
        return f"Error running git push: {e.stderr}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

@mcp.tool
def git_pull_request(project_path: str, base: str, title: str, body: str) -> str:
    """Creates a GitHub pull request using the 'gh' CLI."""
    try:
        command = [
            "gh", "pr", "create",
            "--base", base,
            "--title", title,
            "--body", body
        ]
        
        result = subprocess.run(
            command,
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )
        
        return f"Successfully created Pull Request:\n{result.stdout.strip()}"

    except FileNotFoundError:
        return "Error: 'gh' (GitHub CLI) not found. Please install it to use this tool."
    except subprocess.CalledProcessError as e:
        return f"Error creating pull request: {e.stderr}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@mcp.tool
def read_file_content(file_path: str) -> str:
    """Reads and returns the full text content of a specified file."""
    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        # Handle potential encoding errors or other read issues
        return f"Error reading file: {str(e)}"

@mcp.tool
def find_java_test_files(project_path: str) -> list:
    """Finds all Java test files in the 'src/test/java' directory."""
    test_src_dir = os.path.join(project_path, "src", "test", "java")
    if not os.path.exists(test_src_dir):
        return {"error": f"Test source directory not found at {test_src_dir}"}
    
    java_files = []
    for root, dirs, files in os.walk(test_src_dir):
        for file in files:
            if file.endswith(".java"):
                java_files.append(os.path.join(root, file))
                
    return java_files

@mcp.tool
def find_jacoco_report(project_path: str) -> str:
    """Finds the JaCoCo XML report in the specified project path."""
    report_path = os.path.join(project_path, "target", "jacoco-report", "jacoco.xml")
    if not os.path.exists(report_path):
        return f"Error: JaCoCo report not found at {report_path}. Please run 'mvn clean test' first."
    return report_path

@mcp.tool
def get_missing_coverage(jacoco_report_path: str) -> dict:
    """Parses a JaCoCo XML report to find lines with missing coverage."""
    if not os.path.exists(jacoco_report_path):
        return {"error": f"Report not found at {jacoco_report_path}"}

    try:
        tree = ET.parse(jacoco_report_path)
        root = tree.getroot()
        
        missing_coverage = {}

        # JaCoCo XML structure: package -> class -> method -> line
        for package in root.findall('package'):
            package_name = package.get('name')
            for class_elem in package.findall('class'):
                class_name = class_elem.get('name')
                
                uncovered_lines = []
                
                # Find all line elements within the class's sourcefile
                for line in class_elem.findall('sourcefile/line'):
                    # Get missed instructions (mi) and line number (nr)
                    missed_instructions = line.get('mi')
                    line_number = line.get('nr')

                    # --- THIS IS THE FIX ---
                    # Check if attributes are not None before trying to convert to int
                    if missed_instructions is not None and line_number is not None:
                        try:
                            # If missed instructions > 0, add the line number
                            if int(missed_instructions) > 0:
                                uncovered_lines.append(int(line_number))
                        except ValueError:
                            # Skip if 'mi' or 'nr' is not a valid number
                            pass 
                    # --- END OF FIX ---

                if uncovered_lines:
                    full_class_name = f"{package_name.replace('/', '.')}.{class_name.split('/')[-1]}"
                    # Use set to remove duplicates, then sort
                    missing_coverage[full_class_name] = sorted(list(set(uncovered_lines)))

        if not missing_coverage:
            return {"status": "100% Coverage!"}
            
        return missing_coverage

    except ET.ParseError:
        return {"error": "Failed to parse the JaCoCo XML file. It might be malformed."}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool
def get_test_failures(project_path: str) -> dict:
    """Parses Surefire XML reports to find test failures and errors.

    Accepts either a project root (looks under target/surefire-reports) or a direct
    path to a single XML file. Returns a structured dict with failures or status.
    """
    report_files = []

    # If the user passed a direct XML file, parse that single file
    if os.path.isfile(project_path) and project_path.lower().endswith('.xml'):
        report_files = [project_path]
    else:
        report_dir = os.path.join(project_path, "target", "surefire-reports")
        if not os.path.exists(report_dir):
            return {"error": "Surefire reports directory not found. Run 'mvn clean test' first."}

        # Prefer TEST-*.xml files but accept any .xml in the directory
        report_files = glob.glob(os.path.join(report_dir, "TEST-*.xml"))
        if not report_files:
            report_files = glob.glob(os.path.join(report_dir, "*.xml"))

    if not report_files:
        return {"error": "No test reports found in surefire-reports."}

    failures = {}
    skipped_files = []

    for report_file in report_files:
        try:
            tree = ET.parse(report_file)
            root = tree.getroot()

            # Iterate over <testcase> elements and inspect their children for <failure> or <error>
            for testcase in root.findall('.//testcase'):
                test_name = testcase.get('name')
                class_name = testcase.get('classname') or root.get('name') or "Unknown"

                for child in list(testcase):
                    tag = child.tag.lower()
                    if tag in ('failure', 'error'):
                        message = child.get('message') or ""
                        details = child.text.strip() if child.text else ""
                        failures.setdefault(class_name, []).append({
                            "test": test_name,
                            "type": tag,
                            "message": message,
                            "details": details
                        })

        except ET.ParseError:
            skipped_files.append(report_file)
            continue
        except Exception:
            skipped_files.append(report_file)
            continue

    if not failures:
        # If some files were skipped, include them for visibility
        if skipped_files:
            return {"status": "All tests passed!", "skipped_files": skipped_files}
        return {"status": "All tests passed!"}

    result = {"failures": failures}
    if skipped_files:
        result["skipped_files"] = skipped_files

    return result

@mcp.tool
def find_java_files(project_path: str) -> list:
    """Finds all Java source files in the 'src/main/java' directory."""
    src_dir = os.path.join(project_path, "src", "main", "java")
    if not os.path.exists(src_dir):
        return {"error": f"Source directory not found at {src_dir}"}
    
    java_files = []
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if file.endswith(".java"):
                java_files.append(os.path.join(root, file))
                
    return java_files
    
if __name__ == "__main__":
    mcp.run(transport="sse")
