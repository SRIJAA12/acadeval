from typing import Optional
from pydantic import BaseModel


class RubricCriteriaItem(BaseModel):
    criteriaId: str
    name: str
    weight: float
    isRequired: bool
    description: str


class RubricCreate(BaseModel):
    name: str
    department: str
    academicYear: Optional[str] = None
    criteria: list[RubricCriteriaItem]


class RubricOut(BaseModel):
    rubricId: str
    name: str
    department: str
    academicYear: Optional[str] = None
    version: int
    supersedesId: Optional[str] = None
    createdBy: str
    isApproved: bool
    criteria: list[RubricCriteriaItem]
    createdAt: str

    model_config = {"from_attributes": True}
