"""
Intelligent Viva Assessment Engine — Pydantic Schemas
=======================================================
All request/response shapes for the viva module.  The schema hierarchy
mirrors the workflow:

  Session start  →  Question served  →  Answer submitted
       →  Evaluation returned  →  Next question (adaptive)
       →  Session complete  →  Final viva report

KCS = Knowledge Coverage Score — the novel metric defined in this framework:
  KCS = (distinct concept nodes answered / total concept nodes in project graph)
"""

from __future__ import annotations

from typing import Optional, Literal
from pydantic import BaseModel, Field


# ── Difficulty levels ─────────────────────────────────────────────────────────

DifficultyLevel = Literal["Easy", "Medium", "Hard", "Research"]

DIFFICULTY_ORDER: dict[DifficultyLevel, int] = {
    "Easy": 1, "Medium": 2, "Hard": 3, "Research": 4
}


# ── Question bank entry ───────────────────────────────────────────────────────

class VivaQuestion(BaseModel):
    questionId: str
    text: str
    category: Literal[
        "Conceptual", "Technical", "Design",
        "Research", "Scenario", "Limitations", "Basic"
    ]
    difficulty: DifficultyLevel
    targetConcept: str = ""          # which knowledge-graph node this tests
    referenceAnswer: str = ""        # used for semantic evaluation (not shown to student)
    expectedKeywords: list[str] = [] # fallback keyword hints for evaluation


# ── Session management ────────────────────────────────────────────────────────

class StartVivaRequest(BaseModel):
    projectId: str
    startDifficulty: DifficultyLevel = "Easy"


class StartVivaResponse(BaseModel):
    sessionId: str
    projectId: str
    projectTitle: str
    totalConcepts: int           # how many concept nodes are in the project graph
    firstQuestion: VivaQuestion
    message: str = "Viva session started. Good luck!"


# ── Answer evaluation ─────────────────────────────────────────────────────────

class VivaAnswerSubmit(BaseModel):
    sessionId: str
    questionId: str
    answer: str = Field(..., min_length=1, max_length=5000)


class AnswerEvaluation(BaseModel):
    """Fine-grained evaluation dimensions for a single answer."""
    correctness: float = Field(..., ge=0.0, le=1.0,  description="Semantic correctness 0–1")
    completeness: float = Field(..., ge=0.0, le=1.0, description="Coverage of expected key points")
    technicalDepth: float = Field(..., ge=0.0, le=1.0, description="Use of technical vocabulary")
    confidence: float = Field(..., ge=0.0, le=1.0,  description="Derived from answer length/detail")
    overallScore: float = Field(..., ge=0.0, le=5.0, description="Composite 0–5")


class VivaAnswerResult(BaseModel):
    questionId: str
    score: float                     # 0–5 composite
    maxScore: float = 5.0
    evaluation: AnswerEvaluation
    feedback: str                    # human-readable feedback sentence
    strongPoints: list[str] = []     # what the student got right
    weakPoints: list[str] = []       # what was missing
    conceptCovered: str = ""         # which graph node was addressed
    # Adaptive next question
    nextQuestion: Optional[VivaQuestion] = None
    sessionComplete: bool = False
    # Live KCS after this answer
    kcsAfterAnswer: float = 0.0      # 0–100 %


# ── Knowledge Gap ─────────────────────────────────────────────────────────────

class ConceptGap(BaseModel):
    concept: str
    category: str
    difficulty: DifficultyLevel
    questionsAsked: int
    averageScore: float
    gapSeverity: Literal["Critical", "Moderate", "Minor"]


# ── Final viva report ─────────────────────────────────────────────────────────

class VivaReport(BaseModel):
    sessionId: str
    projectId: str
    projectTitle: str

    # ── Scores ────────────────────────────────────────────────────────────────
    overallScore: float              # 0–100
    kcs: float                       # Knowledge Coverage Score 0–100
    difficultyReached: DifficultyLevel
    totalQuestionsAnswered: int
    totalConceptsInProject: int
    conceptsCovered: int

    # ── Dimensional breakdown ─────────────────────────────────────────────────
    averageCorrectness: float
    averageCompleteness: float
    averageDepth: float
    averageConfidence: float

    # ── Categories ────────────────────────────────────────────────────────────
    categoryScores: dict[str, float]        # e.g. {"Technical": 3.8, "Design": 2.5}
    difficultyProgression: list[str]        # sequence of difficulties asked

    # ── Gap analysis ─────────────────────────────────────────────────────────
    knowledgeGaps: list[ConceptGap]
    strongAreas: list[str]

    # ── Learning recommendations ──────────────────────────────────────────────
    learningRecommendations: list[str]

    # ── Verdict ───────────────────────────────────────────────────────────────
    grade: Literal["Distinction", "Merit", "Pass", "Needs Improvement"]
    summaryStatement: str


# ── Session status (polling endpoint) ────────────────────────────────────────

class VivaSessionStatus(BaseModel):
    sessionId: str
    projectId: str
    isComplete: bool
    currentDifficulty: DifficultyLevel
    questionsAnswered: int
    currentKcs: float
    progressPct: float               # 0–100 based on concept coverage target


class VivaHistoryItem(BaseModel):
    sessionId: str
    projectId: str
    projectTitle: str
    isComplete: bool
    totalScore: Optional[float]
    kcs: Optional[float]
    questionsAnswered: int
    createdAt: str
