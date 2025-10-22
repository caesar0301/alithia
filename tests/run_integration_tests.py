#!/usr/bin/env python3
"""
Script to run integration tests for the Alithia researcher project.

This script runs only the integration tests that make real API calls.
"""

import subprocess
import sys
from pathlib import Path


def main():
    """Run integration tests."""
    # Get the project root directory
    project_root = Path(__file__).parent.parent

    # Change to project root
    import os

    os.chdir(project_root)

    # Run integration tests using poetry
    cmd = [
        "poetry",
        "run",
        "pytest",
        "tests/integration/",
        "-m",
        "integration",
        "--verbose",
        "--tb=short",
        "--strict-markers",
    ]

    print("Running integration tests...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 50)

    try:
        result = subprocess.run(cmd, check=True)
        print("-" * 50)
        print("✅ Integration tests passed!")
        return 0
    except subprocess.CalledProcessError as e:
        print("-" * 50)
        print(f"❌ Integration tests failed with exit code {e.returncode}")
        return e.returncode


if __name__ == "__main__":
    sys.exit(main())
