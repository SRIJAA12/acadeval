import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Rubric(Base):
    __tablename__ = "rubrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    academic_year: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Bumped when an already-approved rubric is edited: editing an approved
    # rubric creates a new row (version + 1, is_approved=False) instead of
    # mutating it, so past evaluations keep meaning under the version they
    # were scored with.
    version: Mapped[int] = mapped_column(default=1)
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rubrics.id"), nullable=True
    )

    # Array of {criteriaId, name, weight, isRequired, description}
    criteria: Mapped[list] = mapped_column(JSONB, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    creator: Mapped["User"] = relationship("User", back_populates="rubrics")
