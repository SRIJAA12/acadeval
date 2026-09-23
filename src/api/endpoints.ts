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

export const createRubric = async (rubric: Omit<Rubric, 'rubricId' | 'createdAt'>): Promise<Rubric> => {
  const { data } = await apiClient.post<Rubric>('/rubrics', rubric);
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

export const getComparisonGraph = async (projectId: string, distanceThreshold = 0.5) => {
  const { data } = await apiClient.get(`/graph/comparison/${projectId}?distance_threshold=${distanceThreshold}`);
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

