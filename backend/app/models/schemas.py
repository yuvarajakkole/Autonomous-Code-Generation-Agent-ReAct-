"""
Pydantic models for agent state, iterations, and sessions.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────

class AgentPhase(str, Enum):
    CLARIFICATION = "clarification"
    PLANNING      = "planning"
    GENERATION    = "generation"
    EXECUTION     = "execution"
    EVALUATION    = "evaluation"
    REFINEMENT    = "refinement"
    COMPLETED     = "completed"
    FAILED        = "failed"


class StepType(str, Enum):
    THOUGHT     = "thought"
    ACTION      = "action"
    OBSERVATION = "observation"
    EVALUATION  = "evaluation"
    REFINEMENT  = "refinement"
    SYSTEM      = "system"


# ─────────────────────────────────────────────────────────────
# ReAct Step (one atomic unit inside an iteration)
# ─────────────────────────────────────────────────────────────

class ReActStep(BaseModel):
    step_type:   StepType
    content:     str
    metadata:    Dict[str, Any] = Field(default_factory=dict)
    timestamp:   datetime = Field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────────────────────
# Iteration (one full Thought→Action→Observe→Evaluate→Refine cycle)
# ─────────────────────────────────────────────────────────────

class EvaluationScore(BaseModel):
    correctness:    float = 0.0   # 0-1
    completeness:   float = 0.0
    edge_cases:     float = 0.0
    code_quality:   float = 0.0
    test_pass_rate: float = 0.0
    overall:        float = 0.0
    feedback:       str   = ""


class ExecutionResult(BaseModel):
    stdout:     str  = ""
    stderr:     str  = ""
    exit_code:  int  = -1
    timed_out:  bool = False
    duration_ms: int = 0


class TestResult(BaseModel):
    total:   int = 0
    passed:  int = 0
    failed:  int = 0
    errors:  int = 0
    details: List[str] = Field(default_factory=list)


class Iteration(BaseModel):
    iteration_number: int
    session_id:       str
    steps:            List[ReActStep]   = Field(default_factory=list)
    generated_code:   str               = ""
    test_code:        str               = ""
    execution_result: Optional[ExecutionResult] = None
    test_result:      Optional[TestResult]      = None
    score:            Optional[EvaluationScore] = None
    refinement_notes: str               = ""
    created_at:       datetime          = Field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────────────────────
# Session (top-level, spans all iterations)
# ─────────────────────────────────────────────────────────────

class ClarificationQA(BaseModel):
    question: str
    answer:   str


class Session(BaseModel):
    session_id:       str
    raw_requirement:  str
    clarifications:   List[ClarificationQA] = Field(default_factory=list)
    refined_requirement: str = ""
    iterations:       List[Iteration]       = Field(default_factory=list)
    final_code:       str                   = ""
    final_score:      Optional[EvaluationScore] = None
    phase:            AgentPhase            = AgentPhase.CLARIFICATION
    total_iterations: int                   = 0
    success:          bool                  = False
    created_at:       datetime              = Field(default_factory=datetime.utcnow)
    updated_at:       datetime              = Field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────────────────────
# API request / response shapes
# ─────────────────────────────────────────────────────────────

class StartAgentRequest(BaseModel):
    requirement: str = Field(
        ...,
        min_length=10,
        description="User's vague or detailed software requirement",
    )
    clarification_answers: Optional[Dict[str, str]] = None


class ClarificationResponse(BaseModel):
    session_id: str
    questions:  List[str]


class AgentStatusResponse(BaseModel):
    session_id:  str
    phase:       AgentPhase
    iterations:  int
    final_score: Optional[float]
    success:     bool
    final_code:  str


# ─────────────────────────────────────────────────────────────
# SSE event envelope
# ─────────────────────────────────────────────────────────────

class SSEEvent(BaseModel):
    event:   str
    data:    Dict[str, Any]
    session_id: str
    timestamp:  datetime = Field(default_factory=datetime.utcnow)
