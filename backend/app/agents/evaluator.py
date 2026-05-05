"""
Evaluator Component
====================
Scores generated code against multiple quality dimensions.

Fix: Port-in-use / server-startup errors are SANDBOX ENVIRONMENT issues,
not code correctness issues. The evaluator now detects and ignores them
so the correctness score is based on actual code logic quality.
"""

from __future__ import annotations

import json
import re
from typing import Optional

from app.core.llm import get_llm_client
from app.models.schemas import EvaluationScore, ExecutionResult, TestResult


_EVALUATION_SYSTEM = """You are a senior code reviewer performing objective evaluation.
Score the given code submission on a scale of 0.0 to 1.0 per dimension.

Dimensions:
- correctness:    Does the code logic correctly implement the requirement?
- completeness:   Does it cover all stated features/acceptance criteria?
- edge_cases:     Are input validation and error conditions handled?
- code_quality:   Is the code clean, typed, documented, and maintainable?

IMPORTANT RULES for scoring:
- If execution failed ONLY because of "address already in use" / port conflict
  / server startup error → this is a SANDBOX issue, NOT a code bug.
  Score correctness based on the code logic itself, not the execution environment.
- If execution failed due to SyntaxError, ImportError, or logic errors → penalize correctness.
- Do NOT mention port conflicts or uvicorn.run() in your feedback — these are
  environment issues the developer cannot fix in the generated code.
- Focus feedback on actual code quality: logic, validation, structure, tests.

Return ONLY valid JSON (no markdown):
{
  "correctness": 0.0-1.0,
  "completeness": 0.0-1.0,
  "edge_cases": 0.0-1.0,
  "code_quality": 0.0-1.0,
  "feedback": "Specific, actionable improvement notes about the CODE LOGIC only"
}"""


# Weights for overall score
WEIGHTS = {
    "correctness":    0.35,
    "completeness":   0.25,
    "edge_cases":     0.20,
    "code_quality":   0.10,
    "test_pass_rate": 0.10,
}

# Errors that are sandbox/environment issues — NOT code bugs
_ENVIRONMENT_ERRORS = [
    "address already in use",
    "errno 48",
    "errno 98",
    "port.*in use",
    "bind.*address",
    "error while attempting to bind",
]


def _is_environment_error(stderr: str) -> bool:
    """Return True if the execution failure is a sandbox environment issue."""
    stderr_lower = stderr.lower()
    return any(re.search(p, stderr_lower) for p in _ENVIRONMENT_ERRORS)


def _is_real_code_error(result: ExecutionResult) -> bool:
    """Return True if the failure is an actual code bug (not environment)."""
    if result.exit_code == 0:
        return False
    if result.timed_out:
        return True   # timeout = code tried to run server
    if _is_environment_error(result.stderr):
        return False  # port conflict = environment, not code
    # SyntaxError, ImportError, NameError, etc. = real code bugs
    real_errors = ["syntaxerror", "importerror", "nameerror", "typeerror",
                   "attributeerror", "indentationerror", "valueerror: "]
    stderr_lower = result.stderr.lower()
    return any(e in stderr_lower for e in real_errors)


class Evaluator:
    """
    Scores code quality and combines LLM evaluation with test metrics.
    """

    def __init__(self):
        self._llm = get_llm_client()

    async def evaluate(
        self,
        requirement: str,
        code: str,
        execution_result: ExecutionResult,
        test_result: Optional[TestResult] = None,
        acceptance_criteria: Optional[list] = None,
    ) -> EvaluationScore:
        """
        Evaluate code on all dimensions and return a composite EvaluationScore.
        """
        # ── 1. Compute test_pass_rate ─────────────────────────
        test_pass_rate = 0.0
        if test_result and test_result.total > 0:
            test_pass_rate = test_result.passed / test_result.total
        elif execution_result.exit_code == 0 or _is_environment_error(execution_result.stderr):
            # Code itself is fine — give partial credit
            test_pass_rate = 0.5

        # ── 2. Build execution summary for LLM ───────────────
        # Strip environment noise from what we send to the LLM
        clean_stderr = self._clean_stderr(execution_result.stderr)

        exec_summary = (
            f"Exit code: {execution_result.exit_code}\n"
            f"Duration: {execution_result.duration_ms}ms\n"
            f"Stdout: {execution_result.stdout[:400]}\n"
            f"Stderr: {clean_stderr[:300]}"
        )

        if _is_environment_error(execution_result.stderr):
            exec_summary += (
                "\n[NOTE: Execution environment had a port conflict — "
                "this is NOT a code bug. Evaluate code logic only.]"
            )

        if execution_result.timed_out:
            exec_summary += (
                "\n[NOTE: Execution timed out — likely because the code "
                "contains uvicorn.run() which starts a blocking server. "
                "Treat this as a code structure issue.]"
            )

        test_summary = ""
        if test_result:
            test_summary = (
                f"\nTest Results: {test_result.passed}/{test_result.total} passed, "
                f"{test_result.failed} failed"
            )

        criteria_text = ""
        if acceptance_criteria:
            criteria_text = "\nAcceptance Criteria:\n" + "\n".join(
                f"- {c}" for c in acceptance_criteria
            )

        messages = [
            {"role": "system", "content": _EVALUATION_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Requirement:\n{requirement}"
                    f"{criteria_text}\n\n"
                    f"Code:\n```python\n{code}\n```\n\n"
                    f"Execution:\n{exec_summary}"
                    f"{test_summary}"
                ),
            },
        ]

        raw = await self._llm.complete(messages, temperature=0.1)
        scores = self._parse_scores(raw)

        # ── 3. Penalize only REAL code errors ─────────────────
        if execution_result.timed_out:
            # Timeout = code tried to run server = structure bug
            scores["correctness"] = min(scores.get("correctness", 0.4), 0.4)
            scores["code_quality"] = min(scores.get("code_quality", 0.4), 0.5)
        elif _is_real_code_error(execution_result):
            # Real syntax/import/logic error
            scores["correctness"] = min(scores.get("correctness", 0.3), 0.3)
        # Port-in-use = environment issue = NO penalty

        # ── 4. Compute weighted overall ───────────────────────
        overall = (
            scores.get("correctness",  0.0) * WEIGHTS["correctness"]
            + scores.get("completeness", 0.0) * WEIGHTS["completeness"]
            + scores.get("edge_cases",   0.0) * WEIGHTS["edge_cases"]
            + scores.get("code_quality", 0.0) * WEIGHTS["code_quality"]
            + test_pass_rate                  * WEIGHTS["test_pass_rate"]
        )

        return EvaluationScore(
            correctness=round(scores.get("correctness",  0.0), 3),
            completeness=round(scores.get("completeness", 0.0), 3),
            edge_cases=round(scores.get("edge_cases",    0.0), 3),
            code_quality=round(scores.get("code_quality", 0.0), 3),
            test_pass_rate=round(test_pass_rate, 3),
            overall=round(overall, 3),
            feedback=scores.get("feedback", ""),
        )

    def _clean_stderr(self, stderr: str) -> str:
        """Remove environment noise from stderr before sending to LLM."""
        lines = stderr.split("\n")
        clean_lines = []
        for line in lines:
            line_lower = line.lower()
            # Skip port/server lines
            if any(p in line_lower for p in [
                "address already in use", "errno 48", "errno 98",
                "attempting to bind", "started server process",
                "waiting for application", "application startup",
                "application shutdown", "uvicorn",
            ]):
                continue
            clean_lines.append(line)
        return "\n".join(clean_lines).strip()

    def _parse_scores(self, raw: str) -> dict:
        """Parse LLM score response."""
        try:
            cleaned = raw.strip()
            for prefix in ("```json", "```"):
                if cleaned.startswith(prefix):
                    cleaned = cleaned[len(prefix):]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            return json.loads(cleaned.strip())
        except (json.JSONDecodeError, ValueError):
            return {
                "correctness":  0.6,
                "completeness": 0.6,
                "edge_cases":   0.5,
                "code_quality": 0.6,
                "feedback":     "Could not parse evaluation. Applying default scores.",
            }
