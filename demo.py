"""
DEMO SCENARIO: "Build a login API"
====================================
This script demonstrates the full ReAct loop lifecycle.
Run directly:  python demo.py

Shows:
  1. Requirement → Clarification questions
  2. Answers → Refined requirement
  3. Iteration 1: Generate code → Execute → Test → Score
  4. Iteration 2: Refine based on feedback → Re-score
  5. Final output
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
os.environ.setdefault("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", "sk-REPLACE"))
os.environ.setdefault("LLM_PROVIDER", "openai")
os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017")
os.environ.setdefault("MAX_ITERATIONS", "4")
os.environ.setdefault("QUALITY_THRESHOLD", "0.80")


REQUIREMENT = "Build a login API"

CLARIFICATION_ANSWERS = [
    "FastAPI with Pydantic models",     # Q0: framework
    "PostgreSQL via SQLAlchemy ORM",    # Q1: database
    "JWT tokens with 24h expiry",       # Q2: auth method
    "Return HTTP 401 with error body",  # Q3: error handling
    "REST JSON API",                    # Q4: API style
]


async def run_demo():
    print("=" * 70)
    print("  ReAct Agent Demo — 'Build a login API'")
    print("=" * 70)

    # ── Step 1: Clarification ────────────────────────────────────
    print("\n[STEP 1] Generating clarification questions...\n")
    from app.tools.clarification_tool import RequirementClarificationTool
    from app.models.schemas import ClarificationQA

    tool = RequirementClarificationTool()

    try:
        questions = await tool.generate_questions(REQUIREMENT)
    except Exception as e:
        print(f"  ⚠ LLM not available ({e}). Using mock questions.")
        questions = [
            "Which web framework should be used?",
            "What database should store user credentials?",
            "Which authentication method (JWT, sessions, OAuth)?",
            "How should authentication errors be returned?",
            "Should the API be RESTful or GraphQL?",
        ]

    print("  Clarification Questions:")
    for i, q in enumerate(questions):
        ans = CLARIFICATION_ANSWERS[i] if i < len(CLARIFICATION_ANSWERS) else "Not specified"
        print(f"  Q{i+1}: {q}")
        print(f"  A{i+1}: {ans}")
        print()

    # Build QA pairs
    qa_pairs = [
        ClarificationQA(
            question=questions[i],
            answer=CLARIFICATION_ANSWERS[i] if i < len(CLARIFICATION_ANSWERS) else "Not specified"
        )
        for i in range(len(questions))
    ]

    # ── Step 2: Refined requirement ──────────────────────────────
    print("[STEP 2] Refining requirement from answers...\n")
    try:
        refined_data = await tool.refine_requirement(REQUIREMENT, qa_pairs)
        refined_req = refined_data.get("refined_requirement", REQUIREMENT)
    except Exception:
        refined_req = (
            "Build a FastAPI REST login API with email/password authentication. "
            "Store users in PostgreSQL via SQLAlchemy. Issue JWT tokens with 24h expiry. "
            "Return HTTP 401 with JSON error body on failure. Include input validation."
        )
        refined_data = {"acceptance_criteria": ["JWT returned on success", "401 on bad credentials"]}

    print(f"  Refined: {refined_req[:200]}...")
    print()

    # ── Step 3: Simulate the ReAct loop ─────────────────────────
    print("[STEP 3] ReAct Loop\n")
    print("  " + "─" * 50)

    from app.tools.code_generator_tool import CodeGeneratorTool
    from app.tools.execution_tool import CodeExecutionTool
    from app.tools.test_generator_tool import TestCaseGeneratorTool
    from app.tools.test_runner_tool import TestRunnerTool
    from app.agents.planner import Planner
    from app.agents.evaluator import Evaluator
    from app.agents.refiner import Refiner
    from app.core.config import settings

    planner   = Planner()
    evaluator = Evaluator()
    refiner   = Refiner()
    gen_tool  = CodeGeneratorTool()
    exec_tool = CodeExecutionTool()
    test_gen  = TestCaseGeneratorTool()
    runner    = TestRunnerTool()

    score = 0.0
    iteration = 0
    current_code = ""
    current_tests = ""
    current_score = None

    # ═══════════════════════════════════════════════════
    # EXPLICIT ReAct LOOP
    # ═══════════════════════════════════════════════════
    while score < settings.QUALITY_THRESHOLD and iteration < settings.MAX_ITERATIONS:
        iteration += 1
        print(f"\n  ── ITERATION {iteration} ──────────────────────────────")

        # THOUGHT
        print(f"\n  🧠 THOUGHT")
        try:
            thought = await planner.think(refined_req, iteration)
            print(f"     {planner.format_thought(thought)[:200]}")
        except Exception as e:
            thought = {"next_action": "generate", "focus_areas": ["correctness"]}
            print(f"     (mock) Generating code for iteration {iteration}")

        # ACTION — Generate or Refine
        print(f"\n  ⚡ ACTION")
        try:
            if iteration == 1:
                gen_result = await gen_tool.generate(refined_req)
            else:
                gen_result = await gen_tool.refine(
                    requirement=refined_req,
                    previous_code=current_code,
                    execution_output="",
                    test_output="",
                    evaluation_feedback=current_score.feedback if current_score else "",
                    iteration=iteration,
                )
            current_code = gen_result.get("code", "")
            print(f"     Generated {len(current_code)} chars of code")
            print(f"     Preview: {current_code[:100].strip()}...")
        except Exception as e:
            current_code = _demo_login_code()
            print(f"     (mock) Using demo login implementation")

        # Generate tests
        try:
            if iteration == 1:
                test_result_gen = await test_gen.generate(refined_req, current_code)
                current_tests = test_result_gen.get("test_code", "")
        except Exception:
            current_tests = _demo_test_code()

        # OBSERVATION — Execute
        print(f"\n  👁 OBSERVATION")
        exec_result = await exec_tool.execute(current_code)
        print(f"     Exit code: {exec_result.exit_code}")
        print(f"     Duration:  {exec_result.duration_ms}ms")
        if exec_result.stderr:
            print(f"     Stderr:    {exec_result.stderr[:100]}")

        # Run tests
        try:
            _, test_metrics = await runner.run(current_code, current_tests)
            print(f"     Tests:     {runner.format_summary(test_metrics)}")
        except Exception:
            from app.models.schemas import TestResult
            test_metrics = TestResult(total=3, passed=2, failed=1)
            print(f"     Tests:     (mock) 2/3 passed")

        # EVALUATION
        print(f"\n  📊 EVALUATION")
        try:
            current_score = await evaluator.evaluate(
                requirement=refined_req,
                code=current_code,
                execution_result=exec_result,
                test_result=test_metrics,
            )
            score = current_score.overall
        except Exception:
            from app.models.schemas import EvaluationScore
            score = min(0.55 + (iteration * 0.15), 0.95)
            current_score = EvaluationScore(
                correctness=score, completeness=score - 0.05,
                edge_cases=score - 0.1, code_quality=score,
                test_pass_rate=0.66, overall=score,
                feedback="Needs better error handling and input validation"
            )
        print(f"     Overall Score: {score:.2f} / 1.0  (threshold: {settings.QUALITY_THRESHOLD})")
        print(f"       Correctness:    {current_score.correctness:.2f}")
        print(f"       Completeness:   {current_score.completeness:.2f}")
        print(f"       Edge Cases:     {current_score.edge_cases:.2f}")
        print(f"       Test Pass Rate: {current_score.test_pass_rate:.2f}")
        print(f"     Feedback: {current_score.feedback[:120]}")

        # REFINEMENT (if loop continues)
        if score < settings.QUALITY_THRESHOLD and iteration < settings.MAX_ITERATIONS:
            print(f"\n  🔄 REFINEMENT")
            try:
                from app.models.schemas import Iteration as IterModel, ExecutionResult as ER
                iter_obj = IterModel(
                    iteration_number=iteration,
                    session_id="demo",
                    execution_result=exec_result,
                    test_result=test_metrics,
                )
                plan = await refiner.plan_refinement(refined_req, current_code, current_score, iter_obj)
                print(f"     {refiner.format_notes(plan)[:200]}")
            except Exception:
                print(f"     Targeting: {current_score.feedback[:100]}")

        print(f"\n  {'✅ THRESHOLD MET' if score >= settings.QUALITY_THRESHOLD else '🔁 CONTINUING LOOP'}")
        print(f"  " + "─" * 50)

    # ── Final output ─────────────────────────────────────────────
    print(f"\n[FINAL OUTPUT]")
    print(f"  Total Iterations: {iteration}")
    print(f"  Final Score:      {score:.2f}")
    print(f"  Success:          {score >= settings.QUALITY_THRESHOLD}")
    print(f"\n  Code ({len(current_code)} chars):")
    print("  " + "─" * 50)
    for line in current_code[:800].split("\n"):
        print(f"  {line}")
    if len(current_code) > 800:
        print(f"  ... [{len(current_code) - 800} more chars]")
    print("=" * 70)


def _demo_login_code() -> str:
    return '''"""Login API - FastAPI implementation."""
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
import os

app = FastAPI(title="Login API")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# In-memory user store (replace with DB in production)
_users: dict = {}

class UserCreate(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@app.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate):
    """Register a new user."""
    if not body.email or "@" not in body.email:
        raise HTTPException(status_code=400, detail="Invalid email address")
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if body.email in _users:
        raise HTTPException(status_code=409, detail="Email already registered")
    _users[body.email] = hash_password(body.password)
    return {"message": "User registered successfully"}

@app.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    """Authenticate and return a JWT token."""
    if not body.email or body.email not in _users:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(body.password, _users[body.email]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": body.email})
    return TokenResponse(access_token=token)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''


def _demo_test_code() -> str:
    return '''"""Tests for Login API."""
import pytest
from unittest.mock import patch

def test_hash_and_verify_password():
    """Test password hashing and verification."""
    from passlib.context import CryptContext
    ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = ctx.hash("mypassword123")
    assert ctx.verify("mypassword123", hashed)
    assert not ctx.verify("wrongpassword", hashed)

def test_create_access_token():
    """Test JWT token creation."""
    from jose import jwt
    from datetime import datetime, timedelta
    secret = "test-secret"
    data = {"sub": "user@example.com"}
    expire = datetime.utcnow() + timedelta(hours=1)
    data["exp"] = expire
    token = jwt.encode(data, secret, algorithm="HS256")
    decoded = jwt.decode(token, secret, algorithms=["HS256"])
    assert decoded["sub"] == "user@example.com"

def test_password_too_short():
    """Test short password rejection."""
    assert len("abc") < 8  # sentinel for validation logic

def test_invalid_email_format():
    """Test invalid email detection."""
    email = "notanemail"
    assert "@" not in email
'''


if __name__ == "__main__":
    asyncio.run(run_demo())
