"""
Refiner Component
==================
Uses evaluation feedback to produce targeted improvement instructions
for the code generator in the next iteration.
"""

from __future__ import annotations

import json
from typing import Optional

from app.core.llm import get_llm_client
from app.models.schemas import EvaluationScore, Iteration


_REFINER_SYSTEM = """You are a code improvement specialist in a ReAct agent loop.
Analyse the evaluation feedback and produce a precise refinement plan.

Return ONLY valid JSON:
{
  "priority_fixes": ["fix1", "fix2"],
  "suggested_approach": "...",
  "code_patterns_to_add": ["pattern1"],
  "code_patterns_to_remove": ["antipattern1"],
  "refinement_prompt": "Direct instruction for the code generator"
}"""


class Refiner:
    """
    Produces targeted refinement instructions from evaluation feedback.
    """

    def __init__(self):
        self._llm = get_llm_client()

    async def plan_refinement(
        self,
        requirement: str,
        current_code: str,
        score: EvaluationScore,
        iteration: Iteration,
    ) -> dict:
        """Generate a refinement plan based on evaluation feedback."""

        exec_info = ""
        if iteration.execution_result:
            r = iteration.execution_result
            exec_info = f"\nExecution exit_code={r.exit_code}\nStderr: {r.stderr[:400]}"

        test_info = ""
        if iteration.test_result:
            t = iteration.test_result
            test_info = f"\nTests: {t.passed}/{t.total} passed\nDetails: {chr(10).join(t.details[:5])}"

        messages = [
            {"role": "system", "content": _REFINER_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Requirement:\n{requirement}\n\n"
                    f"Current Code:\n```python\n{current_code[:2000]}\n```\n\n"
                    f"Scores:\n"
                    f"  overall={score.overall:.2f} correctness={score.correctness:.2f} "
                    f"completeness={score.completeness:.2f} edge_cases={score.edge_cases:.2f} "
                    f"test_pass_rate={score.test_pass_rate:.2f}\n\n"
                    f"Feedback:\n{score.feedback}"
                    f"{exec_info}"
                    f"{test_info}"
                ),
            },
        ]

        raw = await self._llm.complete(messages, temperature=0.15)
        try:
            cleaned = raw.strip().lstrip("```json").lstrip("```").rstrip("```")
            return json.loads(cleaned.strip())
        except json.JSONDecodeError:
            return {
                "priority_fixes": [score.feedback],
                "suggested_approach": "Fix identified issues",
                "refinement_prompt": score.feedback,
            }

    def format_notes(self, plan: dict) -> str:
        lines = []
        if fixes := plan.get("priority_fixes"):
            lines.append("Priority Fixes: " + "; ".join(fixes))
        if approach := plan.get("suggested_approach"):
            lines.append(f"Approach: {approach}")
        return "\n".join(lines) if lines else "Apply general improvements."
