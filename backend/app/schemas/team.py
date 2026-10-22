from typing import Optional
from pydantic import BaseModel


class TeamMemberOut(BaseModel):
    studentId: str
    name: str
    rollNo: Optional[str] = None
    role: str  # "member" | "lead"


class TeamOut(BaseModel):
    teamId: str
    teamCode: str
    name: Optional[str] = None
    members: list[TeamMemberOut]
    createdAt: str

    model_config = {"from_attributes": True}


class TeamMessageCreate(BaseModel):
    body: str


class TeamMessageOut(BaseModel):
    messageId: str
    authorId: str
    authorName: str
    body: str
    mentionedUserIds: list[str] = []
    createdAt: str

    model_config = {"from_attributes": True}


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    assigneeId: Optional[str] = None  # defaults to self when omitted
    projectId: Optional[str] = None
    dueDate: Optional[str] = None


class TaskUpdateRequest(BaseModel):
    status: str  # "pending" | "done"


class TaskOut(BaseModel):
    taskId: str
    projectId: Optional[str] = None
    projectTitle: Optional[str] = None
    teamId: Optional[str] = None
    teamCode: Optional[str] = None
    assigneeId: str
    assigneeName: str
    createdByName: Optional[str] = None
    title: str
    description: Optional[str] = None
    status: str
    source: str
    dueDate: Optional[str] = None
    createdAt: str
    completedAt: Optional[str] = None

    model_config = {"from_attributes": True}
