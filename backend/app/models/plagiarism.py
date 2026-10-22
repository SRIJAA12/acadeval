"""Real plagiarism evidence: text TF-IDF/cosine passage matches against other
submitted projects, and code k-gram/winnowing fingerprint matches against
linked GitHub repos. See app/services/plagiarism_checker.py and
app/services/github_code_fetcher.py. Deliberately separate from the novelty
engine's topic-similarity corpus matching (app/services/corpus_matcher.py) —
similarity is not the same as plagiarism."""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Enum, Float, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MatchType(str, enum.Enum):
    text = "text"
    code = "code"


class ReviewStatus(str, enum.Enum):
    unreviewed = "unreviewed"
    confirmed = "confirmed"
    acceptable_overlap = "acceptable_overlap"
    uncertain = "uncertain"
    no_issue = "no_issue"


class PlagiarismMatch(Base):
    """One piece of evidence: a candidate passage/code span and the source
    passage/file it matched, with the raw detector score and a human review
    decision kept separate from the automated flag (see app/routers/plagiarism.py)."""
    __tablename__ = "plagiarism_matches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    match_type: Mapped[MatchType] = mapped_column(Enum(MatchType), nullable=False)

    source_project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    source_label: Mapped[str] = mapped_column(String(500), nullable=False)

    candidate_passage: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_location: Mapped[str | None] = mapped_column(String(300), nullable=True)
    source_passage: Mapped[str] = mapped_column(Text, nullable=False)
    source_location: Mapped[str | None] = mapped_column(String(300), nullable=True)

    score: Mapped[float] = mapped_column(Float, nullable=False)

    review_status: Mapped[ReviewStatus] = mapped_column(Enum(ReviewStatus), nullable=False, default=ReviewStatus.unreviewed)
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewer_comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class CodeFingerprint(Base):
    """Cached winnowed k-gram fingerprint set for one project's linked GitHub
    repo, so later submissions can compare against it without refetching."""
    __tablename__ = "code_fingerprints"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, unique=True)
    repo_owner: Mapped[str | None] = mapped_column(String(200), nullable=True)
    repo_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    branch: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    fingerprints: Mapped[list] = mapped_column(JSONB, default=list)
    fetch_error: Mapped[str | None] = mapped_column(Text, nullable=True)
