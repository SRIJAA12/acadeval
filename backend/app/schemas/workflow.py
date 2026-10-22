from typing import Optional
from pydantic import BaseModel


class MilestoneOut(BaseModel):
    milestoneId: str
    orderIndex: int
    title: str
    description: str
    status: str
    studentSubmission: Optional[str] = None
    guideComment: Optional[str] = None
    submittedAt: Optional[str] = None
    reviewedAt: Optional[str] = None

    model_config = {"from_attributes": True}


class MilestoneSubmitRequest(BaseModel):
    text: str


class MilestoneReviewRequest(BaseModel):
    approve: bool
    comment: Optional[str] = None


class DiscussionMessageOut(BaseModel):
    messageId: str
    authorId: str
    authorName: str
    authorRole: str
    body: str
    createdAt: str
    unread: bool = False

    model_config = {"from_attributes": True}


class DiscussionPostRequest(BaseModel):
    body: str


class NotificationOut(BaseModel):
    notificationId: str
    type: str
    title: str
    body: str
    link: Optional[str] = None
    isRead: bool
    createdAt: str

    model_config = {"from_attributes": True}


class ProgressUpdateOut(BaseModel):
    updateId: str
    authorId: str
    authorName: str
    content: str
    attachmentFilename: Optional[str] = None
    githubUrl: Optional[str] = None
    createdAt: str

    model_config = {"from_attributes": True}


class GuideFeedbackOut(BaseModel):
    guideId: str
    guideName: str
    overallScore: float
    comment: str
    updatedAt: str

    model_config = {"from_attributes": True}


class GuideFeedbackUpdateRequest(BaseModel):
    overallScore: float
    comment: str = ""


class AuditLogOut(BaseModel):
    auditLogId: str
    actorName: str
    actorRole: str
    action: str
    entityType: str
    entityId: str
    details: dict
    createdAt: str

    model_config = {"from_attributes": True}
