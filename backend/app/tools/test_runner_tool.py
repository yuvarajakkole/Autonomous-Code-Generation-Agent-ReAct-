"""
Tool 5: Test Runner Tool
=========================
Runs tests for both frontend (HTML checklist) and backend (pytest) projects.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
from typing import Tuple

from app.models.schemas import ExecutionResult, TestResult
from app.tools.execution_tool import CodeExecutionTool


class TestRunnerTool:
    name = "test_runner"
    description = "Runs tests and returns structured pass/fail results"

    def __init__(self):
        self._executor = CodeExecutionTool()

    async def run(
        self,
        implementation_code: str,
        test_code: str,
    ) -> Tuple[ExecutionResult, TestResult]:

        # Detect project type
        project = self._try_parse_project(implementation_code)

        if project:
            return await self._run_project_tests(project, test_code)
        else:
            return await self._run_python_tests(implementation_code, test_code)

    async def _run_project_tests(
        self, project: dict, test_code: str
    ) -> Tuple[ExecutionResult, TestResult]:
        """Run structural checks on a multi-file project."""
        files: dict = project.get("files", {})
        passed = []
        failed = []

        # Check 1: Has entry point file
        entry = project.get("entry_point", "index.html")
        if entry in files:
            passed.append(f"PASSED: Entry point '{entry}' exists")
        else:
            failed.append(f"FAILED: Entry point '{entry}' missing")

        # Check 2: HTML validation
        for fname, content in files.items():
            if fname.endswith(".html"):
                html_lower = content.lower()
                if "<html" in html_lower and "<body" in html_lower:
                    passed.append(f"PASSED: {fname} has valid HTML structure")
                else:
                    failed.append(f"FAILED: {fname} missing html/body tags")

                # Check for interactive elements
                has_input = "input" in html_lower
                has_button = "button" in html_lower or "onclick" in html_lower
                has_script = "<script" in html_lower

                if has_input:
                    passed.append("PASSED: Has input elements")
                if has_button:
                    passed.append("PASSED: Has interactive buttons")
                if has_script:
                    passed.append("PASSED: Has JavaScript")
                else:
                    failed.append("FAILED: No JavaScript found — app may not be interactive")

                # Check for styling
                has_css = "<style" in html_lower or fname.replace(".html", ".css") in files
                if has_css:
                    passed.append("PASSED: Has CSS styling")
                else:
                    failed.append("FAILED: No CSS found — app has no styling")

                # Check content length (too short = incomplete)
                if len(content) > 500:
                    passed.append(f"PASSED: {fname} has substantial content ({len(content)} chars)")
                else:
                    failed.append(f"FAILED: {fname} seems too short ({len(content)} chars)")

        # Check 3: CSS
        for fname, content in files.items():
            if fname.endswith(".css") and len(content) > 50:
                passed.append(f"PASSED: {fname} has styling ({len(content)} chars)")

        # Check 4: Python backend if present
        for fname, content in files.items():
            if fname.endswith(".py"):
                import subprocess
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".py", delete=False
                ) as f:
                    f.write(content)
                    tmp = f.name
                try:
                    r = subprocess.run(
                        [sys.executable, "-m", "py_compile", tmp],
                        capture_output=True, text=True, timeout=10
                    )
                    if r.returncode == 0:
                        passed.append(f"PASSED: {fname} has valid Python syntax")
                    else:
                        failed.append(f"FAILED: {fname} syntax error: {r.stderr[:100]}")
                finally:
                    os.unlink(tmp)

        total = len(passed) + len(failed)
        stdout = "\n".join(passed + failed)
        stderr = "\n".join(failed) if failed else ""

        exec_result = ExecutionResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=0 if not failed else 1,
            timed_out=False,
            duration_ms=100,
        )
        test_result = TestResult(
            total=total,
            passed=len(passed),
            failed=len(failed),
            errors=0,
            details=passed + failed,
        )
        return exec_result, test_result

    async def _run_python_tests(
        self, implementation_code: str, test_code: str
    ) -> Tuple[ExecutionResult, TestResult]:
        exec_result = await self._executor.execute_tests(implementation_code, test_code)
        test_result = self._parse_pytest_output(exec_result.stdout + exec_result.stderr)
        return exec_result, test_result

    def _parse_pytest_output(self, output: str) -> TestResult:
        result = TestResult()
        summary = re.search(
            r"(\d+) passed(?:,\s*(\d+) failed)?(?:,\s*(\d+) error)?", output
        )
        if summary:
            result.passed = int(summary.group(1) or 0)
            result.failed = int(summary.group(2) or 0)
            result.errors = int(summary.group(3) or 0)
            result.total  = result.passed + result.failed + result.errors
        else:
            failed_m = re.search(r"(\d+) failed", output)
            if failed_m:
                result.failed = int(failed_m.group(1))
                result.total  = result.failed
        test_lines = [
            l.strip() for l in output.split("\n")
            if re.match(r"\s*(PASSED|FAILED|ERROR)\s+", l)
        ]
        result.details = test_lines[:20]
        return result

    def format_summary(self, test_result: TestResult) -> str:
        if test_result.total == 0:
            return "No tests executed"
        rate = (test_result.passed / test_result.total) * 100
        return (
            f"{test_result.passed}/{test_result.total} tests passed ({rate:.0f}%), "
            f"{test_result.failed} failed"
        )

    def _try_parse_project(self, code: str) -> dict | None:
        try:
            cleaned = code.strip()
            for prefix in ("```json", "```"):
                if cleaned.startswith(prefix):
                    cleaned = cleaned[len(prefix):]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            data = json.loads(cleaned.strip())
            if isinstance(data, dict) and "files" in data:
                return data
        except (json.JSONDecodeError, TypeError):
            pass
        return None
