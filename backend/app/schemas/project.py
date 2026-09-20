import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.project import SubmissionType, PipelineStatus


class ProjectSummary(BaseModel):
    """Matches frontend ProjectSummary interface exactly."""
    projectId: str
    studentName: str
    rollNo: str
    title: str
    submissionType: SubmissionType
    domain: str
    submittedOn: str   # ISO date string
    pipelineStatus: PipelineStatus
    overallScore: Optional[float]

    model_config = {"from_attributes": True}


class ProjectStatusResponse(BaseModel):
    status: str


class UploadResponse(BaseModel):
    projectId: str


class BatchUploadResponse(BaseModel):
    batchId: str
    totalFiles: int
    projectIds: list[str]


class BatchJobStatusResponse(BaseModel):
    batchId: str
    totalFiles: int
    processed: int
    failed: int
    status: str
    startedAt: str
    completedAt: Optional[str] = None
    projects: list[ProjectSummary] = []
