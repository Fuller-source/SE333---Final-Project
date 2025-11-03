# SE333 Final Project: Intelligent Testing Agent

This project implements an autonomous AI software agent using the Model Context Protocol (MCP) framework to manage, test, and iteratively improve a complex Java Maven codebase. The agent's primary function is to achieve code stability, fix bugs, and enhance code quality, demonstrating a fully automated software development workflow.

Installation and Configuration

Follow these steps to set up the agent and the environment.

Prerequisites

    Java: JDK 11+ (or higher) and Maven 3.6+.

    Python: Python 3.10+ (or higher).

    VS Code: Latest version with the Chat view.

    Node.js: Version 18+ (LTS recommended).

    Git: And an active GitHub account.

    GitHub CLI (gh): Required for the git_pull_request tool.

Setup Steps

    git clone [YOUR REPOSITORY URL HERE]
    cd [YOUR REPOSITORY NAME]

Set up Python environment:
Bash

# Create and activate virtual environment
    uv venv
    source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows

# Install MCP dependencies
    uv add mcp[cli] httpx fastmcp

# Run the MCP Server:
Bash

    python server.py

Connect to VS Code:

    Open the VS Code Command Palette (Ctrl+Shift+P).

    Run MCP: Add Server.

    Enter the server URL (e.g., http://127.0.0.1:8000).

    Give it a name.

Enable Auto-Approve:

    Open the Command Palette (Ctrl+Shift+P).

    Run Chat: Settings and enable Auto-Approve .

# How to Run the Agent

To start the agent's full autonomous workflow, send this command in the VS Code Chat:

    "Run the build and show me the Quality Dashboard."

The agent will begin its iterative process: running mvn clean verify, analyzing the results, and deciding whether to fix bugs, fix PMD violations, or add new tests.

MCP Tool API Documentation

The agent's intelligence is defined by the following toolset:

Phase 2 & 4: Core Analysis and Iteration Tools

    - run_maven_test	    Runs mvn clean verify to build and test the project.	Provides BUILD SUCCESS/FAILURE status.
    - get_quality_dashboard	Parses Surefire and JaCoCo reports.	Tracks test counts and coverage percentages for overall project health.
    - get_test_failures	    Parses Surefire XML reports.	Finds detailed failure messages and stack traces for bug triage.
    - get_missing_coverage	Parses JaCoCo XML reports.	Identifies specific classes and line numbers that lack test coverage.
    - read_file_content	    Reads and returns the content of a file.	Allows the agent to ingest code for analysis.
    - write_file_content	Writes content to a file.	Allows the agent to implement code fixes and new tests.

Phase 3: Git Automation Tools

    - git_status	    Checks for uncommitted changes.	Enforces a clean state before starting a workflow.
    - git_add_all	    Runs git add . to stage changes.	Prepares code edits for commit.
    - git_commit	    Commits staged changes with a message.	Records fixes and improvements in version control.
    - git_push	        Pushes the current branch to origin.	Synchronizes local fixes with the remote repository.
    - git_pull_request	Creates a pull request via the gh CLI.	Submits completed work for code review.

Phase 5: Creative Extensions (Advanced Analysis)

    - generate_bva_test_cases	Specification-Based Testing Generator	Implements Boundary Value Analysis (BVA). Takes a data type and constraints (e.g., "between 18 and 65") and returns necessary boundary values.
    - run_pmd_analysis	        AI Code Review Agent	Runs static analysis (mvn pmd:check). Parses the report (pmd.xml) to identify code smells, bad practices (e.g., EmptyCatchBlock), and violations for automated cleanup.

What I was able to accomplish in the code base using my agent.

        - Build Fix: Successfully debugged and fixed a major conflict in pom.xml between the JaCoCo agent and the Surefire plugin, enabling correct coverage reporting.

        - NPE Fix: Identified and fixed a NullPointerException bug in SystemUtils.java related to Java version checks, which was causing dozens of tests to fail.

        - Reflection Fix: Automatically added the necessary --add-opens flags to the Maven configuration to resolve InaccessibleObjectException errors caused by modern JDK security policies.

        - Code Quality: Successfully ran the static analysis tool and identified 98+ PMD violations, demonstrating its capability to perform high-level code review.