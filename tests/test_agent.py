"""
Integration tests for the ReAct Agent system.
Run with:  pytest tests/ -v
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def sample_requirement():
    return "Build a login API with email/password and JWT tokens"


@pytest.fixture
def mock_llm_response():
    """Generic LLM response for tests."""
    return '{"code": "def login(email, password): return True", "explanation": "test", "dependencies": []}'


# ─────────────────────────────────────────────────────────────
# Tool tests
# ─────────────────────────────────────────────────────────────

class TestRequirementClarificationTool:
    @pytest.mark.asyncio
    async def test_generate_questions_returns_list(self, sample_requirement):
        from app.tools.clarification_tool import RequirementClarificationTool
        tool = RequirementClarificationTool()

        with patch.object(tool._llm, 'complete', new_callable=AsyncMock) as mock_complete:
            mock_complete.return_value = '{"questions": ["What DB?", "Which auth method?", "REST or GraphQL?"]}'
            questions = await tool.generate_questions(sample_requirement)

        assert isinstance(questions, list)
        assert len(questions) >= 1

    @pytest.mark.asyncio
    async def test_refine_requirement_returns_dict(self, sample_requirement):
        from app.tools.clarification_tool import RequirementClarificationTool
        from app.models.schemas import ClarificationQA

        tool = RequirementClarificationTool()
        qa = [ClarificationQA(question="What DB?", answer="PostgreSQL")]

        with patch.object(tool._llm, 'complete', new_callable=AsyncMock) as mock_complete:
            mock_complete.return_value = '{"refined_requirement": "Build a login API with PostgreSQL", "key_features": [], "technical_constraints": [], "acceptance_criteria": []}'
            result = await tool.refine_requirement(sample_requirement, qa)

        assert "refined_requirement" in result

    @pytest.mark.asyncio
    async def test_generate_questions_handles_bad_json(self, sample_requirement):
        from app.tools.clarification_tool import RequirementClarificationTool
        tool = RequirementClarificationTool()

        with patch.object(tool._llm, 'complete', new_callable=AsyncMock) as mock_complete:
            mock_complete.return_value = "What auth method? What DB? Which framework?"
            questions = await tool.generate_questions(sample_requirement)

        # Should not raise; should return something
        assert isinstance(questions, list)


class TestCodeGeneratorTool:
    @pytest.mark.asyncio
    async def test_generate_returns_code(self, sample_requirement):
        from app.tools.code_generator_tool import CodeGeneratorTool
        tool = CodeGeneratorTool()

        mock_response = '{"code": "def login(): pass", "explanation": "stub", "dependencies": [], "entry_point": "login"}'
        with patch.object(tool._llm, 'complete', new_callable=AsyncMock) as mock_complete:
            mock_complete.return_value = mock_response
            result = await tool.generate(sample_requirement)

        assert "code" in result
        assert len(result["code"]) > 0

    @pytest.mark.asyncio
    async def test_refine_accepts_feedback(self, sample_requirement):
        from app.tools.code_generator_tool import CodeGeneratorTool
        tool = CodeGeneratorTool()

        mock_response = '{"code": "def login(): return True", "changes_made": ["Added return value"]}'
        with patch.object(tool._llm, 'complete', new_callable=AsyncMock) as mock_complete:
            mock_complete.return_value = mock_response
            result = await tool.refine(
                requirement=sample_requirement,
                previous_code="def login(): pass",
                execution_output="",
                test_output="1 failed",
                evaluation_feedback="Missing return value",
                iteration=2,
            )

        assert "code" in result

    def test_parse_code_response_extracts_markdown_block(self):
        from app.tools.code_generator_tool import CodeGeneratorTool
        tool = CodeGeneratorTool()
        raw = "Some text\n```python\ndef hello(): return 'world'\n```\nMore text"
        result = tool._parse_code_response(raw)
        assert "def hello" in result["code"]


class TestCodeExecutionTool:
    @pytest.mark.asyncio
    async def test_execute_simple_code(self):
        from app.tools.execution_tool import CodeExecutionTool
        tool = CodeExecutionTool()
        result = await tool.execute("print('hello world')")
        # Either Docker or subprocess should work
        assert "hello world" in result.stdout or result.exit_code == 0

    @pytest.mark.asyncio
    async def test_execute_captures_stderr(self):
        from app.tools.execution_tool import CodeExecutionTool
        tool = CodeExecutionTool()
        result = await tool.execute("import sys; sys.stderr.write('error msg\\n')")
        assert result.exit_code == 0  # stderr doesn't mean failure

    @pytest.mark.asyncio
    async def test_execute_syntax_error(self):
        from app.tools.execution_tool import CodeExecutionTool
        tool = CodeExecutionTool()
        result = await tool.execute("def bad syntax")
        assert result.exit_code != 0

    @pytest.mark.asyncio
    async def test_execute_has_duration(self):
        from app.tools.execution_tool import CodeExecutionTool
        tool = CodeExecutionTool()
        result = await tool.execute("x = 1 + 1")
        assert result.duration_ms >= 0


class TestTestRunnerTool:
    def test_parse_pytest_output_passed(self):
        from app.tools.test_runner_tool import TestRunnerTool
        tool = TestRunnerTool()
        output = "PASSED test_solution.py::test_login\n3 passed in 0.5s"
        result = tool._parse_pytest_output(output)
        assert result.passed == 3
        assert result.total == 3

    def test_parse_pytest_output_mixed(self):
        from app.tools.test_runner_tool import TestRunnerTool
        tool = TestRunnerTool()
        output = "2 passed, 1 failed in 0.8s"
        result = tool._parse_pytest_output(output)
        assert result.passed == 2
        assert result.failed == 1
        assert result.total == 3

    def test_format_summary(self):
        from app.tools.test_runner_tool import TestRunnerTool
        from app.models.schemas import TestResult
        tool = TestRunnerTool()
        tr = TestResult(total=5, passed=4, failed=1, errors=0)
        summary = tool.format_summary(tr)
        assert "4/5" in summary
        assert "80%" in summary


# ─────────────────────────────────────────────────────────────
# Evaluator tests
# ─────────────────────────────────────────────────────────────

class TestEvaluator:
    @pytest.mark.asyncio
    async def test_evaluate_returns_score(self, sample_requirement):
        from app.agents.evaluator import Evaluator
        from app.models.schemas import ExecutionResult, TestResult

        evaluator = Evaluator()
        exec_result = ExecutionResult(stdout="OK", stderr="", exit_code=0, duration_ms=100)
        test_result = TestResult(total=5, passed=4, failed=1)

        llm_response = '{"correctness": 0.8, "completeness": 0.7, "edge_cases": 0.6, "code_quality": 0.75, "feedback": "Good but missing validation"}'

        with patch.object(evaluator._llm, 'complete', new_callable=AsyncMock) as mock:
            mock.return_value = llm_response
            score = await evaluator.evaluate(
                requirement=sample_requirement,
                code="def login(): pass",
                execution_result=exec_result,
                test_result=test_result,
            )

        assert 0 <= score.overall <= 1
        assert score.test_pass_rate == pytest.approx(0.8, 0.01)

    @pytest.mark.asyncio
    async def test_evaluate_penalises_crash(self, sample_requirement):
        from app.agents.evaluator import Evaluator
        from app.models.schemas import ExecutionResult

        evaluator = Evaluator()
        exec_result = ExecutionResult(stdout="", stderr="SyntaxError", exit_code=1, duration_ms=50)

        llm_response = '{"correctness": 0.9, "completeness": 0.8, "edge_cases": 0.7, "code_quality": 0.8, "feedback": "n/a"}'

        with patch.object(evaluator._llm, 'complete', new_callable=AsyncMock) as mock:
            mock.return_value = llm_response
            score = await evaluator.evaluate(
                requirement=sample_requirement,
                code="def bad(:",
                execution_result=exec_result,
            )

        # Correctness must be clamped to <= 0.3 on crash
        assert score.correctness <= 0.3


# ─────────────────────────────────────────────────────────────
# Planner tests
# ─────────────────────────────────────────────────────────────

class TestPlanner:
    @pytest.mark.asyncio
    async def test_think_returns_dict(self, sample_requirement):
        from app.agents.planner import Planner

        planner = Planner()
        llm_response = '{"summary": "Start", "identified_problems": [], "next_action": "Generate code", "rationale": "First iter", "focus_areas": []}'

        with patch.object(planner._llm, 'complete', new_callable=AsyncMock) as mock:
            mock.return_value = llm_response
            thought = await planner.think(
                requirement=sample_requirement,
                iteration_number=1,
            )

        assert "next_action" in thought
        assert "summary" in thought

    def test_format_thought(self):
        from app.agents.planner import Planner
        planner = Planner()
        thought = {
            "summary": "Working on login",
            "identified_problems": ["no hashing"],
            "next_action": "Add bcrypt",
            "rationale": "Security",
            "focus_areas": ["security"],
        }
        text = planner.format_thought(thought)
        assert "bcrypt" in text
        assert "Security" in text


# ─────────────────────────────────────────────────────────────
# Schema tests
# ─────────────────────────────────────────────────────────────

class TestSchemas:
    def test_session_defaults(self):
        from app.models.schemas import Session
        s = Session(session_id="abc", raw_requirement="Build something")
        assert s.phase.value == "clarification"
        assert s.success is False
        assert s.total_iterations == 0

    def test_evaluation_score(self):
        from app.models.schemas import EvaluationScore
        score = EvaluationScore(
            correctness=0.9, completeness=0.8,
            edge_cases=0.7, code_quality=0.85,
            test_pass_rate=1.0, overall=0.85,
        )
        assert score.overall == 0.85

    def test_iteration_defaults(self):
        from app.models.schemas import Iteration
        it = Iteration(iteration_number=1, session_id="abc")
        assert it.steps == []
        assert it.generated_code == ""
