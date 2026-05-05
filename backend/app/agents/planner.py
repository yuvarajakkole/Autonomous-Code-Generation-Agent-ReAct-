"""
Planner Component (Thought Generator)
======================================
Analyses the current agent state and produces a structured Thought:
  - What has been accomplished so far?
  - What is the next best action?
  - What specific improvements should be targeted?

This is the "Reason" step in the ReAct loop.
"""

from __future__ import annotations

import json
from typing import Optional

from app.core.llm import get_llm_client
from app.models.schemas import EvaluationScore, Iteration


_PLANNER_SYSTEM = """You are the planning component of a ReAct code generation agent.
Your job is to reason about the current state and determine the best next action.

Given:
- The original requirement
- Current iteration number
- Previous iteration results (if any)
- Current quality scores

Produce a structured thought process including:
1. Summary of what has been achieved
2. Identified problems / gaps
3. Specific next action to take
4. Expected improvement from that action

Return ONLY valid JSON:
{
  "summary": "What has been done so far",
  "identified_problems": ["problem1", "problem2"],
  "next_action": "Specific action to take next",
  "rationale": "Why this action will improve quality",
  "focus_areas": ["area1", "area2"]
}"""


class Planner:
    """
    Generates structured Thought steps for the ReAct loop.
    """

    def __init__(self):
        self._llm = get_llm_client()

    async def think(
        self,
        requirement: str,
        iteration_number: int,
        previous_iteration: Optional[Iteration] = None,
        current_score: Optional[EvaluationScore] = None,
    ) -> dict:
        """
        Generate a structured Thought based on current agent state.
        """
        context = self._build_context(
            requirement, iteration_number, previous_iteration, current_score
        )

        messages = [
            {"role": "system", "content": _PLANNER_SYSTEM},
            {"role": "user", "content": context},
        ]

        raw = await self._llm.complete(messages, temperature=0.2)

        try:
            cleaned = raw.strip()
            for prefix in ("```json", "```"):
                if cleaned.startswith(prefix):
                    cleaned = cleaned[len(prefix):]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            thought = json.loads(cleaned.strip())
        except json.JSONDecodeError:
            thought = {
                "summary": f"Starting iteration {iteration_number}",
                "identified_problems": [],
                "next_action": "Generate and test code",
                "rationale": "Initial generation",
                "focus_areas": ["implementation", "correctness"],
            }

        return thought

    def _build_context(
        self,
        requirement: str,
        iteration_number: int,
        previous_iteration: Optional[Iteration],
        current_score: Optional[EvaluationScore],
    ) -> str:
        parts = [
            f"Requirement:\n{requirement}",
            f"\nCurrent Iteration: {iteration_number}",
        ]

        if previous_iteration and current_score:
            parts.append(f"\nPrevious Score: {current_score.overall:.2f}")
            parts.append(f"Correctness: {current_score.correctness:.2f}")
            parts.append(f"Completeness: {current_score.completeness:.2f}")
            parts.append(f"Edge Cases: {current_score.edge_cases:.2f}")
            parts.append(f"Test Pass Rate: {current_score.test_pass_rate:.2f}")

            if current_score.feedback:
                parts.append(f"\nFeedback:\n{current_score.feedback}")

            if previous_iteration.execution_result:
                r = previous_iteration.execution_result
                parts.append(f"\nLast Execution: exit_code={r.exit_code}")
                if r.stderr:
                    parts.append(f"Errors:\n{r.stderr[:300]}")

            if previous_iteration.test_result:
                t = previous_iteration.test_result
                parts.append(
                    f"\nTests: {t.passed}/{t.total} passed, {t.failed} failed"
                )

        return "\n".join(parts)

    def format_thought(self, thought: dict) -> str:
        """Format thought dict as a human-readable string."""
        lines = [
            f"📊 Summary: {thought.get('summary', '')}",
        ]
        if problems := thought.get("identified_problems"):
            lines.append("⚠️  Problems: " + ", ".join(problems))
        lines.append(f"🎯 Next Action: {thought.get('next_action', '')}")
        lines.append(f"💡 Rationale: {thought.get('rationale', '')}")
        if focus := thought.get("focus_areas"):
            lines.append("🔍 Focus Areas: " + ", ".join(focus))
        return "\n".join(lines)
