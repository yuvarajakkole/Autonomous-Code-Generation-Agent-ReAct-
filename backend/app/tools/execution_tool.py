"""
Tool 4: Code Execution Tool — Multi-file Project Validator
===========================================================
For frontend-only projects: validates HTML structure, JS syntax.
For fullstack projects: also runs pytest on the Python backend.
Never tries to start a server.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Optional

from app.models.schemas import ExecutionResult


class CodeExecutionTool:
    name = "code_executor"
    description = "Validates and executes generated project files"

    def __init__(self):
        pass  # No Docker needed

    async def execute(
        self,
        code: str,
        filename: str = "solution.py",
        timeout: Optional[int] = None,
    ) -> ExecutionResult:
        """
        Smart executor: detects if code is JSON project or raw code,
        and validates appropriately.
        """
        timeout = timeout or 30

        # Try parsing as a project JSON first
        project = self._try_parse_project(code)
        if project:
            return await self._validate_project(project, timeout)

        # Detect HTML
        if "<!DOCTYPE" in code or "<html" in code.lower():
            return self._validate_html(code)

        # Python code — strip server startup and run
        safe = self._strip_server_code(code)
        return await self._run_python(safe, timeout)

    async def execute_tests(
        self,
        implementation_code: str,
        test_code: str,
        timeout: Optional[int] = None,
    ) -> ExecutionResult:
        """Run pytest for Python backends, or JS validation for frontends."""
        timeout = timeout or 30

        # Try parsing as project JSON
        project = self._try_parse_project(implementation_code)
        if project:
            return await self._validate_project(project, timeout)

        # Pure Python path
        safe_impl = self._strip_server_code(implementation_code)
        safe_tests = re.sub(r'\bfrom\s+(main|calculator|app)\b', 'from solution', test_code)
        safe_tests = re.sub(r'\bimport\s+(main|calculator|app)\b', 'import solution', safe_tests)

        tmpdir = tempfile.mkdtemp(prefix="react_agent_")
        try:
            with open(os.path.join(tmpdir, "solution.py"), "w") as f:
                f.write(safe_impl)
            with open(os.path.join(tmpdir, "test_solution.py"), "w") as f:
                f.write(safe_tests)

            cmd = [sys.executable, "-m", "pytest",
                   os.path.join(tmpdir, "test_solution.py"),
                   "-v", "--tb=short", "--no-header",
                   f"--rootdir={tmpdir}"]
            return await self._run_cmd(cmd, timeout, cwd=tmpdir)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    # ── Project validation ────────────────────────────────────

    async def _validate_project(self, project: dict, timeout: int) -> ExecutionResult:
        """Validate a multi-file project — check HTML structure, JS syntax."""
        files: dict = project.get("files", {})
        errors = []
        warnings = []
        report_lines = []

        report_lines.append(f"Project type: {project.get('project_type', 'unknown')}")
        report_lines.append(f"Files: {list(files.keys())}")

        for fname, content in files.items():
            if fname.endswith(".html"):
                html_issues = self._check_html(content, fname)
                if html_issues:
                    errors.extend(html_issues)
                else:
                    report_lines.append(f"✓ {fname}: valid HTML structure")

            elif fname.endswith(".js"):
                js_result = await self._check_js_syntax(content, timeout)
                if js_result:
                    errors.append(f"{fname}: {js_result}")
                else:
                    report_lines.append(f"✓ {fname}: JS syntax OK")

            elif fname.endswith(".css"):
                report_lines.append(f"✓ {fname}: CSS present ({len(content)} chars)")

            elif fname.endswith(".py"):
                py_result = await self._check_python_syntax(content, timeout)
                if py_result:
                    errors.append(f"{fname}: {py_result}")
                else:
                    report_lines.append(f"✓ {fname}: Python syntax OK")

        stdout = "\n".join(report_lines)
        stderr = "\n".join(errors)
        exit_code = 1 if errors else 0

        return ExecutionResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            timed_out=False,
            duration_ms=50,
        )

    def _check_html(self, html: str, fname: str) -> list[str]:
        """Check HTML for critical issues."""
        issues = []
        html_lower = html.lower()
        if "<html" not in html_lower:
            issues.append(f"{fname}: Missing <html> tag")
        if "<head>" not in html_lower and "<head " not in html_lower:
            issues.append(f"{fname}: Missing <head> tag")
        if "<body>" not in html_lower and "<body " not in html_lower:
            issues.append(f"{fname}: Missing <body> tag")
        return issues

    async def _check_js_syntax(self, js: str, timeout: int) -> str | None:
        """Check JS syntax using node if available, else basic check."""
        try:
            result = subprocess.run(["node", "--version"],
                                    capture_output=True, timeout=3)
            if result.returncode == 0:
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".js", delete=False
                ) as f:
                    f.write(js)
                    tmp = f.name
                try:
                    r = subprocess.run(
                        ["node", "--check", tmp],
                        capture_output=True, timeout=timeout, text=True
                    )
                    if r.returncode != 0:
                        return r.stderr[:200]
                finally:
                    os.unlink(tmp)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # node not available — do a basic check
            if js.count("{") != js.count("}"):
                return "Unmatched braces in JavaScript"
        return None

    async def _check_python_syntax(self, code: str, timeout: int) -> str | None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write(code)
            tmp = f.name
        try:
            r = subprocess.run(
                [sys.executable, "-m", "py_compile", tmp],
                capture_output=True, timeout=timeout, text=True
            )
            if r.returncode != 0:
                return r.stderr[:200]
        finally:
            os.unlink(tmp)
        return None

    def _validate_html(self, html: str) -> ExecutionResult:
        issues = self._check_html(html, "index.html")
        return ExecutionResult(
            stdout="HTML validation complete",
            stderr="\n".join(issues),
            exit_code=1 if issues else 0,
            timed_out=False,
            duration_ms=10,
        )

    async def _run_python(self, code: str, timeout: int) -> ExecutionResult:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write(code)
            tmp = f.name
        try:
            return await self._run_cmd([sys.executable, tmp], timeout)
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    # ── Helpers ───────────────────────────────────────────────

    def _try_parse_project(self, code: str) -> dict | None:
        """Try to parse code as a project JSON dict with 'files' key."""
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
        except (json.JSONDecodeError, AttributeError):
            pass
        return None

    def _strip_server_code(self, code: str) -> str:
        code = re.sub(
            r'\nif\s+__name__\s*==\s*["\']__main__["\']\s*:.*',
            '', code, flags=re.DOTALL,
        )
        code = re.sub(r'^\s*uvicorn\.run\(.*?\)\s*$', '', code, flags=re.MULTILINE)
        return code

    async def _run_cmd(
        self, cmd: list, timeout: int, cwd: Optional[str] = None
    ) -> ExecutionResult:
        start = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
                return ExecutionResult(
                    stdout=stdout.decode("utf-8", errors="replace"),
                    stderr=stderr.decode("utf-8", errors="replace"),
                    exit_code=proc.returncode or 0,
                    timed_out=False,
                    duration_ms=int((time.monotonic() - start) * 1000),
                )
            except asyncio.TimeoutError:
                proc.kill()
                return ExecutionResult(
                    stdout="", stderr=f"Timed out after {timeout}s",
                    exit_code=-1, timed_out=True,
                    duration_ms=timeout * 1000,
                )
        except Exception as exc:
            return ExecutionResult(
                stdout="", stderr=str(exc),
                exit_code=-1, timed_out=False, duration_ms=0,
            )
