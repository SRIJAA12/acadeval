// ─── Core Domain Types ───────────────────────────────────────────────────────

export type SubmissionType = 'document' | 'video' | 'abstract';
export type PipelineStatus = 'uploaded' | 'ai_processing' | 'awaiting_review' | 'reviewed';
export type UserRole = 'student' | 'guide' | 'reviewer' | 'hod';
export type FeasibilityRating = 'High' | 'Medium' | 'Low';
export type NoveltyVerdict = 'Common' | 'Somewhat Novel' | 'Novel';

// ─── Auth ────────────────────────────────────────────────────────────────────

export interface JwtPayload {
  sub: string;
  role: UserRole;
  name: string;
  email: string;
  exp: number;
  iat: number;
}

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: UserRole;
}

export interface LoginRequest {
  email: string;
  password: string;
  role: UserRole;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

// ─── Project Summary ─────────────────────────────────────────────────────────

export interface ProjectSummary {
  projectId: string;
  studentName: string;
  rollNo: string;
  title: string;
  submissionType: SubmissionType;
  domain: string;
  submittedOn: string;
  pipelineStatus: PipelineStatus;
  overallScore: number | null;
}

// ─── Dimension Scores ────────────────────────────────────────────────────────

export interface DimensionScores {
  novelty: number | null;
  feasibility: number | null;
  completeness: number | null; // null for abstract-only
  technicalDepth: number | null;
  clarity: number | null;
  similarityRisk: number | null;
  publicationPotential: number | null;
}

// ─── Public Report (Student-safe) ────────────────────────────────────────────

export interface PublicEvaluationReport {
  projectId: string;
  title: string;
  domain: string;
  submissionType: SubmissionType;
  pipelineStatus: PipelineStatus;
  isPreliminary: boolean;
  overallScore: number;
  grade: string;
  dimensionScores: DimensionScores;
  missingSections: string[];
  similarity: {
    internalScore: number;
    externalScore: number;
    isDuplicate: boolean;
  };
  feasibilityRating: FeasibilityRating;
  noveltyVerdict: NoveltyVerdict;
  writingQuality: {
    readability: number | null;
    clarityScore: number | null;
    passiveVoiceCount: number;
    wordCount: number;
    toneFlags: string[];
    methodVersion: string | null;
  } | null;
  citations: {
    verifiedPercent: number;
    recentPercent: number;
    referenceCount: number;
    issues: string[];
    status: string;
    methodVersion: string | null;
  } | null;
  strengths: string[];
  weaknesses: string[];
  improvementRoadmap: {
    week: number;
    focus: string;
    actions: string[];
  }[];
  badges: string[];
  percentileRanks: Record<string, number>;
  assessmentEvidence: {
    evidence_quality: string;
    feasibility: AssessmentDimensionEvidence;
    completeness: {
      score: number | null;
      present_sections: string[];
      missing_sections: string[];
      reason?: string;
    };
    technical_depth: AssessmentDimensionEvidence;
    gaps: string[];
  } | null;
  evaluationMethodVersion: string | null;
}

export interface AssessmentCriterionEvidence {
  score: number;
  evidence: string[];
  gaps: string[];
}

export interface AssessmentDimensionEvidence {
  score: number;
  criteria: Record<string, AssessmentCriterionEvidence>;
}

// ─── Internal Report (Faculty/HOD only — NEVER fetched on student routes) ────

export interface FacultyNote {
  author: string;
  role: UserRole;
  text: string;
  timestamp: string;
}

export interface ExplainabilityAnnotation {
  sentence: string;
  weight: number;
  reason: string;
}

export interface ScoreOverrideEntry {
  dimension: string;
  oldValue: number;
  newValue: number;
  by: string;
  comment: string;
  timestamp: string;
}

export interface InternalEvaluationReport extends PublicEvaluationReport {
  facultyNotes: FacultyNote[];
  explainabilityAnnotations: ExplainabilityAnnotation[];
  flaggingReasons: string[];
  assignedGuide: string;
  assignedReviewer: string | null;
  scoreOverrideHistory: ScoreOverrideEntry[];
}

// ─── Viva ─────────────────────────────────────────────────────────────────────

export interface VivaQuestion {
  questionId: string;
  text: string;
  category: string;
  difficulty: 'Easy' | 'Medium' | 'Hard' | 'Research';
  targetConcept: string;
  referenceAnswer?: string;
  expectedKeywords?: string[];
}

export interface VivaAnswerEvaluation {
  correctness: number;
  completeness: number;
  technicalDepth: number;
  confidence: number;
  overallScore: number;
}

export interface VivaAnswerResult {
  questionId: string;
  score: number; // 0-5
  maxScore: number;
  evaluation: VivaAnswerEvaluation;
  feedback: string;
  strongPoints: string[];
  weakPoints: string[];
  conceptCovered: string;
  nextQuestion: VivaQuestion | null;
  sessionComplete: boolean;
  kcsAfterAnswer: number;
}

export interface StartVivaResponse {
  sessionId: string;
  projectId: string;
  projectTitle: string;
  totalConcepts: number;
  firstQuestion: VivaQuestion;
  message: string;
}

export interface VivaConceptGap {
  concept: string;
  category: string;
  difficulty: VivaQuestion['difficulty'];
  questionsAsked: number;
  averageScore: number;
  gapSeverity: 'Critical' | 'Moderate' | 'Minor';
}

export interface VivaReport {
  sessionId: string;
  projectId: string;
  projectTitle: string;
  overallScore: number;
  kcs: number;
  difficultyReached: VivaQuestion['difficulty'];
  totalQuestionsAnswered: number;
  totalConceptsInProject: number;
  conceptsCovered: number;
  averageCorrectness: number;
  averageCompleteness: number;
  averageDepth: number;
  averageConfidence: number;
  categoryScores: Record<string, number>;
  difficultyProgression: string[];
  knowledgeGaps: VivaConceptGap[];
  strongAreas: string[];
  learningRecommendations: string[];
  grade: 'Distinction' | 'Merit' | 'Pass' | 'Needs Improvement';
  summaryStatement: string;
}

export interface VivaSession {
  sessionId: string;
  projectId: string;
  questions: VivaQuestion[];
  answers: VivaAnswerResult[];
  totalScore: number | null;
  isComplete: boolean;
}

// ─── Appeals ─────────────────────────────────────────────────────────────────

export type AppealStatus = 'pending' | 'under_review' | 'resolved' | 'rejected';

export interface Appeal {
  appealId: string;
  projectId: string;
  projectTitle: string;
  dimension: string;
  originalScore: number;
  studentJustification: string;
  status: AppealStatus;
  facultyResponse?: string;
  resolvedScore?: number;
  createdAt: string;
  resolvedAt?: string;
}

// ─── Rubrics ─────────────────────────────────────────────────────────────────

export interface RubricCriteria {
  criteriaId: string;
  name: string;
  weight: number;
  isRequired: boolean;
  description: string;
}

export interface Rubric {
  rubricId: string;
  name: string;
  department: string;
  createdBy: string;
  isApproved: boolean;
  criteria: RubricCriteria[];
  createdAt: string;
}

// ─── Leaderboard ─────────────────────────────────────────────────────────────

export interface LeaderboardEntry {
  rank: number;
  studentName: string;
  rollNo: string;
  projectTitle: string;
  domain: string;
  overallScore: number;
  badges: string[];
  isCurrentUser?: boolean;
}

// ─── Batch Upload ─────────────────────────────────────────────────────────────

export type BatchStatus = 'queued' | 'processing' | 'completed' | 'failed';

export interface BatchJobStatus {
  batchId: string;
  totalFiles: number;
  processed: number;
  failed: number;
  status: BatchStatus;
  startedAt: string;
  completedAt?: string;
  projects: ProjectSummary[];
}

// ─── Benchmarking ─────────────────────────────────────────────────────────────

export interface SemesterBenchmark {
  semester: string;
  year: number;
  avgNovelty: number;
  avgFeasibility: number;
  avgCompleteness: number;
  avgTechnicalDepth: number;
  avgClarity: number;
  avgOverall: number;
  topScore: number;
  totalProjects: number;
}

// ─── Dashboard Stats ─────────────────────────────────────────────────────────

export interface FacultyDashboardStats {
  totalSubmissions: number;
  pendingReview: number;
  flaggedDuplicates: number;
  avgScoreThisSemester: number;
  recentActivity: ActivityItem[];
}

export interface ActivityItem {
  id: string;
  type: 'submitted' | 'reviewed' | 'appealed' | 'published' | 'flagged';
  studentName: string;
  projectTitle: string;
  timestamp: string;
  details?: string;
}

export interface HODDeptStats {
  totalStudents: number;
  totalFaculty: number;
  totalSubmissions: number;
  reviewedCount: number;
  avgScore: number;
  domainDistribution: Record<string, number>;
  trendData: { month: string; avgScore: number }[];
}

// ─── User Management ─────────────────────────────────────────────────────────

export interface User {
  userId: string;
  name: string;
  email: string;
  rollNo?: string;
  role: UserRole;
  department: string;
  isActive: boolean;
  joinedAt: string;
}
