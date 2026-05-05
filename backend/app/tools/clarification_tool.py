"""
Tool 1: Requirement Clarification Tool — Token Optimized
=========================================================
Single LLM call that generates questions AND refines requirement together.
Skips clarification entirely for simple/clear requirements.
"""

from __future__ import annotations
import json
from typing import Dict, List
from app.core.llm import get_llm_client
from app.models.schemas import ClarificationQA


# Simple requirements that don't need clarification
_SKIP_CLARIFICATION_KEYWORDS = [
    "calculator", "todo", "timer", "clock", "counter", "quiz",
    "game", "weather", "chat", "form", "landing page", "portfolio",
]

_COMBINED_PROMPT = """Analyse this requirement. If clear enough, ask 3 short questions.
Return ONLY JSON: {"questions": ["Q1", "Q2", "Q3"], "skip": false}
If requirement is very clear (e.g. "build a calculator"), return: {"questions": [], "skip": true}"""

_REFINE_PROMPT = """Given requirement + Q&A, write a single refined requirement sentence.
Return ONLY JSON: {"refined_requirement": "...", "acceptance_criteria": ["c1","c2","c3"]}"""


class RequirementClarificationTool:
    name = "requirement_clarification"
    description = "Analyses requirements and generates clarifying questions"

    def __init__(self):
        self._llm = get_llm_client()

    def _is_simple(self, requirement: str) -> bool:
        """Skip clarification for common simple requirements."""
        req_lower = requirement.lower()
        return any(kw in req_lower for kw in _SKIP_CLARIFICATION_KEYWORDS)

    async def generate_questions(self, requirement: str) -> List[str]:
        # Simple requirements → skip clarification entirely, save 1 LLM call
        if self._is_simple(requirement):
            return []

        messages = [
            {"role": "system", "content": _COMBINED_PROMPT},
            {"role": "user",   "content": requirement},
        ]
        raw = await self._llm.complete(messages, temperature=0.1, max_tokens=200)
        try:
            data = json.loads(raw.strip().lstrip("```json").lstrip("```").rstrip("```"))
            if data.get("skip"):
                return []
            return data.get("questions", [])[:3]  # max 3 questions
        except json.JSONDecodeError:
            return []  # on parse failure, skip clarification

    async def refine_requirement(self, original: str, qa_pairs: List[ClarificationQA]) -> Dict:
        if not qa_pairs:
            # No Q&A — return original as-is, save 1 LLM call
            return {
                "refined_requirement": original,
                "acceptance_criteria": [],
            }

        qa_text = "\n".join(f"Q: {p.question}\nA: {p.answer}" for p in qa_pairs)
        messages = [
            {"role": "system", "content": _REFINE_PROMPT},
            {"role": "user",   "content": f"Requirement: {original}\n\nQ&A:\n{qa_text}"},
        ]
        raw = await self._llm.complete(messages, temperature=0.1, max_tokens=250)
        try:
            return json.loads(raw.strip().lstrip("```json").lstrip("```").rstrip("```"))
        except json.JSONDecodeError:
            return {"refined_requirement": original, "acceptance_criteria": []}
