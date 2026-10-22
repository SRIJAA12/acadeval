from typing import Optional
from pydantic import BaseModel


# ── Roster allocation (guide/team assignment via Excel) ────────────────────────

class RosterRowResult(BaseModel):
    rowNumber: int
    rollNo: str
    status: str  # "applied" | "pending" | "error"
    message: str


class RosterUploadResponse(BaseModel):
    totalRows: int
    applied: int
    pending: int
    errors: int
    results: list[RosterRowResult]


class RosterAllocationOut(BaseModel):
    allocationId: str
    rollNo: str
    studentEmail: Optional[str] = None
    teamId: Optional[str] = None
    guideName: Optional[str] = None
    domain: Optional[str] = None
    isApplied: bool
    error: Optional[str] = None
    createdAt: str

    model_config = {"from_attributes": True}


# ── Reviewer slot accounts ──────────────────────────────────────────────────────

class ReviewerSlotCreate(BaseModel):
    name: str


class ReviewerSlotOut(BaseModel):
    slotId: str
    name: str
    email: str
    isActive: bool
    createdAt: str

    model_config = {"from_attributes": True}


# ── Review rounds & schedule ────────────────────────────────────────────────────

class ReviewRoundCreate(BaseModel):
    name: str
    description: Optional[str] = None
    scheduledDate: Optional[str] = None  # ISO date/datetime
    isFinal: bool = False


class ReviewRoundOut(BaseModel):
    roundId: str
    name: str
    description: Optional[str] = None
    scheduledDate: Optional[str] = None
    isFinal: bool
    createdAt: str
    assignmentCount: int = 0
    publishedCount: int = 0

    model_config = {"from_attributes": True}


class ReviewSlotAssignmentCreate(BaseModel):
    projectIds: Optional[list[str]] = None
    teamId: Optional[str] = None
    reviewerSlotId: str
    staffEmail: str
    scheduledAt: Optional[str] = None


class ReviewSlotAssignmentOut(BaseModel):
    assignmentId: str
    roundId: str
    projectId: str
    projectTitle: str
    studentName: str
    reviewerSlotId: str
    reviewerSlotName: str
    staffEmail: str
    scheduledAt: Optional[str] = None
    credentialEmailSent: bool
    createdAt: str

    model_config = {"from_attributes": True}


# ── Per-round evaluation (the reviewer's score for that round) ─────────────────

class RoundEvaluationUpdateRequest(BaseModel):
    novelty: Optional[float] = None
    feasibility: Optional[float] = None
    completeness: Optional[float] = None
    technicalDepth: Optional[float] = None
    clarity: Optional[float] = None
    similarityRisk: Optional[float] = None
    publicationPotential: Optional[float] = None
    comment: str = ""


class RoundEvaluationOut(BaseModel):
    evaluationId: str
    roundId: str
    roundName: str
    isFinalRound: bool
    projectId: str
    reviewerSlotName: str
    novelty: Optional[float] = None
    feasibility: Optional[float] = None
    completeness: Optional[float] = None
    technicalDepth: Optional[float] = None
    clarity: Optional[float] = None
    similarityRisk: Optional[float] = None
    publicationPotential: Optional[float] = None
    overallScore: Optional[float] = None
    grade: Optional[str] = None
    comment: str
    isPublished: bool
    publishedAt: Optional[str] = None
    updatedAt: str

    model_config = {"from_attributes": True}


class CoordinatorOverview(BaseModel):
    totalProjects: int
    unallocatedProjects: int
    pendingRosterRows: int
    reviewerSlotCount: int
    activeRoundCount: int
    rubricsPendingApproval: int
