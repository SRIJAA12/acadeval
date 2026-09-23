from pydantic import BaseModel


class ActivityItem(BaseModel):
    id: str
    type: str
    studentName: str
    projectTitle: str
    timestamp: str
    details: str = ""


class FacultyDashboardStats(BaseModel):
    totalSubmissions: int
    pendingReview: int
    flaggedDuplicates: int
    avgScoreThisSemester: float
    recentActivity: list[ActivityItem]


class HODDeptStats(BaseModel):
    totalStudents: int
    totalFaculty: int
    totalSubmissions: int
    reviewedCount: int
    avgScore: float
    domainDistribution: dict[str, int]
    trendData: list[dict]
    recentOverrides: list[dict] = []


class SemesterBenchmark(BaseModel):
    semester: str
    year: int
    avgNovelty: float
    avgFeasibility: float
    avgCompleteness: float
    avgTechnicalDepth: float
    avgClarity: float
    avgOverall: float
    topScore: float
    totalProjects: int
