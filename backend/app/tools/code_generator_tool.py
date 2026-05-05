"""
Tool 2: Code Generator Tool
============================
Now delegates all generation to the react_loop directly.
This file kept for backward compatibility only.
"""
from __future__ import annotations
import json, re
from typing import Dict, Optional
from app.core.llm import get_llm_client

class CodeGeneratorTool:
    name = "code_generator"
    description = "Generates complete runnable web projects"

    def __init__(self):
        self._llm = get_llm_client()

    async def generate(self, requirement: str, key_features=None, constraints=None) -> Dict:
        return {"code": "", "files": {}, "project_type": "frontend_only"}

    async def refine(self, requirement, previous_code, execution_output,
                     test_output, evaluation_feedback, iteration) -> Dict:
        return {"code": previous_code, "changes_made": []}

    def _parse_code_response(self, raw: str) -> Dict:
        return {"code": raw, "files": {}}

    def _strip_server_code(self, code: str) -> str:
        return code
