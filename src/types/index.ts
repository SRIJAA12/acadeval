// ─── Core Domain Types ───────────────────────────────────────────────────────

export type SubmissionType = 'document' | 'journal' | 'abstract' | 'video';
export type PipelineStatus = 'uploaded' | 'ai_processing' | 'awaiting_review' | 'reviewed' | 'failed';
export type UserRole = 'student' | 'guide' | 'reviewer' | 'hod' | 'coordinator';
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
  githubUrl?: string | null;
  guideName?: string | null;
  reviewerName?: string | null;
  isPreliminary?: boolean;
  teamId?: string | null;
  guideSubmittedAt?: string | null;
  reviewerReadyAt?: string | null;
}

// ─── Assignment, Milestones, Discussion, Notifications, Audit ────────────────

export interface AssignRequest {
  guideId?: string;
  reviewerId?: string;
}

export type MilestoneStatus = 'pending' | 'submitted' | 'approved' | 'revision_requested';

export interface Milestone {
  milestoneId: string;
  orderIndex: number;
  title: string;
  description: string;
  status: MilestoneStatus;
  studentSubmission: string | null;
  guideComment: string | null;
  submittedAt: string | null;
  reviewedAt: string | null;
}

export interface DiscussionMessageItem {
  messageId: string;
  authorId: string;
  authorName: string;
  authorRole: string;
  body: string;
  createdAt: string;
  unread: boolean;
}

export interface NotificationItem {
  notificationId: string;
  type: string;
  title: string;
  body: string;
  link: string | null;
  isRead: boolean;
  createdAt: string;
}

export interface AuditLogEntry {
  auditLogId: string;
  actorName: string;
  actorRole: string;
  action: string;
  entityType: string;
  entityId: string;
  details: Record<string, unknown>;
  createdAt: string;
}

export interface ProgressUpdateItem {
  updateId: string;
  authorId: string;
  authorName: string;
  content: string;
  attachmentFilename?: string | null;
  githubUrl?: string | null;
  createdAt: string;
}

export interface GuideFeedback {
  guideId: string;
  guideName: string;
  overallScore: number;
  comment: string;
  updatedAt: string;
}

// ─── Plagiarism ──────────────────────────────────────────────────────────────

export type PlagiarismMatchType = 'text' | 'code';
export type PlagiarismReviewStatus = 'unreviewed' | 'confirmed' | 'acceptable_overlap' | 'uncertain' | 'no_issue';

export interface PlagiarismMatchItem {
  matchId: string;
  matchType: PlagiarismMatchType;
  sourceProjectId?: string | null;
  sourceLabel: string;
  candidatePassage: string;
  candidateLocation?: string | null;
  sourcePassage: string;
  sourceLocation?: string | null;
  score: number;
  reviewStatus: PlagiarismReviewStatus;
  reviewedByName?: string | null;
  reviewedAt?: string | null;
  reviewerComment?: string | null;
  createdAt: string;
}

export interface PlagiarismReport {
  projectId: string;
  textMax: number;
  codeMax: number;
  textMatchCount: number;
  codeMatchCount: number;
  codeFetchError?: string | null;
  matches: PlagiarismMatchItem[];
  summaryText: string;
}

// ─── Coordinator: roster allocation, reviewer slots, review rounds ───────────

export interface RosterRowResult {
  rowNumber: number;
  rollNo: string;
  status: 'applied' | 'pending' | 'error';
  message: string;
}

export interface RosterUploadResponse {
  totalRows: number;
  applied: number;
  pending: number;
  errors: number;
  results: RosterRowResult[];
}

export interface RosterAllocationItem {
  allocationId: string;
  rollNo: string;
  studentEmail?: string | null;
  teamId?: string | null;
  guideName?: string | null;
  domain?: string | null;
  isApplied: boolean;
  error?: string | null;
  createdAt: string;
}

export interface ReviewerSlot {
  slotId: string;
  name: string;
  email: string;
  isActive: boolean;
  createdAt: string;
}

export interface ReviewRound {
  roundId: string;
  name: string;
  description?: string | null;
  scheduledDate?: string | null;
  isFinal: boolean;
  createdAt: string;
  assignmentCount: number;
  publishedCount: number;
}

export interface ReviewSlotAssignmentItem {
  assignmentId: string;
  roundId: string;
  projectId: string;
  projectTitle: string;
  studentName: string;
  reviewerSlotId: string;
  reviewerSlotName: string;
  staffEmail: string;
  scheduledAt?: string | null;
  credentialEmailSent: boolean;
  createdAt: string;
}

export interface RoundEvaluationItem {
  evaluationId: string;
  roundId: string;
  roundName: string;
  isFinalRound: boolean;
  projectId: string;
  reviewerSlotName: string;
  novelty: number | null;
  feasibility: number | null;
  completeness: number | null;
  technicalDepth: number | null;
  clarity: number | null;
  similarityRisk: number | null;
  publicationPotential: number | null;
  overallScore: number | null;
  grade: string | null;
  comment: string;
  isPublished: boolean;
  publishedAt?: string | null;
  updatedAt: string;
}

// ─── Teams ─────────────────────────────────────────────────────────────────

export interface TeamMember {
  studentId: string;
  name: string;
  rollNo?: string | null;
  role: 'member' | 'lead';
}

export interface TeamItem {
  teamId: string;
  teamCode: string;
  name?: string | null;
  members: TeamMember[];
  createdAt: string;
}

export interface TeamMessageItem {
  messageId: string;
  authorId: string;
  authorName: string;
  body: string;
  mentionedUserIds: string[];
  createdAt: string;
}

export type TaskStatus = 'pending' | 'done';
export type TaskSource = 'manual' | 'guide_request' | 'review_scheduled' | 'team';

export interface TaskItem {
  taskId: string;
  projectId?: string | null;
  projectTitle?: string | null;
  teamId?: string | null;
  teamCode?: string | null;
  assigneeId: string;
  assigneeName: string;
  createdByName?: string | null;
  title: string;
  description?: string | null;
  status: TaskStatus;
  source: TaskSource;
  dueDate?: string | null;
  createdAt: string;
  completedAt?: string | null;
}

export interface CoordinatorOverview {
  totalProjects: number;
  unallocatedProjects: number;
  pendingRosterRows: number;
  reviewerSlotCount: number;
  activeRoundCount: number;
  rubricsPendingApproval: number;
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

export interface ExplainabilitySignal {
  signal_key: string;
  signal_name: string;
  plain_name?: string;
  question?: string;
  plain_meaning?: string;
  analogy?: string;
  high_meaning?: string;
  low_meaning?: string;
  raw_value: number;
  weight: number;
  weighted_contribution: number;
  max_possible_contribution: number;
  percentage_of_max: number;
  dataset_source?: string;
  method?: string;
  explanation: string;
}

export interface ExplainabilityDimensionScore {
  dimension_key: string;
  dimension_name: string;
  raw_score: number;
  weight: number;
  weight_percentage: number;
  weighted_contribution: number;
  max_possible_contribution: number;
  percentage_of_max: number;
  formula: string;
  description: string;
  explanation: string;
}

export interface ExplainabilityDatasetComparison {
  dataset_name: string;
  dataset_category: string;
  role: string;
  algorithm_used: string;
  comparative_metric: string;
  status: string;
  status_color: string;
  explanation: string;
}

export interface ExplainabilityResult {
  explainer_mode: string;
  composite_novelty_score: number;
  novelty_band: string;
  overall_score?: number;
  overall_grade?: string;
  overall_summary: string;
  signals: ExplainabilitySignal[];
  dimension_scores?: ExplainabilityDimensionScore[];
  dataset_comparisons?: ExplainabilityDatasetComparison[];
}

// ─── Score Coach ───────────────────────────────────────────────────────────────

export type CoachStatus = 'strong' | 'fair' | 'low' | 'not_scored';

export interface CoachAction {
  text: string;
  points: number;
}

export interface CoachCriterion {
  key: string;
  name: string;
  score: number;
  max_reachable: number;
  status: CoachStatus;
  standard: string;
  found: string[];
  gaps: string[];
}

export interface CoachDimension {
  key: string;
  name: string;
  weight_percent: number;
  score: number | null;
  status: CoachStatus;
  points_earned: number;
  points_recoverable: number;
  max_reachable: number;
  why: string[];
  gaps: string[];
  actions: CoachAction[];
  standard_for_100: string[];
  note: string;
  criteria: CoachCriterion[];
}

export interface CoachPriority {
  dimension_key: string;
  name: string;
  points_recoverable: number;
  top_action: string;
}

export interface ScoreCoach {
  method_version: string;
  available: boolean;
  message?: string;
  overall_score?: number;
  grade?: string;
  max_overall_reachable?: number;
  next_grade?: { grade: string; threshold: number; points_needed: number } | null;
  evidence_quality?: string;
  grading_scale?: { grade: string; min: number }[];
  summary?: string;
  dimensions: CoachDimension[];
  priorities: CoachPriority[];
  disclaimer?: string;
}

export interface CoachAnswer {
  answer: string;
  source: 'ai' | 'rules';
  relatedDimensions: string[];
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
  explainability?: ExplainabilityResult;
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

export interface VivaHistoryItem {
  sessionId: string;
  projectId: string;
  projectTitle: string;
  isComplete: boolean;
  totalScore: number | null;
  kcs: number | null;
  questionsAnswered: number;
  createdAt: string;
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
  academicYear?: string | null;
  version: number;
  supersedesId?: string | null;
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
  recentOverrides?: {
    id: string;
    projectId: string;
    dimension: string;
    oldValue: number;
    newValue: number;
    changedByName: string;
    comment: string;
    timestamp: string;
  }[];
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

// ─── Live Quality Dashboard (HOD only) ───────────────────────────────────────
// Every metric is kept separate — there is deliberately no single combined
// "accuracy %" field anywhere in this module. See app/routers/quality.py.

export interface QualityMetricPoint {
  metric: string;
  variant: string;
  slice: string;
  value: number | null;
  n: number | null;
  ci_low: number | null;
  ci_high: number | null;
  target: number | null;
  target_op: string | null;
  passed: boolean | null;
  details: Record<string, unknown>;
}

export interface QualityRunSummary {
  run_id: string;
  started_at: string;
  trigger: string;
  label: string | null;
  method_fingerprint: string | null;
  n_cases: number | null;
  duration_ms: number | null;
  metrics: QualityMetricPoint[];
}

export interface QualitySummary {
  current_method_fingerprint: string;
  current_versions: Record<string, string>;
  runs: {
    benchmark: QualityRunSummary | null;
    graph_integrity: QualityRunSummary | null;
    faculty_agreement: QualityRunSummary | null;
    online_rollup: QualityRunSummary | null;
  };
}

export interface QualityTimeseries {
  metric: string;
  variant: string;
  slice: string;
  points: {
    started_at: string;
    label: string | null;
    value: number | null;
    n: number | null;
    ci_low: number | null;
    ci_high: number | null;
    passed: boolean | null;
  }[];
}

export interface QualityAblation {
  run_id: string | null;
  started_at?: string;
  variants: Record<string, { metric: string; slice: string; value: number | null; n: number | null; passed: boolean | null }[]>;
}

export interface QualityRun {
  run_id: string;
  kind: string;
  trigger: string;
  status: string;
  label: string | null;
  method_fingerprint: string | null;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
  n_cases: number | null;
  error: string | null;
}

export interface QualityTelemetryRow {
  run_id: string;
  project_id: string;
  status: string;
  failed_stage: string | null;
  total_ms: number | null;
  novelty_score: number | null;
  overall_score: number | null;
  invariants_passed: boolean | null;
  evidence_quality: string | null;
  corpus_key_coverage: number | null;
  created_at: string;
}

export interface QualityFacultyAgreement {
  run_id: string | null;
  started_at?: string;
  metrics: { metric: string; value: number | null; n: number | null; details: Record<string, unknown> }[];
  note: string;
}
