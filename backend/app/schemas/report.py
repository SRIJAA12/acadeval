from typing import Optional, Any
from pydantic import BaseModel, Field
from app.models.project import SubmissionType, PipelineStatus


class DimensionScores(BaseModel):
    novelty: Optional[float]
    feasibility: Optional[float]
    completeness: Optional[float]      # null for abstract-only
    technicalDepth: Optional[float]
    clarity: Optional[float]
    similarityRisk: Optional[float]
    publicationPotential: Optional[float]


class SimilarityInfo(BaseModel):
    internalScore: float
    externalScore: float
    isDuplicate: bool


class WritingQuality(BaseModel):
    readability: float
    passiveVoiceCount: int
    toneFlags: list[str]


class CitationInfo(BaseModel):
    ieeeCompliancePercent: float
    missingReferences: list[str]


class ImprovementWeek(BaseModel):
    week: int
    focus: str
    actions: list[str]


class PublicEvaluationReport(BaseModel):
    """Matches frontend PublicEvaluationReport — safe for students."""
    projectId: str
    title: str
    domain: str
    submissionType: SubmissionType
    pipelineStatus: PipelineStatus
    isPreliminary: bool
    overallScore: float
    grade: str
    dimensionScores: DimensionScores
    missingSections: list[str]
    similarity: SimilarityInfo
    feasibilityRating: str
    noveltyVerdict: str
    writingQuality: Optional[WritingQuality]
    citations: Optional[CitationInfo]
    strengths: list[str]
    weaknesses: list[str]
    improvementRoadmap: list[ImprovementWeek]
    badges: list[str]
    percentileRanks: dict[str, float]

    model_config = {"from_attributes": True}


class FacultyNote(BaseModel):
    author: str
    role: str
    text: str
    timestamp: str


class ExplainabilityAnnotation(BaseModel):
    sentence: str
    weight: float
    reason: str


class ScoreOverrideEntry(BaseModel):
    dimension: str
    oldValue: float
    newValue: float
    by: str
    comment: str
    timestamp: str


class InternalEvaluationReport(PublicEvaluationReport):
    """Extends public report — never returned on student routes."""
    facultyNotes: list[FacultyNote]
    explainabilityAnnotations: list[ExplainabilityAnnotation]
    flaggingReasons: list[str]
    assignedGuide: str
    assignedReviewer: Optional[str]
    scoreOverrideHistory: list[ScoreOverrideEntry]


class ScoreOverrideRequest(BaseModel):
    dimension: str
    newValue: float
    comment: str


class AddNoteRequest(BaseModel):
    text: str

class FacultyReviewRequest(BaseModel):
    faculty_score: float = Field(ge=1, le=10)
    override_reason: str | None = None
    is_confirmed: bool = True