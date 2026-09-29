from fastapi import APIRouter
from sqlalchemy import func, select
from datetime import datetime, timezone

from app.dependencies import DB, CurrentFaculty, CurrentHOD
from app.models.project import Project, PipelineStatus
from app.models.evaluation import EvaluationReport, HistoricalScore, ScoreOverrideHistory
from app.models.user import User, UserRole
from app.schemas.dashboard import FacultyDashboardStats, HODDeptStats, SemesterBenchmark, ActivityItem

router = APIRouter(tags=["Dashboard"])


@router.get("/dashboard/faculty", response_model=FacultyDashboardStats)
def faculty_dashboard(current_user: CurrentFaculty, db: DB):
    from sqlalchemy.orm import joinedload

    # Phase 1: Show all department projects to Guide and Reviewer
    projects = db.query(Project).all()
    total = len(projects)
    pending = sum(1 for p in projects if p.pipeline_status == PipelineStatus.awaiting_review)
    flagged = sum(1 for p in projects if p.evaluation and p.evaluation.is_duplicate)

    scores = [p.evaluation.overall_score for p in projects if p.evaluation and p.evaluation.overall_score]
    avg = round(sum(scores) / len(scores), 1) if scores else 0.0

    # Recent activity (last 10 events by submitted_on)
    recent = sorted(projects, key=lambda p: p.submitted_on, reverse=True)[:10]
    activity = [
        ActivityItem(
            id=str(p.id),
            type="submitted" if p.pipeline_status == PipelineStatus.uploaded else
                 "reviewed" if p.pipeline_status == PipelineStatus.reviewed else "submitted",
            studentName=p.student.name,
            projectTitle=p.title,
            timestamp=p.submitted_on.isoformat(),
        )
        for p in recent
    ]

    return FacultyDashboardStats(
        totalSubmissions=total,
        pendingReview=pending,
        flaggedDuplicates=flagged,
        avgScoreThisSemester=avg,
        recentActivity=activity,
    )


@router.get("/dashboard/hod", response_model=HODDeptStats)
def hod_dashboard(current_user: CurrentHOD, db: DB):
    total_students = db.query(func.count(User.id)).filter(User.role == UserRole.student).scalar() or 0
    total_faculty = db.query(func.count(User.id)).filter(User.role.in_([UserRole.guide, UserRole.reviewer])).scalar() or 0
    total_projects = db.query(func.count(Project.id)).scalar() or 0
    reviewed_count = db.query(func.count(Project.id)).filter(Project.pipeline_status == PipelineStatus.reviewed).scalar() or 0

    # Avg score
    avg_result = db.query(func.avg(EvaluationReport.overall_score)).scalar()
    avg_score = round(float(avg_result), 1) if avg_result else 0.0

    # Domain distribution
    domain_rows = db.query(Project.domain, func.count(Project.id)).group_by(Project.domain).all()
    domain_dist = {row[0]: row[1] for row in domain_rows if row[0]}

    # Real trend data from project submissions
    try:
        monthly_rows = (
            db.query(
                func.to_char(Project.submitted_on, 'Mon').label("month"),
                func.date_trunc('month', Project.submitted_on).label("month_date"),
                func.avg(EvaluationReport.overall_score).label("avg_score")
            )
            .join(EvaluationReport, EvaluationReport.project_id == Project.id)
            .filter(EvaluationReport.overall_score > 0)
            .group_by(func.to_char(Project.submitted_on, 'Mon'), func.date_trunc('month', Project.submitted_on))
            .order_by(func.date_trunc('month', Project.submitted_on))
            .all()
        )
        if monthly_rows:
            trend_data = [
                {"month": row.month, "avgScore": round(float(row.avg_score), 1)}
                for row in monthly_rows
            ]
        else:
            # Fallback to historical_scores if available
            hist_rows = (
                db.query(
                    HistoricalScore.semester,
                    func.avg(HistoricalScore.score).label("avg_score")
                )
                .filter(HistoricalScore.dimension == "overall")
                .group_by(HistoricalScore.semester)
                .all()
            )
            trend_data = [
                {"month": row.semester, "avgScore": round(float(row.avg_score), 1)}
                for row in hist_rows
            ]
    except Exception:
        trend_data = []

    # Recent score overrides across all projects for audit oversight
    try:
        overrides = (
            db.query(ScoreOverrideHistory)
            .order_by(ScoreOverrideHistory.timestamp.desc())
            .limit(10)
            .all()
        )
        recent_overrides = [
            {
                "id": str(ov.id),
                "projectId": str(ov.project_id),
                "dimension": ov.dimension,
                "oldValue": ov.old_value,
                "newValue": ov.new_value,
                "changedByName": ov.changed_by_name,
                "comment": ov.comment,
                "timestamp": ov.timestamp.isoformat() if ov.timestamp else "",
            }
            for ov in overrides
        ]
    except Exception:
        recent_overrides = []

    return HODDeptStats(
        totalStudents=total_students,
        totalFaculty=total_faculty,
        totalSubmissions=total_projects,
        reviewedCount=reviewed_count,
        avgScore=avg_score,
        domainDistribution=domain_dist,
        trendData=trend_data,
        recentOverrides=recent_overrides,
    )


@router.get("/benchmarks", response_model=list[SemesterBenchmark])
def get_benchmarks(current_user: CurrentFaculty, db: DB):
    """Aggregate dimension averages per semester from historical_scores."""
    rows = (
        db.query(
            HistoricalScore.semester,
            HistoricalScore.year,
            HistoricalScore.dimension,
            func.avg(HistoricalScore.score).label("avg_score"),
            func.max(HistoricalScore.score).label("max_score"),
            func.count(HistoricalScore.id).label("count"),
        )
        .group_by(HistoricalScore.semester, HistoricalScore.year, HistoricalScore.dimension)
        .all()
    )

    # Pivot into SemesterBenchmark per (semester, year)
    sem_map: dict[tuple, dict] = {}
    for row in rows:
        key = (row.semester, row.year)
        if key not in sem_map:
            sem_map[key] = {
                "semester": row.semester, "year": row.year,
                "avgNovelty": 0, "avgFeasibility": 0, "avgCompleteness": 0,
                "avgTechnicalDepth": 0, "avgClarity": 0, "avgOverall": 0,
                "topScore": 0, "totalProjects": 0,
            }
        dim_col = {
            "novelty": "avgNovelty", "feasibility": "avgFeasibility",
            "completeness": "avgCompleteness", "technicalDepth": "avgTechnicalDepth",
            "clarity": "avgClarity", "overall": "avgOverall",
        }.get(row.dimension)
        if dim_col:
            sem_map[key][dim_col] = round(float(row.avg_score), 1)
        sem_map[key]["topScore"] = max(sem_map[key]["topScore"], float(row.max_score))
        sem_map[key]["totalProjects"] = row.count

    return [SemesterBenchmark(**v) for v in sorted(sem_map.values(), key=lambda x: (x["year"], x["semester"]))]
