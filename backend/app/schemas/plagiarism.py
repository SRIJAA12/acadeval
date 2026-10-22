from typing import Optional
from pydantic import BaseModel


class PlagiarismMatchOut(BaseModel):
    matchId: str
    matchType: str  # "text" | "code"
    sourceProjectId: Optional[str] = None
    sourceLabel: str
    candidatePassage: str
    candidateLocation: Optional[str] = None
    sourcePassage: str
    sourceLocation: Optional[str] = None
    score: float
    reviewStatus: str
    reviewedByName: Optional[str] = None
    reviewedAt: Optional[str] = None
    reviewerComment: Optional[str] = None
    createdAt: str

    model_config = {"from_attributes": True}


class PlagiarismReportOut(BaseModel):
    projectId: str
    textMax: float
    codeMax: float
    textMatchCount: int
    codeMatchCount: int
    codeFetchError: Optional[str] = None
    matches: list[PlagiarismMatchOut]
    summaryText: str


class ReviewDecisionRequest(BaseModel):
    reviewStatus: str  # "confirmed" | "acceptable_overlap" | "uncertain" | "no_issue"
    reviewerComment: Optional[str] = None
