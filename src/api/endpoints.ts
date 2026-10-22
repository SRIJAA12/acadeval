import apiClient from './client';
import type {
  LoginRequest,
  LoginResponse,
  ProjectSummary,
  PublicEvaluationReport,
  InternalEvaluationReport,
  VivaAnswerResult,
  StartVivaResponse,
  VivaReport,
  Appeal,
  Rubric,
  LeaderboardEntry,
  BatchJobStatus,
  SemesterBenchmark,
  FacultyDashboardStats,
  HODDeptStats,
  User,
  QualitySummary,
  QualityTimeseries,
  QualityAblation,
  QualityRun,
  QualityTelemetryRow,
  QualityFacultyAgreement,
  AssignRequest,
  Milestone,
  DiscussionMessageItem,
  NotificationItem,
  AuditLogEntry,
  VivaHistoryItem,
  ProgressUpdateItem,
  GuideFeedback,
  RosterUploadResponse,
  RosterAllocationItem,
  ReviewerSlot,
  ReviewRound,
  ReviewSlotAssignmentItem,
  RoundEvaluationItem,
  CoordinatorOverview,
  ExplainabilityResult,
  TeamItem,
  TeamMessageItem,
  TaskItem,
  PlagiarismReport,
  PlagiarismMatchItem,
  PlagiarismReviewStatus,
} from '../types';
import type { NoveltyReportData } from '../components/NoveltyReportView';

export const login = async (req: LoginRequest): Promise<LoginResponse> => {
  const { data } = await apiClient.post<LoginResponse>('/auth/login', req);
  return data;
};

export const getMyProjects = async (): Promise<ProjectSummary[]> => {
  const { data } = await apiClient.get<ProjectSummary[]>('/projects/my');
  return data;
};

export const deleteProject = async (projectId: string): Promise<void> => {
  await apiClient.delete(`/projects/${projectId}`);
};

export const getAllProjects = async (): Promise<ProjectSummary[]> => {
  const { data } = await apiClient.get<ProjectSummary[]>('/projects');
  return data;
};

export const getProjectStatus = async (projectId: string): Promise<{ status: string }> => {
  const { data } = await apiClient.get(`/projects/${projectId}/status`);
  return data;
};

export const getPipelineStatus = async (projectId: string): Promise<{
  project_id: string;
  db_status: string;
  celery_state: string | null;
  celery_task_id: string | null;
  ready: boolean;
  error: string | null;
}> => {
  const { data } = await apiClient.get(`/projects/${projectId}/pipeline-status`);
  return data;
};

export const uploadProject = async (formData: FormData): Promise<{ projectId: string }> => {
  const { data } = await apiClient.post('/projects/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};

export const getEvaluationReport = async (
  projectId: string,
  role: string,
): Promise<PublicEvaluationReport | InternalEvaluationReport> => {
  if (role === 'student') {
    const { data } = await apiClient.get<PublicEvaluationReport>(`/projects/${projectId}/report/public`);
    return data;
  }
  const { data } = await apiClient.get<InternalEvaluationReport>(`/projects/${projectId}/report/internal`);
  return data;
};

export const getNoveltyReport = async (projectId: string): Promise<NoveltyReportData> => {
  const { data } = await apiClient.get<NoveltyReportData>(`/v1/acadeval/report/${projectId}`);
  return data;
};

export const submitFacultyNoveltyReview = async (
  projectId: string,
  facultyScore: number,
  systemScore: number,
  overrideReason?: string,
): Promise<void> => {
  await apiClient.post('/v1/acadeval/faculty-review', {
    project_id: projectId,
    faculty_score: facultyScore,
    system_score: systemScore,
    override_reason: overrideReason || null,
  });
};

export const overrideScore = async (
  projectId: string,
  dimension: string,
  newValue: number,
  comment: string,
): Promise<void> => {
  await apiClient.patch(`/projects/${projectId}/scores`, { dimension, newValue, comment });
};

export const addFacultyNote = async (projectId: string, text: string): Promise<void> => {
  await apiClient.post(`/projects/${projectId}/notes`, { text });
};

export const publishReview = async (projectId: string): Promise<void> => {
  await apiClient.post(`/projects/${projectId}/publish`);
};

export const startVivaSession = async (projectId: string): Promise<StartVivaResponse> => {
  const { data } = await apiClient.post<StartVivaResponse>('/viva/session/start', {
    projectId,
    startDifficulty: 'Easy',
  });
  return data;
};

export const submitVivaAnswer = async (
  sessionId: string,
  questionId: string,
  answer: string,
): Promise<VivaAnswerResult> => {
  const { data } = await apiClient.post<VivaAnswerResult>('/viva/answer', { sessionId, questionId, answer });
  return data;
};

export const getVivaReport = async (sessionId: string): Promise<VivaReport> => {
  const { data } = await apiClient.get<VivaReport>(`/viva/session/${sessionId}/report`);
  return data;
};

export const getMyAppeals = async (): Promise<Appeal[]> => {
  const { data } = await apiClient.get<Appeal[]>('/appeals');
  return data;
};

export const getAllAppeals = async (): Promise<Appeal[]> => {
  const { data } = await apiClient.get<Appeal[]>('/appeals');
  return data;
};

export const submitAppeal = async (
  projectId: string,
  dimension: string,
  originalScore: number,
  justification: string,
): Promise<{ appealId: string }> => {
  const { data } = await apiClient.post('/appeals', {
    projectId,
    dimension,
    originalScore,
    studentJustification: justification,
  });
  return data;
};

export const resolveAppeal = async (
  appealId: string,
  action: 'approve' | 'reject',
  resolvedScore?: number,
  facultyResponse = '',
): Promise<void> => {
  await apiClient.patch(`/appeals/${appealId}`, { action, resolvedScore, facultyResponse });
};

export const getRubrics = async (): Promise<Rubric[]> => {
  const { data } = await apiClient.get<Rubric[]>('/rubrics');
  return data;
};

export interface RubricCreatePayload {
  name: string;
  department: string;
  academicYear?: string;
  criteria: Rubric['criteria'];
}

export const createRubric = async (rubric: RubricCreatePayload): Promise<Rubric> => {
  const { data } = await apiClient.post<Rubric>('/rubrics', rubric);
  return data;
};

export const editRubric = async (rubricId: string, rubric: RubricCreatePayload): Promise<Rubric> => {
  const { data } = await apiClient.put<Rubric>(`/rubrics/${rubricId}`, rubric);
  return data;
};

export const approveRubric = async (rubricId: string): Promise<void> => {
  await apiClient.patch(`/rubrics/${rubricId}/approve`);
};

export const getLeaderboard = async (): Promise<LeaderboardEntry[]> => {
  const { data } = await apiClient.get<LeaderboardEntry[]>('/leaderboard');
  return data;
};

export const uploadBatch = async (formData: FormData): Promise<{ batchId: string }> => {
  const { data } = await apiClient.post('/projects/batch', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};

export const getBatchStatus = async (batchId: string): Promise<BatchJobStatus> => {
  const { data } = await apiClient.get<BatchJobStatus>(`/projects/batch/${batchId}/status`);
  return data;
};

export const getBenchmarks = async (): Promise<SemesterBenchmark[]> => {
  const { data } = await apiClient.get<SemesterBenchmark[]>('/benchmarks');
  return data;
};

export const getFacultyDashboard = async (): Promise<FacultyDashboardStats> => {
  const { data } = await apiClient.get<FacultyDashboardStats>('/dashboard/faculty');
  return data;
};

export const getHODStats = async (): Promise<HODDeptStats> => {
  const { data } = await apiClient.get<HODDeptStats>('/dashboard/hod');
  return data;
};

export const getUsers = async (): Promise<User[]> => {
  const { data } = await apiClient.get<User[]>('/users');
  return data;
};

export const updateUserRole = async (userId: string, role: string): Promise<void> => {
  await apiClient.patch(`/users/${userId}/role`, { role });
};

export const getKnowledgeBase = async (params?: {
  category?: string;
  search?: string;
  limit?: number;
  offset?: number;
}) => {
  const { data } = await apiClient.get('/entities/knowledge-base', { params });
  return data;
};

export const getProjectEntities = async (projectId: string) => {
  const { data } = await apiClient.get(`/entities/project/${projectId}`);
  return data;
};

export const getPendingReviewEntities = async () => {
  const { data } = await apiClient.get('/entities/pending-review');
  return data;
};

export const approveEntityReview = async (name: string, payload: object) => {
  const { data } = await apiClient.post(`/entities/pending-review/${encodeURIComponent(name)}/approve`, payload);
  return data;
};

export const rejectEntityReview = async (name: string) => {
  const { data } = await apiClient.post(`/entities/pending-review/${encodeURIComponent(name)}/reject`);
  return data;
};

export const getGraphSummary = async (refresh = false) => {
  const { data } = await apiClient.get(`/graph/summary${refresh ? '?refresh=true' : ''}`);
  return data;
};

export const getGraphVisualization = async (limit = 300, nodeTypes?: string) => {
  const params = new URLSearchParams();
  if (limit) params.append('limit', limit.toString());
  if (nodeTypes) params.append('node_types', nodeTypes);
  const { data } = await apiClient.get(`/graph/visualization?${params.toString()}`);
  return data;
};

export const getNodeNeighborhood = async (query: string, radius = 1) => {
  const { data } = await apiClient.get(`/graph/node/${encodeURIComponent(query)}?radius=${radius}`);
  return data;
};

export const rebuildKnowledgeGraph = async () => {
  const { data } = await apiClient.post('/graph/rebuild');
  return data;
};

export const getProjectGraph = async (projectId: string) => {
  const { data } = await apiClient.get(`/graph/project/${projectId}`);
  return data;
};

export const getComparisonGraph = async (projectId: string, compareProjectId?: string) => {
  const params = new URLSearchParams();
  if (compareProjectId) {
    params.append('compare_project_id', compareProjectId);
  }
  const { data } = await apiClient.get(`/graph/comparison/${projectId}?${params.toString()}`);
  return data;
};

export const rebuildProjectGraph = async (projectId: string) => {
  const { data } = await apiClient.post(`/graph/rebuild/${projectId}`);
  return data;
};

export const getProjectNoveltyReport = async (projectId: string, distanceThreshold = 0.5) => {
  const { data } = await apiClient.get(`/v1/acadeval/report/${projectId}?distance_threshold=${distanceThreshold}`);
  return data;
};

export const getProjectExplainability = async (projectId: string): Promise<ExplainabilityResult> => {
  const { data } = await apiClient.get<ExplainabilityResult>(`/projects/${projectId}/explainability`);
  return data;
};

// ── Live Quality Dashboard (HOD only) — see app/routers/quality.py ────────────

export const getQualitySummary = async (): Promise<QualitySummary> => {
  const { data } = await apiClient.get('/v1/quality/summary');
  return data;
};

export const getQualityTimeseries = async (
  metric: string, variant = 'graph_only', slice = 'all', days = 30
): Promise<QualityTimeseries> => {
  const { data } = await apiClient.get('/v1/quality/timeseries', {
    params: { metric, variant, slice, days },
  });
  return data;
};

export const getQualityAblation = async (): Promise<QualityAblation> => {
  const { data } = await apiClient.get('/v1/quality/ablation');
  return data;
};

export const getQualityRuns = async (kind?: string, limit = 50): Promise<QualityRun[]> => {
  const { data } = await apiClient.get('/v1/quality/runs', { params: { kind, limit } });
  return data;
};

export const getRecentTelemetry = async (limit = 50): Promise<QualityTelemetryRow[]> => {
  const { data } = await apiClient.get('/v1/quality/telemetry/recent', { params: { limit } });
  return data;
};

export const getFacultyAgreementLatest = async (): Promise<QualityFacultyAgreement> => {
  const { data } = await apiClient.get('/v1/quality/faculty-agreement');
  return data;
};

export const triggerBenchmarkRun = async (label?: string): Promise<{ queued: boolean; task_id: string }> => {
  const { data } = await apiClient.post('/v1/quality/benchmark/run', null, { params: { label } });
  return data;
};

// ── Assignment (HOD) ───────────────────────────────────────────────────────────

export const getUnassignedProjects = async (): Promise<ProjectSummary[]> => {
  const { data } = await apiClient.get<ProjectSummary[]>('/projects/unassigned');
  return data;
};

export const assignProject = async (projectId: string, payload: AssignRequest): Promise<ProjectSummary> => {
  const { data } = await apiClient.patch<ProjectSummary>(`/projects/${projectId}/assign`, payload);
  return data;
};

export const submitToGuide = async (projectId: string): Promise<ProjectSummary> => {
  const { data } = await apiClient.patch<ProjectSummary>(`/projects/${projectId}/submit-to-guide`);
  return data;
};

export const markReadyForReview = async (projectId: string): Promise<ProjectSummary> => {
  const { data } = await apiClient.patch<ProjectSummary>(`/projects/${projectId}/mark-ready-for-review`);
  return data;
};

// ── Milestones ────────────────────────────────────────────────────────────────

export const getMilestones = async (projectId: string): Promise<Milestone[]> => {
  const { data } = await apiClient.get<Milestone[]>(`/projects/${projectId}/milestones`);
  return data;
};

export const submitMilestone = async (milestoneId: string, text: string): Promise<Milestone> => {
  const { data } = await apiClient.patch<Milestone>(`/milestones/${milestoneId}/submit`, { text });
  return data;
};

export const reviewMilestone = async (
  milestoneId: string, approve: boolean, comment?: string
): Promise<Milestone> => {
  const { data } = await apiClient.patch<Milestone>(`/milestones/${milestoneId}/review`, { approve, comment });
  return data;
};

// ── Discussion ────────────────────────────────────────────────────────────────

export const getDiscussion = async (projectId: string): Promise<DiscussionMessageItem[]> => {
  const { data } = await apiClient.get<DiscussionMessageItem[]>(`/projects/${projectId}/discussion`);
  return data;
};

export const postDiscussionMessage = async (projectId: string, body: string): Promise<DiscussionMessageItem> => {
  const { data } = await apiClient.post<DiscussionMessageItem>(`/projects/${projectId}/discussion`, { body });
  return data;
};

export const markDiscussionRead = async (projectId: string): Promise<void> => {
  await apiClient.post(`/projects/${projectId}/discussion/read`);
};

// ── Notifications ─────────────────────────────────────────────────────────────

export const getNotifications = async (limit = 30): Promise<NotificationItem[]> => {
  const { data } = await apiClient.get<NotificationItem[]>('/notifications', { params: { limit } });
  return data;
};

export const getUnreadNotificationCount = async (): Promise<number> => {
  const { data } = await apiClient.get<{ count: number }>('/notifications/unread-count');
  return data.count;
};

export const markNotificationRead = async (notificationId: string): Promise<void> => {
  await apiClient.patch(`/notifications/${notificationId}/read`);
};

export const markAllNotificationsRead = async (): Promise<void> => {
  await apiClient.post('/notifications/read-all');
};

// ── Audit log (HOD) ───────────────────────────────────────────────────────────

export const getAuditLogs = async (limit = 100): Promise<AuditLogEntry[]> => {
  const { data } = await apiClient.get<AuditLogEntry[]>('/audit-logs', { params: { limit } });
  return data;
};

// ── Viva history ──────────────────────────────────────────────────────────────

export const getVivaHistory = async (): Promise<VivaHistoryItem[]> => {
  const { data } = await apiClient.get<VivaHistoryItem[]>('/viva/history');
  return data;
};

// ── Progress updates (append-only student log) ────────────────────────────────

export const getProgressUpdates = async (projectId: string): Promise<ProgressUpdateItem[]> => {
  const { data } = await apiClient.get<ProgressUpdateItem[]>(`/projects/${projectId}/progress`);
  return data;
};

export const postProgressUpdate = async (
  projectId: string, content: string, options?: { file?: File; githubUrl?: string }
): Promise<ProgressUpdateItem> => {
  const formData = new FormData();
  formData.append('content', content);
  if (options?.githubUrl) formData.append('githubUrl', options.githubUrl);
  if (options?.file) formData.append('file', options.file);
  const { data } = await apiClient.post<ProgressUpdateItem>(`/projects/${projectId}/progress`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};

export const downloadProgressAttachment = async (projectId: string, updateId: string, filename: string): Promise<void> => {
  const { data } = await apiClient.get(`/projects/${projectId}/progress/${updateId}/attachment`, { responseType: 'blob' });
  const url = window.URL.createObjectURL(data as Blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
};

// ── Guide feedback (informal — separate from the reviewer's official grade) ───

export const getGuideFeedback = async (projectId: string): Promise<GuideFeedback | null> => {
  const { data } = await apiClient.get<GuideFeedback | null>(`/projects/${projectId}/guide-feedback`);
  return data;
};

export const updateGuideFeedback = async (
  projectId: string, overallScore: number, comment: string
): Promise<GuideFeedback> => {
  const { data } = await apiClient.put<GuideFeedback>(`/projects/${projectId}/guide-feedback`, { overallScore, comment });
  return data;
};

// ── Coordinator ────────────────────────────────────────────────────────────────

export const getCoordinatorOverview = async (): Promise<CoordinatorOverview> => {
  const { data } = await apiClient.get<CoordinatorOverview>('/coordinator/overview');
  return data;
};

export const uploadRoster = async (file: File): Promise<RosterUploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await apiClient.post<RosterUploadResponse>('/coordinator/roster/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};

export const getRoster = async (): Promise<RosterAllocationItem[]> => {
  const { data } = await apiClient.get<RosterAllocationItem[]>('/coordinator/roster');
  return data;
};

export const getReviewerSlots = async (): Promise<ReviewerSlot[]> => {
  const { data } = await apiClient.get<ReviewerSlot[]>('/coordinator/reviewer-slots');
  return data;
};

export const createReviewerSlot = async (name: string): Promise<ReviewerSlot> => {
  const { data } = await apiClient.post<ReviewerSlot>('/coordinator/reviewer-slots', { name });
  return data;
};

export const getReviewRounds = async (): Promise<ReviewRound[]> => {
  const { data } = await apiClient.get<ReviewRound[]>('/coordinator/review-rounds');
  return data;
};

export const createReviewRound = async (payload: {
  name: string; description?: string; scheduledDate?: string; isFinal: boolean;
}): Promise<ReviewRound> => {
  const { data } = await apiClient.post<ReviewRound>('/coordinator/review-rounds', payload);
  return data;
};

export const getRoundAssignments = async (roundId: string): Promise<ReviewSlotAssignmentItem[]> => {
  const { data } = await apiClient.get<ReviewSlotAssignmentItem[]>(`/coordinator/review-rounds/${roundId}/assignments`);
  return data;
};

export const createRoundAssignment = async (roundId: string, payload: {
  projectIds?: string[]; teamId?: string; reviewerSlotId: string; staffEmail: string; scheduledAt?: string;
}): Promise<ReviewSlotAssignmentItem[]> => {
  const { data } = await apiClient.post<ReviewSlotAssignmentItem[]>(`/coordinator/review-rounds/${roundId}/assignments`, payload);
  return data;
};

export const getRoundEvaluations = async (projectId: string): Promise<RoundEvaluationItem[]> => {
  const { data } = await apiClient.get<RoundEvaluationItem[]>(`/coordinator/projects/${projectId}/round-evaluations`);
  return data;
};

export const updateRoundEvaluation = async (
  projectId: string, roundId: string,
  payload: {
    novelty?: number; feasibility?: number; completeness?: number; technicalDepth?: number;
    clarity?: number; similarityRisk?: number; publicationPotential?: number; comment: string;
  }
): Promise<RoundEvaluationItem> => {
  const { data } = await apiClient.put<RoundEvaluationItem>(
    `/coordinator/projects/${projectId}/rounds/${roundId}/evaluation`, payload
  );
  return data;
};

export const publishRoundEvaluation = async (
  projectId: string, roundId: string
): Promise<{ message: string; isFinal: boolean; syncedOfficialReport: boolean }> => {
  const { data } = await apiClient.post(`/coordinator/projects/${projectId}/rounds/${roundId}/publish`);
  return data;
};

// ── Teams ──────────────────────────────────────────────────────────────────────

export const getMyTeams = async (): Promise<TeamItem[]> => {
  const { data } = await apiClient.get<TeamItem[]>('/teams/my');
  return data;
};

export const getAllTeams = async (): Promise<TeamItem[]> => {
  const { data } = await apiClient.get<TeamItem[]>('/coordinator/teams');
  return data;
};

export const getTeam = async (teamId: string): Promise<TeamItem> => {
  const { data } = await apiClient.get<TeamItem>(`/teams/${teamId}`);
  return data;
};

export const getTeamMessages = async (teamId: string): Promise<TeamMessageItem[]> => {
  const { data } = await apiClient.get<TeamMessageItem[]>(`/teams/${teamId}/messages`);
  return data;
};

export const postTeamMessage = async (teamId: string, body: string): Promise<TeamMessageItem> => {
  const { data } = await apiClient.post<TeamMessageItem>(`/teams/${teamId}/messages`, { body });
  return data;
};

export const getTeamTasks = async (teamId: string): Promise<TaskItem[]> => {
  const { data } = await apiClient.get<TaskItem[]>(`/teams/${teamId}/tasks`);
  return data;
};

export const createTeamTask = async (
  teamId: string, payload: { title: string; description?: string; assigneeId?: string; dueDate?: string }
): Promise<TaskItem> => {
  const { data } = await apiClient.post<TaskItem>(`/teams/${teamId}/tasks`, payload);
  return data;
};

export const getMyTasks = async (): Promise<TaskItem[]> => {
  const { data } = await apiClient.get<TaskItem[]>('/tasks/my');
  return data;
};

export const createTask = async (
  payload: { title: string; description?: string; projectId?: string; dueDate?: string }
): Promise<TaskItem> => {
  const { data } = await apiClient.post<TaskItem>('/tasks', payload);
  return data;
};

export const updateTaskStatus = async (taskId: string, status: 'pending' | 'done'): Promise<TaskItem> => {
  const { data } = await apiClient.patch<TaskItem>(`/tasks/${taskId}`, { status });
  return data;
};

// ── Plagiarism ─────────────────────────────────────────────────────────────────

export const getPlagiarismReport = async (projectId: string): Promise<PlagiarismReport> => {
  const { data } = await apiClient.get<PlagiarismReport>(`/projects/${projectId}/plagiarism-report`);
  return data;
};

export const reviewPlagiarismMatch = async (
  matchId: string, reviewStatus: Exclude<PlagiarismReviewStatus, 'unreviewed'>, reviewerComment?: string
): Promise<PlagiarismMatchItem> => {
  const { data } = await apiClient.patch<PlagiarismMatchItem>(`/plagiarism-matches/${matchId}/review`, {
    reviewStatus, reviewerComment,
  });
  return data;
};

