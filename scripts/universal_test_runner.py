#!/usr/bin/env python3
"""Universal Test Runner - Language-Agnostic Test Orchestration

Automatically detects project type and runs appropriate test framework with optimizations.
Supports: Python (pytest), Node.js (jest/vitest), Go, Rust, Java

Usage:
    python universal_test_runner.py [suite_name] [options]

Available suites:
    smoke      - Quick smoke tests
    unit       - Unit tests only
    integration - Integration tests
    e2e        - End-to-end tests
    all        - Complete test suite (default)
    coverage   - Full suite with coverage

Options:
    --parallel N      - Run with N parallel workers (default: auto)
    --no-coverage     - Disable coverage collection
    --verbose         - Verbose output
    --timeout N       - Test timeout in seconds (default: 300)
"""

import json
import subprocess
import sys
from pathlib import Path


class ProjectDetector:
    """Detect project type and configuration."""

    @staticmethod
    def detect_language() -> str:
        """Auto-detect primary language."""
        if Path("pyproject.toml").exists() or Path("setup.py").exists():
            return "python"
        elif Path("package.json").exists():
            return "node"
        elif Path("go.mod").exists():
            return "go"
        elif Path("Cargo.toml").exists():
            return "rust"
        elif Path("pom.xml").exists() or Path("build.gradle").exists():
            return "java"
        else:
            return "unknown"

    @staticmethod
    def detect_test_framework(language: str) -> str:
        """Detect test framework for the language."""
        if language == "python":
            if Path("pytest.ini").exists() or "pytest" in Path("pyproject.toml").read_text():
                return "pytest"
            return "unittest"

        elif language == "node":
            package_json = json.loads(Path("package.json").read_text())
            deps = {
                **package_json.get("dependencies", {}),
                **package_json.get("devDependencies", {}),
            }

            if "vitest" in deps:
                return "vitest"
            elif "jest" in deps:
                return "jest"
            return "unknown"

        elif language == "go":
            return "go-test"

        elif language == "rust":
            return "cargo-test"

        elif language == "java":
            if Path("pom.xml").exists():
                return "maven"
            elif Path("build.gradle").exists():
                return "gradle"

        return "unknown"

    @staticmethod
    def get_cpu_count() -> int:
        """Get available CPU count for parallel execution."""
        try:
            import multiprocessing

            return multiprocessing.cpu_count()
        except (ImportError, NotImplementedError):
            return 4


class TestRunner:
    """Universal test runner supporting multiple languages."""

    def __init__(self, language: str, framework: str):
        self.language = language
        self.framework = framework
        self.project_root = Path.cwd()

    def build_command(
        self,
        suite: str = "all",
        parallel: int | None = None,
        coverage: bool = True,
        verbose: bool = False,
        timeout: int = 300,
    ) -> list[str]:
        """Build test command based on language and framework."""

        if self.language == "python" and self.framework == "pytest":
            return self._build_pytest_command(suite, parallel, coverage, verbose, timeout)

        elif self.language == "node":
            return self._build_node_command(suite, parallel, coverage, verbose)

        elif self.language == "go":
            return self._build_go_command(suite, coverage, verbose)

        elif self.language == "rust":
            return self._build_rust_command(suite, coverage, verbose)

        elif self.language == "java":
            return self._build_java_command(suite, coverage)

        else:
            raise ValueError(f"Unsupported language/framework: {self.language}/{self.framework}")

    def _build_pytest_command(
        self,
        suite: str,
        parallel: int | None,
        coverage: bool,
        verbose: bool,
        timeout: int,
    ) -> list[str]:
        """Build pytest command with optimizations."""
        cmd = ["pytest"]

        # Test selection
        if suite == "smoke":
            cmd.extend(["-m", "smoke and not slow", "--tb=short", "-q"])
        elif suite == "unit":
            cmd.extend(["tests/unit", "-m", "unit"])
        elif suite == "integration":
            cmd.extend(["-m", "integration"])
        elif suite == "e2e":
            cmd.extend(["-m", "e2e"])
        elif suite == "coverage":
            cmd.extend(["tests"])
        else:  # all
            cmd.extend(["tests"])

        # Parallel execution
        if parallel is None:
            parallel = ProjectDetector.get_cpu_count()

        if parallel > 1:
            cmd.extend(["-n", str(parallel), "--dist=worksteal"])

        # Coverage
        if coverage and suite != "smoke":
            source_dir = self._detect_python_source_dir()
            cmd.extend(
                [
                    f"--cov={source_dir}",
                    "--cov-report=term-missing:skip-covered",
                    "--cov-report=xml",
                ]
            )

        # Verbosity
        if verbose:
            cmd.append("-v")
        else:
            cmd.append("-q")

        # Timeout
        cmd.extend(["--timeout", str(timeout)])

        # Standard options
        cmd.extend(["--tb=short", "--strict-markers"])

        return cmd

    def _build_node_command(
        self,
        suite: str,
        parallel: int | None,
        coverage: bool,
        verbose: bool,
    ) -> list[str]:
        """Build Node.js test command."""
        if self.framework == "jest":
            cmd = ["npx", "jest"]

            if coverage:
                cmd.append("--coverage")

            if parallel and parallel > 1:
                cmd.extend(["--maxWorkers", str(parallel)])

            if suite != "all":
                cmd.append(f"--testPathPattern=.*{suite}.*")

            return cmd

        elif self.framework == "vitest":
            cmd = ["npx", "vitest", "run"]

            if coverage:
                cmd.append("--coverage")

            if parallel and parallel > 1:
                cmd.extend(["--threads", "--maxThreads", str(parallel)])

            return cmd

        else:
            return ["npm", "test"]

    def _build_go_command(self, suite: str, coverage: bool, verbose: bool) -> list[str]:
        """Build Go test command."""
        cmd = ["go", "test"]

        if verbose:
            cmd.append("-v")

        cmd.append("-race")

        if coverage:
            cmd.extend(["-coverprofile=coverage.out", "-covermode=atomic"])

        cmd.append("./...")

        return cmd

    def _build_rust_command(self, suite: str, coverage: bool, verbose: bool) -> list[str]:
        """Build Rust test command."""
        if coverage:
            return ["cargo", "tarpaulin", "--out", "Xml"]
        else:
            cmd = ["cargo", "test"]
            if verbose:
                cmd.append("--verbose")
            return cmd

    def _build_java_command(self, suite: str, coverage: bool) -> list[str]:
        """Build Java test command."""
        if self.framework == "maven":
            cmd = ["mvn", "test"]
            if coverage:
                cmd.append("jacoco:report")
            return cmd
        elif self.framework == "gradle":
            cmd = ["./gradlew", "test"]
            if coverage:
                cmd.append("jacocoTestReport")
            return cmd
        else:
            return ["mvn", "test"]

    def _detect_python_source_dir(self) -> str:
        """Detect Python source directory."""
        # Common patterns
        candidates = ["src", "app", "apps/api/src", Path.cwd().name]

        for candidate in candidates:
            if Path(candidate).exists() and Path(candidate).is_dir():
                # Check if it contains Python files
                py_files = list(Path(candidate).rglob("*.py"))
                if py_files:
                    return candidate

        return "."


def print_usage():
    """Print usage information."""
    print(__doc__)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Universal Test Runner")
    parser.add_argument("suite", nargs="?", default="all", help="Test suite to run")
    parser.add_argument("--parallel", type=int, help="Number of parallel workers")
    parser.add_argument("--no-coverage", action="store_true", help="Disable coverage")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--timeout", type=int, default=300, help="Test timeout in seconds")

    args = parser.parse_args()

    # Detect project
    language = ProjectDetector.detect_language()
    framework = ProjectDetector.detect_test_framework(language)

    print(f"🔍 Detected: {language} + {framework}")
    print(f"🧪 Running: {args.suite} test suite")

    if language == "unknown":
        print("❌ Could not detect project type")
        print("Supported: Python, Node.js, Go, Rust, Java")
        return 1

    # Build and run command
    runner = TestRunner(language, framework)

    try:
        command = runner.build_command(
            suite=args.suite,
            parallel=args.parallel,
            coverage=not args.no_coverage,
            verbose=args.verbose,
            timeout=args.timeout,
        )

        print(f"⚡ Command: {' '.join(command)}")
        print("=" * 60)

        result = subprocess.run(command, check=False)

        if result.returncode == 0:
            print(f"\n✅ {args.suite} test suite completed successfully!")
        else:
            print(f"\n❌ {args.suite} test suite failed with exit code {result.returncode}")

        return result.returncode

    except Exception as e:
        print(f"\n💥 Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
