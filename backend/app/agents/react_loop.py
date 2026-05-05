"""
ReAct Loop Controller — Smart Intent Detection + Token Optimized
================================================================
Key improvement: Detects project type BEFORE generation.
  - Simple requests (calculator, todo, quiz, timer, game, form)
    → pure HTML+CSS+JS, no backend, works by opening index.html
  - Complex requests (blog API, auth system, REST API with DB)
    → FastAPI + SQLite backend + minimal HTML frontend

Token budget:
  Frontend only : 2 LLM calls (~$0.002 with gpt-4o-mini)
  Fullstack     : 3 LLM calls (~$0.004)
  Max 3 iters   : 6 LLM calls (~$0.008)
"""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from datetime import datetime
from typing import AsyncIterator, Optional

from app.core.config import settings
from app.core.database import get_db
from app.core.llm import get_llm_client
from app.models.schemas import (
    AgentPhase, EvaluationScore, ExecutionResult,
    Iteration, ReActStep, Session, SSEEvent, StepType, TestResult,
)
from app.tools.execution_tool import CodeExecutionTool


# ─────────────────────────────────────────────────────────────
# INTENT DETECTION — zero LLM calls, pure keyword matching
# ─────────────────────────────────────────────────────────────

# These ALWAYS use pure frontend (HTML+CSS+JS only, no backend)
_FRONTEND_ONLY_PATTERNS = [
    r"\bcalculator?\b", r"\btodo\b", r"\bto-do\b", r"\btask list\b",
    r"\btimer\b", r"\bstopwatch\b", r"\bclock\b", r"\bcountdown\b",
    r"\bquiz\b", r"\bflashcard", r"\bword game\b", r"\bsnake game\b",
    r"\btic.tac.toe\b", r"\bchess\b", r"\bpuzzle\b",
    r"\blanding page\b", r"\bportfolio\b", r"\bresume\b",
    r"\bform\b", r"\bsurvey\b", r"\bcontact page\b",
    r"\bdashboard\b", r"\bweather app\b", r"\bnotes? app\b",
    r"\bcolor picker\b", r"\bimage gallery\b", r"\bslideshow\b",
    r"\baccordion\b", r"\bnavbar\b", r"\bcard\b",
]

# These REQUIRE a backend
_FULLSTACK_PATTERNS = [
    r"\bapi\b", r"\brest\b", r"\bfastapi\b", r"\bflask\b",
    r"\bdatabase\b", r"\bsqlite\b", r"\bpostgres\b", r"\bmysql\b",
    r"\bauth(entication)?\b", r"\blogin\b", r"\bregister\b", r"\bjwt\b",
    r"\bblog\b", r"\bcms\b", r"\bbackend\b", r"\bserver\b",
    r"\bendpoint\b", r"\bscraper?\b", r"\bcrawler?\b",
    r"\bcron\b", r"\bschedul", r"\bemail\b", r"\bwebhook\b",
    r"\bwebsocket\b", r"\bchat app\b",
]


def detect_project_type(requirement: str) -> str:
    """
    Classify requirement as frontend_only, fullstack, or backend_only.
    No LLM call needed — pure regex matching.
    """
    req = requirement.lower()

    # Explicit backend signals win
    has_backend = any(re.search(p, req) for p in _FULLSTACK_PATTERNS)
    has_frontend = any(re.search(p, req) for p in _FRONTEND_ONLY_PATTERNS)

    # "blog with html" or "todo with api" edge cases
    wants_html = bool(re.search(r"\bhtml\b|\bweb\b|\bui\b|\binterface\b|\bpage\b|\bsite\b", req))

    if has_backend and not has_frontend:
        # Pure API request (no UI mentioned)
        if wants_html or "frontend" in req or "ui" in req:
            return "fullstack"
        return "backend_only" if not wants_html else "fullstack"

    if has_backend and has_frontend:
        return "fullstack"

    # Default: if it sounds like a UI thing, make it frontend
    return "frontend_only"


# ─────────────────────────────────────────────────────────────
# PROMPTS — one per project type
# ─────────────────────────────────────────────────────────────

_FRONTEND_PROMPT = """You are an expert front-end developer and UI designer.
Build a COMPLETE, BEAUTIFUL, WORKING single-page web app.

OUTPUT: One self-contained index.html file.
ALL CSS inside <style> in <head>.
ALL JavaScript inside <script> before </body>.
NO external JS libraries except what's loaded via CDN if needed.
NO fetch() calls to a backend — all data stored in JS variables/localStorage.

LAYOUT & DESIGN RULES — follow exactly:
1. CSS Grid or Flexbox for ALL layouts — never use float or table
2. CSS custom properties (variables) for colors/spacing
3. Google Fonts via <link> in <head> (Inter, Poppins, or Space Grotesk)
4. Consistent sizing: same-size buttons, uniform gaps (use gap: not margin)
5. Professional color scheme — NOT plain grey/white
6. Smooth CSS transitions on hover/focus/active states
7. Mobile responsive: viewport meta tag + max-width container + fluid widths
8. Meaningful visual hierarchy: heading → subheading → content → controls

CALCULATOR SPECIFIC (if building a calculator):
  - Grid layout: grid-template-columns: repeat(4, 1fr)
  - Display at top spanning all 4 columns
  - Digits 0-9, operators +,-,*,/, clear (C), equals (=), decimal (.)
  - Handle: divide by zero, multiple operators, leading zeros, decimals
  - Use eval() safely or implement your own parser

TODO/TASK SPECIFIC (if building todo/task list):
  - Input + Add button at top
  - Each task: checkbox to complete, task text, delete button
  - Strike-through + opacity for completed tasks
  - Empty state message when no tasks
  - Enter key to add task
  - Use localStorage to persist tasks

Return ONLY valid JSON (no markdown fences outside the JSON):
{
  "thought": "What I'm building, layout approach, key design decisions",
  "project_type": "frontend_only",
  "files": {
    "index.html": "COMPLETE HTML — DO NOT TRUNCATE"
  },
  "entry_point": "index.html",
  "how_to_run": "Open index.html in browser — no server needed"
}"""


_FULLSTACK_PROMPT = """You are an expert full-stack developer.
Build a COMPLETE, WORKING full-stack application.

Generate these files:
1. backend/main.py    — FastAPI app with SQLite (use sqlite3, NOT aiosqlite)
2. backend/requirements.txt — just: fastapi uvicorn
3. index.html         — minimal clean frontend that calls the API

BACKEND RULES:
- Use sqlite3 (standard library) — NO aiosqlite, NO SQLAlchemy
- Use StaticFiles to serve index.html from FastAPI
- Include CORS middleware
- All routes return proper JSON
- Include startup event to create tables
- Handle 404s properly with HTTPException
- DO NOT use deprecated @app.on_event — use lifespan instead

FRONTEND RULES:
- Calls backend API with fetch()
- Shows loading states
- Handles errors gracefully
- Clean, minimal UI

IMPORTANT: Use this lifespan pattern (not deprecated on_event):
  from contextlib import asynccontextmanager
  @asynccontextmanager
  async def lifespan(app):
      init_db()
      yield
  app = FastAPI(lifespan=lifespan)

Return ONLY valid JSON:
{
  "thought": "Architecture decisions and implementation plan",
  "project_type": "fullstack",
  "files": {
    "backend/main.py": "COMPLETE FastAPI code",
    "backend/requirements.txt": "fastapi\\nuvicorn",
    "index.html": "COMPLETE HTML frontend"
  },
  "entry_point": "backend/main.py",
  "how_to_run": "cd backend && pip install -r requirements.txt && uvicorn main:app --port 8001"
}"""


_BACKEND_PROMPT = """You are an expert Python/FastAPI developer.
Build a COMPLETE, WORKING backend application.

RULES:
- Use sqlite3 (standard library) — NOT aiosqlite
- Use lifespan pattern (not deprecated on_event)
- Include all CRUD operations needed
- Proper error handling with HTTPException
- Include requirements.txt
- Add a simple test using pytest + httpx

Return ONLY valid JSON:
{
  "thought": "Architecture and implementation plan",
  "project_type": "backend_only",
  "files": {
    "main.py": "COMPLETE FastAPI code",
    "requirements.txt": "fastapi\\nuvicorn\\nhttpx\\npytest",
    "test_main.py": "COMPLETE pytest tests"
  },
  "entry_point": "main.py",
  "how_to_run": "pip install -r requirements.txt && uvicorn main:app --port 8001"
}"""


_REFINE_PROMPT = """You are a senior developer fixing issues in an existing project.

Requirement: {requirement}
Project type: {project_type}
Issues to fix: {feedback}

Return the COMPLETE improved files. Never truncate.
Fix EVERY issue listed. Keep what works.

Return ONLY JSON:
{{
  "thought": "What I fixed",
  "files": {{
    "index.html": "COMPLETE improved HTML (if frontend)"
  }},
  "changes_made": ["Fixed X", "Improved Y"]
}}"""


_EVALUATE_PROMPT = """Senior code reviewer. Score this project objectively.

Requirement: {requirement}
Project type: {project_type}
Local validation: {local_checks}

Score 0.0-1.0 per dimension:
- correctness:  All logic works correctly, no broken features
- completeness: All required features are present
- edge_cases:   Error handling, invalid inputs handled
- code_quality: Clean, readable, well-structured

Return ONLY JSON (no markdown):
{{
  "correctness": 0.0,
  "completeness": 0.0,
  "edge_cases": 0.0,
  "code_quality": 0.0,
  "overall": 0.0,
  "feedback": "List specific bugs to fix. Be concrete and brief."
}}"""


# ─────────────────────────────────────────────────────────────
# Controller
# ─────────────────────────────────────────────────────────────

class ReActLoopController:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._llm = get_llm_client()
        self._executor = CodeExecutionTool()
        self._event_queue: asyncio.Queue[SSEEvent | None] = asyncio.Queue()

    async def run(self, session: Session) -> AsyncIterator[SSEEvent]:
        loop_task = asyncio.create_task(self._run_loop(session))
        while True:
            event = await self._event_queue.get()
            if event is None:
                break
            yield event
        if not loop_task.cancelled():
            await loop_task

    # ─────────────────────────────────────────────────────────
    # EXPLICIT ReAct LOOP
    # ─────────────────────────────────────────────────────────

    async def _run_loop(self, session: Session) -> None:
        """
        while score < threshold and iter < max:
            thought, code = think_and_generate()   # 1 LLM call
            exec_result   = validate_locally()     # 0 LLM calls
            score         = evaluate()             # 1 LLM call
            if score < threshold: plan_refinement()
        """
        db = get_db()
        score = 0.0
        iteration_number = 0
        current_files: dict = {}
        current_code = ""
        current_score: Optional[EvaluationScore] = None
        refined_req = session.refined_requirement or session.raw_requirement

        # ── Detect project type BEFORE any LLM call ──────────
        project_type = detect_project_type(refined_req)

        await self._emit("agent_started", {
            "message": f"ReAct loop started — detected: {project_type}",
            "project_type": project_type,
            "max_iterations": settings.MAX_ITERATIONS,
            "threshold": settings.QUALITY_THRESHOLD,
            "model": settings.OPENAI_MODEL,
        })

        try:
            while score < settings.QUALITY_THRESHOLD and iteration_number < settings.MAX_ITERATIONS:
                iteration_number += 1
                iteration = Iteration(
                    iteration_number=iteration_number,
                    session_id=self.session_id,
                )

                await self._emit("iteration_start", {
                    "iteration": iteration_number,
                    "current_score": round(score, 3),
                    "project_type": project_type,
                })

                # ── THINK + ACT (1 LLM call) ─────────────────
                await self._emit("phase_change", {"phase": AgentPhase.PLANNING})

                if iteration_number == 1:
                    gen_result = await self._generate(refined_req, project_type)
                else:
                    gen_result = await self._refine(
                        refined_req, project_type,
                        current_files,
                        current_score.feedback if current_score else "",
                    )

                thought_text = gen_result.get("thought", f"Iteration {iteration_number}: generating {project_type} project")
                new_files    = gen_result.get("files", {})

                # Merge files (keep existing, override with new)
                current_files = {**current_files, **{k: v for k, v in new_files.items() if v and len(v) > 20}}
                current_code  = json.dumps({
                    "project_type": project_type,
                    "files": current_files,
                    "entry_point": gen_result.get("entry_point", "index.html"),
                    "how_to_run":  gen_result.get("how_to_run", "Open index.html in browser"),
                })
                iteration.generated_code = current_code

                # Emit THOUGHT
                iteration.steps.append(ReActStep(
                    step_type=StepType.THOUGHT, content=thought_text, metadata={}
                ))
                await self._emit("thought", {"iteration": iteration_number, "content": thought_text})

                # Emit ACTION
                entry = gen_result.get("entry_point", "index.html")
                primary = current_files.get(entry, next(iter(current_files.values()), ""))
                iteration.steps.append(ReActStep(
                    step_type=StepType.ACTION,
                    content=f"Generated: {list(current_files.keys())}",
                    metadata={
                        "files": list(current_files.keys()),
                        "full_code": current_code,
                        "changes_made": gen_result.get("changes_made", []),
                    },
                ))
                await self._emit("action", {
                    "iteration": iteration_number,
                    "action": f"{'Initial generation' if iteration_number == 1 else 'Refinement'} ({project_type})",
                    "code_preview": primary[:400],
                    "full_code": current_code,
                    "changes_made": gen_result.get("changes_made", []),
                })

                # ── OBSERVE — local validation, 0 LLM calls ──
                await self._emit("phase_change", {"phase": AgentPhase.EXECUTION})
                exec_result = self._validate_locally(current_files, project_type)
                test_result = self._score_locally(current_files, project_type, refined_req)
                iteration.execution_result = exec_result
                iteration.test_result      = test_result

                obs_text = (
                    f"Validated {len(current_files)} file(s) — "
                    f"{test_result.passed}/{test_result.total} checks passed"
                )
                iteration.steps.append(ReActStep(
                    step_type=StepType.OBSERVATION, content=obs_text,
                    metadata={"exit_code": exec_result.exit_code,
                              "tests_passed": test_result.passed,
                              "tests_total": test_result.total},
                ))
                await self._emit("observation", {
                    "iteration": iteration_number,
                    "content": obs_text,
                    "execution": exec_result.model_dump(),
                    "tests": test_result.model_dump(),
                })

                # ── EVALUATE (1 LLM call) ─────────────────────
                await self._emit("phase_change", {"phase": AgentPhase.EVALUATION})
                eval_result = await self._evaluate(
                    refined_req, current_files, project_type, test_result
                )

                # Compute overall ourselves — don't trust LLM's "overall"
                raw = {
                    "correctness":  max(0.0, min(1.0, float(eval_result.get("correctness",  0.7)))),
                    "completeness": max(0.0, min(1.0, float(eval_result.get("completeness", 0.7)))),
                    "edge_cases":   max(0.0, min(1.0, float(eval_result.get("edge_cases",   0.6)))),
                    "code_quality": max(0.0, min(1.0, float(eval_result.get("code_quality", 0.7)))),
                }
                local_rate = test_result.passed / max(test_result.total, 1)
                overall = round(
                    raw["correctness"]  * 0.35 +
                    raw["completeness"] * 0.25 +
                    raw["edge_cases"]   * 0.20 +
                    raw["code_quality"] * 0.10 +
                    local_rate          * 0.10,
                    3
                )

                current_score = EvaluationScore(
                    correctness=round(raw["correctness"],  3),
                    completeness=round(raw["completeness"], 3),
                    edge_cases=round(raw["edge_cases"],    3),
                    code_quality=round(raw["code_quality"], 3),
                    test_pass_rate=round(local_rate, 3),
                    overall=overall,
                    feedback=eval_result.get("feedback", ""),
                )
                score = overall
                iteration.score = current_score

                iteration.steps.append(ReActStep(
                    step_type=StepType.EVALUATION,
                    content=(
                        f"Overall: {score:.2f} | "
                        f"Correctness: {current_score.correctness:.2f} | "
                        f"Completeness: {current_score.completeness:.2f} | "
                        f"Edge Cases: {current_score.edge_cases:.2f}\n"
                        f"Feedback: {current_score.feedback}"
                    ),
                    metadata=current_score.model_dump(),
                ))
                await self._emit("evaluation", {
                    "iteration": iteration_number,
                    "score": current_score.model_dump(),
                    "threshold": settings.QUALITY_THRESHOLD,
                    "threshold_met": score >= settings.QUALITY_THRESHOLD,
                })

                # ── REFINEMENT note ───────────────────────────
                if score < settings.QUALITY_THRESHOLD and iteration_number < settings.MAX_ITERATIONS:
                    await self._emit("phase_change", {"phase": AgentPhase.REFINEMENT})
                    iteration.steps.append(ReActStep(
                        step_type=StepType.REFINEMENT,
                        content=f"Will fix in next iteration: {current_score.feedback}",
                        metadata={},
                    ))
                    await self._emit("refinement", {
                        "iteration": iteration_number,
                        "notes": current_score.feedback,
                        "plan": {},
                    })

                # Persist
                session.iterations.append(iteration)
                session.total_iterations = iteration_number
                session.updated_at = datetime.utcnow()
                await db.iterations.insert_one(
                    {**iteration.model_dump(), "_id": str(uuid.uuid4())}
                )
                await db.sessions.update_one(
                    {"session_id": self.session_id},
                    {"$set": session.model_dump()},
                )
                await self._emit("iteration_end", {
                    "iteration": iteration_number,
                    "score": round(score, 3),
                    "threshold_met": score >= settings.QUALITY_THRESHOLD,
                })

            # ── Completion ────────────────────────────────────
            session.final_code  = current_code
            session.final_score = current_score
            session.success     = score >= settings.QUALITY_THRESHOLD
            session.phase       = AgentPhase.COMPLETED
            await db.sessions.update_one(
                {"session_id": self.session_id},
                {"$set": session.model_dump()},
            )
            await self._emit("completed", {
                "session_id": self.session_id,
                "final_score": round(score, 3),
                "total_iterations": iteration_number,
                "success": session.success,
                "final_code": current_code,
                "project_type": project_type,
            })

        except Exception as exc:
            import traceback
            session.phase = AgentPhase.FAILED
            await db.sessions.update_one(
                {"session_id": self.session_id},
                {"$set": {"phase": AgentPhase.FAILED}},
            )
            await self._emit("error", {
                "message": str(exc),
                "trace": traceback.format_exc()[-800:],
            })
        finally:
            await self._event_queue.put(None)

    # ─────────────────────────────────────────────────────────
    # LLM CALLS — kept lean
    # ─────────────────────────────────────────────────────────

    def _get_system_prompt(self, project_type: str) -> str:
        return {
            "frontend_only": _FRONTEND_PROMPT,
            "fullstack":     _FULLSTACK_PROMPT,
            "backend_only":  _BACKEND_PROMPT,
        }.get(project_type, _FRONTEND_PROMPT)

    async def _generate(self, requirement: str, project_type: str) -> dict:
        """LLM Call 1: Think + Generate."""
        messages = [
            {"role": "system", "content": self._get_system_prompt(project_type)},
            {"role": "user",   "content": f"Requirement: {requirement}"},
        ]
        raw = await self._llm.complete(
            messages, temperature=0.2,
            max_tokens=settings.MAX_TOKENS_GENERATION,
        )
        return self._parse_json(raw, fallback={
            "thought": "Generating project",
            "project_type": project_type,
            "files": {"index.html": raw},
            "entry_point": "index.html",
        })

    async def _refine(
        self, requirement: str, project_type: str,
        current_files: dict, feedback: str
    ) -> dict:
        """LLM Call 1 (iter 2+): Fix issues from feedback."""
        # Pick primary file to send — don't send everything
        priority_order = ["index.html", "backend/main.py", "main.py"]
        primary_key = next(
            (k for k in priority_order if k in current_files),
            next(iter(current_files), "")
        )
        primary_content = current_files.get(primary_key, "")

        prompt = _REFINE_PROMPT.format(
            requirement=requirement,
            project_type=project_type,
            feedback=feedback,
        )
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user",   "content": (
                f"Current {primary_key}:\n{primary_content}\n\n"
                "Return complete improved files in JSON."
            )},
        ]
        raw = await self._llm.complete(
            messages, temperature=0.2,
            max_tokens=settings.MAX_TOKENS_GENERATION,
        )
        return self._parse_json(raw, fallback={
            "thought": "Refining",
            "files": current_files,
            "changes_made": [],
        })

    async def _evaluate(
        self, requirement: str, files: dict,
        project_type: str, test_result: TestResult,
    ) -> dict:
        """LLM Call 2: Evaluate quality. Cheap — only 500 tokens output."""
        # Send primary file for evaluation
        priority_order = ["index.html", "backend/main.py", "main.py"]
        primary_key = next(
            (k for k in priority_order if k in files),
            next(iter(files), "")
        )
        content_preview = files.get(primary_key, "")[:2500]

        local_summary = (
            f"{test_result.passed}/{test_result.total} checks passed. "
            + " | ".join(test_result.details[:6])
        )
        prompt = _EVALUATE_PROMPT.format(
            requirement=requirement,
            project_type=project_type,
            local_checks=local_summary,
        )
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user",   "content": f"Code ({primary_key}):\n{content_preview}"},
        ]
        raw = await self._llm.complete(
            messages, temperature=0.1,
            max_tokens=settings.MAX_TOKENS_EVALUATION,
        )
        return self._parse_json(raw, fallback={
            "correctness": 0.7, "completeness": 0.7,
            "edge_cases": 0.6,  "code_quality": 0.7,
            "overall": 0.68,    "feedback": "Looks reasonable. Check manually.",
        })

    # ─────────────────────────────────────────────────────────
    # LOCAL VALIDATION — zero LLM calls
    # ─────────────────────────────────────────────────────────

    def _validate_locally(self, files: dict, project_type: str) -> ExecutionResult:
        errors = []
        for fname, content in files.items():
            if not content or len(content) < 50:
                errors.append(f"{fname}: file is empty or too short")
                continue
            if fname.endswith(".html"):
                lo = content.lower()
                if "<html" not in lo: errors.append(f"{fname}: missing <html> tag")
                if "<body" not in lo: errors.append(f"{fname}: missing <body> tag")
            elif fname.endswith(".py"):
                import subprocess, sys, tempfile, os
                with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                    f.write(content)
                    tmp = f.name
                try:
                    r = subprocess.run(
                        [sys.executable, "-m", "py_compile", tmp],
                        capture_output=True, text=True, timeout=10
                    )
                    if r.returncode != 0:
                        errors.append(f"{fname} syntax error: {r.stderr[:100]}")
                finally:
                    os.unlink(tmp)
        return ExecutionResult(
            stdout=f"Validated {len(files)} files",
            stderr="\n".join(errors),
            exit_code=1 if errors else 0,
            timed_out=False, duration_ms=5,
        )

    def _score_locally(self, files: dict, project_type: str, requirement: str) -> TestResult:
        """Heuristic scoring — no LLM call."""
        passed, failed = [], []

        def chk(cond: bool, label: str):
            lst = passed if cond else failed
            lst.append(("PASSED: " if cond else "FAILED: ") + label)

        req = requirement.lower()
        all_html_lo = " ".join(
            c.lower() for f, c in files.items() if f.endswith(".html")
        )
        all_py = " ".join(c for f, c in files.items() if f.endswith(".py"))
        total_chars = sum(len(v) for v in files.values())

        # ── Universal ─────────────────────────────────────────
        chk(len(files) > 0,      "Project has files")
        chk(total_chars > 500,   "Has sufficient code")

        # ── Frontend checks ───────────────────────────────────
        if project_type in ("frontend_only", "fullstack"):
            chk(any(f.endswith(".html") for f in files),       "Has HTML file")
            chk("<script" in all_html_lo,                      "Has JavaScript")
            chk("<style" in all_html_lo or
                any(f.endswith(".css") for f in files),         "Has CSS styling")
            chk("function" in all_html_lo or
                "=>" in all_html_lo,                            "Has JS functions")
            chk("addeventlistener" in all_html_lo or
                "onclick" in all_html_lo,                       "Has event handlers")
            chk("viewport" in all_html_lo,                     "Responsive (viewport meta)")
            chk("font-family" in all_html_lo or
                "fonts.google" in all_html_lo,                  "Has custom typography")
            chk("grid" in all_html_lo or
                "flex" in all_html_lo,                          "Uses grid/flex layout")

        # ── Feature-specific ──────────────────────────────────
        if "calculator" in req or "calculat" in req:
            chk("input" in all_html_lo or
                "display" in all_html_lo,                       "Has number display")
            chk(all(op in all_html_lo for op in ["+", "-", "*", "/"]),
                                                                "Has all 4 operators")
            chk("eval(" in all_html_lo or
                "result" in all_html_lo,                        "Has calculation logic")
            chk("error" in all_html_lo or
                "isnan" in all_html_lo or
                "infinity" in all_html_lo,                      "Handles errors (div/0, NaN)")
            chk("grid" in all_html_lo,                         "Uses CSS grid for button layout")

        elif "todo" in req or "task" in req:
            # Frontend todo: no fetch() calls — uses localStorage
            if project_type == "frontend_only":
                chk("fetch(" not in all_html_lo,               "No unnecessary API calls")
                chk("localstorage" in all_html_lo or
                    "const tasks" in all_html_lo or
                    "let tasks" in all_html_lo,                 "Stores tasks in JS/localStorage")
            chk("input" in all_html_lo,                        "Has task input field")
            chk("delete" in all_html_lo or
                "remove" in all_html_lo,                        "Has delete functionality")
            chk("addeventlistener" in all_html_lo or
                "onclick" in all_html_lo,                       "Has click handlers")
            chk("li" in all_html_lo or
                "task-item" in all_html_lo,                     "Has task list items")
            chk("completed" in all_html_lo or
                "line-through" in all_html_lo or
                "checkbox" in all_html_lo,                      "Has task completion feature")

        elif "quiz" in req or "game" in req:
            chk("score" in all_html_lo or "point" in all_html_lo, "Has scoring")
            chk("question" in all_html_lo or
                "answer" in all_html_lo,                        "Has questions/answers")

        # ── Backend checks ────────────────────────────────────
        if project_type in ("fullstack", "backend_only"):
            chk(any(f.endswith(".py") for f in files),         "Has Python backend")
            chk("fastapi" in all_py.lower(),                   "Uses FastAPI")
            chk("def " in all_py,                              "Has route functions")
            chk("sqlite3" in all_py.lower() or
                "database" in all_py.lower(),                   "Has database")
            chk("lifespan" in all_py.lower() or
                "startup" in all_py.lower(),                    "Has app startup handler")
            chk("aiosqlite" not in all_py.lower(),             "Uses sqlite3 (not aiosqlite)")

        all_checks = passed + failed
        return TestResult(
            total=len(all_checks),
            passed=len(passed),
            failed=len(failed),
            errors=0,
            details=all_checks,
        )

    # ─────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────

    def _parse_json(self, raw: str, fallback: dict) -> dict:
        try:
            cleaned = raw.strip()
            for prefix in ("```json", "```"):
                if cleaned.startswith(prefix):
                    cleaned = cleaned[len(prefix):]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            return json.loads(cleaned.strip())
        except (json.JSONDecodeError, ValueError):
            return fallback

    async def _emit(self, event_type: str, data: dict) -> None:
        from app.models.schemas import SSEEvent
        event = SSEEvent(event=event_type, data=data, session_id=self.session_id)
        await self._event_queue.put(event)
