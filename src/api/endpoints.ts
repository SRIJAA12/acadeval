import apiClient from './client';
import type {
  LoginRequest, LoginResponse, ProjectSummary, PublicEvaluationReport,
  InternalEvaluationReport, VivaQuestion, VivaAnswerResult, Appeal,
  Rubric, LeaderboardEntry, BatchJobStatus, SemesterBenchmark,
  FacultyDashboardStats, HODDeptStats, User, SubmissionType,
} from '../types';
import type { NoveltyReportData } from '../components/NoveltyReportView';
import {
  mockProjects, mockPublicReport, mockInternalReport, mockLeaderboard,
  mockVivaQuestions, mockVivaAnswer, mockAppeals, mockFacultyDashboard,
  mockRubric, mockBenchmarks, mockHODStats, mockUsers, mockNoveltyReport,
} from './mockData';

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';
const delay = (ms = 600) => new Promise(res => setTimeout(res, ms));

// ─── Mock Persistence (survives Vite HMR reloads) ────────────────────────────
// Extra fields stored per submitted project so entity extraction has real text.
type PersistedProject = {
  projectId: string;
  title: string;
  abstract: string;
  githubUrl: string;
  domain: string;
  submissionType: string;
  rollNo: string;
  studentName: string;
  submittedOn: string;
  pipelineStatus: string;
  overallScore: number;
};

const STORAGE_KEY = 'acadeval_submitted_projects';

function loadPersistedProjects(): PersistedProject[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function savePersistedProjects(projects: PersistedProject[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(projects));
  } catch { /* storage full — ignore */ }
}

// Hydrate mockProjects with any persisted submissions (runs once on module load)
(function hydrateFromStorage() {
  const persisted = loadPersistedProjects();
  for (const p of persisted) {
    const alreadyIn = mockProjects.some(m => m.projectId === p.projectId);
    if (!alreadyIn) {
      mockProjects.unshift(p as any);
    }
  }
})();

// ─── Auth ─────────────────────────────────────────────────────────────────────
export const login = async (req: LoginRequest): Promise<LoginResponse> => {
  if (USE_MOCK) {
    await delay(800);
    const roleTokens: Record<string, string> = {
      student: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1MDAxIiwicm9sZSI6InN0dWRlbnQiLCJuYW1lIjoiUHJpeWEgU2hhcm1hIiwiZW1haWwiOiJwcml5YUBjb2xsZWdlLmVkdSIsImV4cCI6OTk5OTk5OTk5OX0.mock',
      guide: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmMDAxIiwicm9sZSI6Imd1aWRlIiwibmFtZSI6IkRyLiBNZWVyYSBLcmlzaG5hbiIsImVtYWlsIjoibWVlcmFAY29sbGVnZS5lZHUiLCJleHAiOjk5OTk5OTk5OTl9.mock',
      reviewer: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmMDAyIiwicm9sZSI6InJldmlld2VyIiwibmFtZSI6IlByb2YuIFN1cmVzaCBSYWphbiIsImVtYWlsIjoic3VyZXNoQGNvbGxlZ2UuZWR1IiwiZXhwIjo5OTk5OTk5OTk5fQ.mock',
      hod: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJoMDAxIiwicm9sZSI6ImhvZCIsIm5hbWUiOiJEci4gQW5hbmQgS3Jpc2huYW11cnRoeSIsImVtYWlsIjoiaG9kQGNvbGxlZ2UuZWR1IiwiZXhwIjo5OTk5OTk5OTk5fQ.mock',
    };
    const userMap = {
      student: { id: 'u001', name: 'Priya Sharma', email: 'priya@college.edu', role: 'student' as const },
      guide: { id: 'f001', name: 'Dr. Meera Krishnan', email: 'meera@college.edu', role: 'guide' as const },
      reviewer: { id: 'f002', name: 'Prof. Suresh Rajan', email: 'suresh@college.edu', role: 'reviewer' as const },
      hod: { id: 'h001', name: 'Dr. Anand Krishnamurthy', email: 'hod@college.edu', role: 'hod' as const },
    };
    return { access_token: roleTokens[req.role], token_type: 'bearer', user: userMap[req.role] };
  }
  const { data } = await apiClient.post<LoginResponse>('/auth/login', req);
  return data;
};

// ─── Projects ─────────────────────────────────────────────────────────────────
export const getMyProjects = async (): Promise<ProjectSummary[]> => {
  if (USE_MOCK) { await delay(); return mockProjects.filter(p => p.rollNo === 'CS2021001'); }
  const { data } = await apiClient.get<ProjectSummary[]>('/projects/my');
  return data;
};

export const deleteProject = async (projectId: string): Promise<void> => {
  if (USE_MOCK) {
    await delay(300);
    const idx = mockProjects.findIndex(x => x.projectId === projectId);
    if (idx !== -1) mockProjects.splice(idx, 1);
    return;
  }
  await apiClient.delete(`/projects/${projectId}`);
};

export const getAllProjects = async (): Promise<ProjectSummary[]> => {
  if (USE_MOCK) { await delay(); return mockProjects; }
  const { data } = await apiClient.get<ProjectSummary[]>('/projects');
  return data;
};

export const getProjectStatus = async (projectId: string): Promise<{ status: string }> => {
  if (USE_MOCK) {
    await delay(300);
    const p = mockProjects.find(x => x.projectId === projectId);
    return { status: p?.pipelineStatus || 'uploaded' };
  }
  const { data } = await apiClient.get(`/projects/${projectId}/status`);
  return data;
};

export const uploadProject = async (formData: FormData): Promise<{ projectId: string }> => {
  if (USE_MOCK) {
    await delay(1200);
    const mode = (formData.get('mode') as SubmissionType) || 'document';
    const domain = (formData.get('domain') as string) || 'AI/ML';
    const githubUrl = (formData.get('githubUrl') as string) || '';
    const abstract = (formData.get('abstract') as string) || '';
    const files = formData.getAll('files') as File[];
    const fileName = files[0]?.name;
    const defaultTitle = mode === 'video' ? 'Video Presentation Analysis' : 'Submitted Project Report';
    const title = (formData.get('title') as string) || fileName || defaultTitle;
    const projectId = `p_${Date.now()}`;

    const newProj: PersistedProject = {
      projectId,
      studentName: 'Priya Sharma',
      rollNo: 'CS2021001',
      title,
      abstract,
      githubUrl,
      submissionType: mode,
      domain,
      submittedOn: new Date().toISOString().split('T')[0],
      pipelineStatus: 'awaiting_review',
      overallScore: 84,
    };

    // Add to in-memory list
    mockProjects.unshift(newProj as any);

    // Persist so it survives Vite HMR reloads and page refreshes
    const existing = loadPersistedProjects();
    existing.unshift(newProj);
    savePersistedProjects(existing);

    return { projectId };
  }
  const { data } = await apiClient.post('/projects/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};

// ─── Evaluation Report ────────────────────────────────────────────────────────
// CRITICAL: branches on role — student routes NEVER call the internal endpoint
export const getEvaluationReport = async (
  projectId: string,
  role: string
): Promise<PublicEvaluationReport | InternalEvaluationReport> => {
  if (USE_MOCK) {
    await delay();
    const persisted = loadPersistedProjects().find(x => x.projectId === projectId);
    const p = persisted ?? (mockProjects as any[]).find(x => x.projectId === projectId);
    const title = p ? p.title : mockPublicReport.title;
    const domain = p ? (p as any).domain : mockPublicReport.domain;
    const mode = p ? (p as any).submissionType : mockPublicReport.submissionType;
    const isAbstract = mode === 'abstract';

    const overallScore = p && p.overallScore !== null ? p.overallScore : mockPublicReport.overallScore;
    const grade = overallScore >= 90 ? 'A+' : overallScore >= 80 ? 'A' : overallScore >= 70 ? 'B' : 'C';

    const baseReport: PublicEvaluationReport = {
      ...mockPublicReport,
      projectId,
      title,
      domain,
      submissionType: mode,
      overallScore,
      grade,
      dimensionScores: {
        ...mockPublicReport.dimensionScores,
        completeness: isAbstract ? null : mockPublicReport.dimensionScores.completeness,
      },
    };

    if (role === 'student') return baseReport;
    return {
      ...mockInternalReport,
      ...baseReport,
      facultyNotes: [...mockInternalReport.facultyNotes],
    };
  }
  if (role === 'student') {
    const { data } = await apiClient.get<PublicEvaluationReport>(`/projects/${projectId}/report/public`);
    return data;
  }
  const { data } = await apiClient.get<InternalEvaluationReport>(`/projects/${projectId}/report/internal`);
  return data;
};

// ─── AcadEval+ Graph-Based Novelty Engine ─────────────────────────────────────
export const getNoveltyReport = async (projectId: string, abstract: string): Promise<NoveltyReportData> => {
  if (USE_MOCK) {
    await delay(900);
    const persisted = loadPersistedProjects().find(x => x.projectId === projectId);
    const p = persisted ?? (mockProjects as any[]).find(x => x.projectId === projectId || x.id === projectId);
    
    const title = p?.title || 'Academic Capstone Project Proposal';
    const domain = p?.domain || 'Artificial Intelligence';
    const subDomain = (p as any)?.sub_domain || 'Deep Learning';

    // Extract real entities
    const actualAbstract = (p as any)?.abstract || abstract || '';
    const githubUrl = (p as any)?.githubUrl || '';
    const text = `${title}. Domain: ${domain}. ${actualAbstract} ${githubUrl}`;
    const entities = extractEntitiesFromText(title, text);

    // Calculate a stable novelty score based on the title string
    let hash = 0;
    for (let i = 0; i < title.length; i++) {
      hash = (hash << 5) - hash + title.charCodeAt(i);
      hash |= 0;
    }
    const stableScore = 55 + (Math.abs(hash) % 35) + (entities.algorithms.length * 1.5);
    const noveltyScore = Math.min(98, Math.max(40, Math.round(stableScore * 10) / 10));
    
    const noveltyBand = noveltyScore >= 85 ? 'Highly Novel' : 
                        noveltyScore >= 70 ? 'Novel' : 
                        noveltyScore >= 55 ? 'Moderately Novel' : 'Low Novelty';

    // Rarity metrics based on hash
    const graphDistance = parseFloat((0.5 + (Math.abs(hash * 3) % 40) / 100).toFixed(2));
    const featureRarity = parseFloat((0.4 + (Math.abs(hash * 7) % 50) / 100).toFixed(2));
    const relationshipRarity = parseFloat((0.5 + (Math.abs(hash * 11) % 45) / 100).toFixed(2));
    const graphDensity = parseFloat((0.3 + (Math.abs(hash * 13) % 40) / 100).toFixed(2));
    const connectionDiscovery = parseFloat((0.4 + (Math.abs(hash * 17) % 50) / 100).toFixed(2));

    // Pick top similar projects from mock projects in the same domain
    const sameDomain = (mockProjects as any[]).filter(x => x.domain === domain && x.projectId !== projectId).slice(0, 2);
    const similarProjects = sameDomain.map((x, idx) => ({
      project_id: x.projectId,
      title: x.title,
      similarity_score: parseFloat((0.65 - (idx * 0.1)).toFixed(2))
    }));
    
    if (similarProjects.length === 0) {
      similarProjects.push({
        project_id: 'CORPUS-P000412',
        title: `Generic ${domain} Baseline Study`,
        similarity_score: 0.52
      });
    }

    return {
      project_id: projectId,
      title,
      domain,
      sub_domain: subDomain,
      overall_novelty_band: noveltyBand,
      overall_novelty_score: noveltyScore,
      signals_breakdown: {
        graph_distance: graphDistance,
        feature_rarity: featureRarity,
        relationship_rarity: relationshipRarity,
        graph_density: graphDensity,
        new_connection_discovery: connectionDiscovery,
      },
      extracted_entities: entities as any,
      trend_context: {
        topic: entities.applications[0] || title,
        growth_rate_pct: 15 + (Math.abs(hash) % 25),
        paper_count_3yr: 150 + (Math.abs(hash * 2) % 400),
        citation_velocity: parseFloat((8.5 + (Math.abs(hash * 3) % 15)).toFixed(1)),
        trend_status: noveltyScore >= 75 ? 'Hot' : 'Emerging',
        data_source: 'semantic_scholar',
      },
      most_similar_projects: similarProjects,
      explanation_lines: [
        `Graph Distance Signal (${Math.round(graphDistance * 100)}%): Structural separation path from historical project clusters.`,
        `Feature Rarity Signal (${Math.round(featureRarity * 100)}%): Uniqueness of the chosen tools/methods across ${domain}.`,
        `Relationship Rarity Signal (${Math.round(relationshipRarity * 100)}%): Frequency of co-occurrence between the extracted nodes.`,
        `Graph Density Signal (${Math.round(graphDensity * 100)}%): Neighbor node clustering coefficient indicating sparse territory.`,
        `New-Connection Discovery (${Math.round(connectionDiscovery * 100)}%): Adamic-Adar metric indicating novel cross-domain path synthesis.`,
      ],
    };
  }
  const { data } = await apiClient.get<NoveltyReportData>(`/v1/acadeval/report/${projectId}`, {
    params: { abstract },
  });
  return data;
};

export const submitFacultyNoveltyReview = async (
  projectId: string,
  facultyScore: number,
  overrideReason?: string,
  isConfirmed = true
): Promise<void> => {
  if (USE_MOCK) {
    await delay(500);
    return;
  }

  await apiClient.post(
    `/projects/${projectId}/faculty-review`,
    {
      faculty_score: facultyScore,
      override_reason: overrideReason ?? null,
      is_confirmed: isConfirmed,
    }
  );
};
// ─── Review Actions ────────────────────────────────────────────────────────────
export const overrideScore = async (
  projectId: string,
  dimension: string,
  newValue: number,
  comment: string
): Promise<void> => {
  if (USE_MOCK) { await delay(); return; }
  await apiClient.patch(`/projects/${projectId}/scores`, { dimension, newValue, comment });
};

export const addFacultyNote = async (projectId: string, text: string): Promise<void> => {
  if (USE_MOCK) { await delay(); return; }
  await apiClient.post(`/projects/${projectId}/notes`, { text });
};

export const publishReview = async (projectId: string): Promise<void> => {
  if (USE_MOCK) { await delay(); return; }
  await apiClient.post(`/projects/${projectId}/publish`);
};

// ─── Viva ─────────────────────────────────────────────────────────────────────
export const generateVivaQuestions = async (projectId: string): Promise<VivaQuestion[]> => {
  if (USE_MOCK) { await delay(1000); return mockVivaQuestions; }
  const { data } = await apiClient.post<VivaQuestion[]>('/viva/generate', { projectId });
  return data;
};

export const submitVivaAnswer = async (
  sessionId: string,
  questionId: string,
  answer: string
): Promise<VivaAnswerResult> => {
  if (USE_MOCK) { await delay(800); return mockVivaAnswer(questionId, answer); }
  const { data } = await apiClient.post<VivaAnswerResult>('/viva/answer', { sessionId, questionId, answer });
  return data;
};

// ─── Appeals ─────────────────────────────────────────────────────────────────
export const getMyAppeals = async (): Promise<Appeal[]> => {
  if (USE_MOCK) { await delay(); return mockAppeals; }
  const { data } = await apiClient.get<Appeal[]>('/appeals/my');
  return data;
};

export const getAllAppeals = async (): Promise<Appeal[]> => {
  if (USE_MOCK) { await delay(); return mockAppeals; }
  const { data } = await apiClient.get<Appeal[]>('/appeals');
  return data;
};

export const submitAppeal = async (
  projectId: string,
  dimension: string,
  justification: string
): Promise<{ appealId: string }> => {
  if (USE_MOCK) { await delay(); return { appealId: `ap_${Date.now()}` }; }
  const { data } = await apiClient.post('/appeals', { projectId, dimension, justification });
  return data;
};

export const resolveAppeal = async (
  appealId: string,
  action: 'approve' | 'reject' | 'override',
  newScore?: number,
  response?: string
): Promise<void> => {
  if (USE_MOCK) { await delay(); return; }
  await apiClient.patch(`/appeals/${appealId}`, { action, newScore, response });
};

// ─── Rubrics ─────────────────────────────────────────────────────────────────
export const getRubrics = async (): Promise<Rubric[]> => {
  if (USE_MOCK) { await delay(); return [mockRubric]; }
  const { data } = await apiClient.get<Rubric[]>('/rubrics');
  return data;
};

export const createRubric = async (rubric: Omit<Rubric, 'rubricId' | 'createdAt'>): Promise<Rubric> => {
  if (USE_MOCK) { await delay(); return { ...rubric, rubricId: `r_${Date.now()}`, createdAt: new Date().toISOString() }; }
  const { data } = await apiClient.post<Rubric>('/rubrics', rubric);
  return data;
};

export const approveRubric = async (rubricId: string): Promise<void> => {
  if (USE_MOCK) { await delay(); return; }
  await apiClient.post(`/rubrics/${rubricId}/approve`);
};

// ─── Leaderboard ─────────────────────────────────────────────────────────────
export const getLeaderboard = async (): Promise<LeaderboardEntry[]> => {
  if (USE_MOCK) { await delay(); return mockLeaderboard; }
  const { data } = await apiClient.get<LeaderboardEntry[]>('/leaderboard');
  return data;
};

// ─── Batch Upload ─────────────────────────────────────────────────────────────
export const uploadBatch = async (formData: FormData): Promise<{ batchId: string }> => {
  if (USE_MOCK) { await delay(1500); return { batchId: `batch_${Date.now()}` }; }
  const { data } = await apiClient.post('/projects/batch', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};

export const getBatchStatus = async (batchId: string): Promise<BatchJobStatus> => {
  if (USE_MOCK) {
    await delay(400);
    return {
      batchId,
      totalFiles: 12,
      processed: Math.min(12, Math.floor(Date.now() / 1000) % 13),
      failed: 0,
      status: 'processing',
      startedAt: new Date().toISOString(),
      projects: mockProjects,
    };
  }
  const { data } = await apiClient.get<BatchJobStatus>(`/batch/${batchId}/status`);
  return data;
};

// ─── Benchmarking ────────────────────────────────────────────────────────────
export const getBenchmarks = async (): Promise<SemesterBenchmark[]> => {
  if (USE_MOCK) { await delay(); return mockBenchmarks; }
  const { data } = await apiClient.get<SemesterBenchmark[]>('/benchmarks');
  return data;
};

// ─── Faculty Dashboard ────────────────────────────────────────────────────────
export const getFacultyDashboard = async (): Promise<FacultyDashboardStats> => {
  if (USE_MOCK) { await delay(); return mockFacultyDashboard; }
  const { data } = await apiClient.get<FacultyDashboardStats>('/dashboard/faculty');
  return data;
};

// ─── HOD ─────────────────────────────────────────────────────────────────────
export const getHODStats = async (): Promise<HODDeptStats> => {
  if (USE_MOCK) { await delay(); return mockHODStats; }
  const { data } = await apiClient.get<HODDeptStats>('/dashboard/hod');
  return data;
};

export const getUsers = async (): Promise<User[]> => {
  if (USE_MOCK) {
    await delay();
    return [...mockUsers.students, ...mockUsers.faculty, ...mockUsers.hod];
  }
  const { data } = await apiClient.get<User[]>('/users');
  return data;
};

export const updateUserRole = async (userId: string, role: string): Promise<void> => {
  if (USE_MOCK) { await delay(); return; }
  await apiClient.patch(`/users/${userId}`, { role });
};

// ─── Module 3 \u2014 Entity Knowledge Base & Pending Review ─────────────────────────

export const getKnowledgeBase = async (params?: {
  category?: string; search?: string; limit?: number; offset?: number;
}) => {
  if (USE_MOCK) {
    await delay(400);
    // Return a handful of mock KB entries
    const mockKB = [
      { name: 'CNN', category: 'algorithm', aliases: ['Convolutional Neural Network', 'ConvNet'], first_seen_year: 1989 },
      { name: 'YOLO', category: 'algorithm', aliases: ['You Only Look Once'], first_seen_year: 2015 },
      { name: 'TensorFlow', category: 'framework', aliases: ['TF'], first_seen_year: 2015 },
      { name: 'PyTorch', category: 'framework', aliases: [], first_seen_year: 2016 },
      { name: 'COCO', category: 'dataset', aliases: ['MS COCO'], first_seen_year: 2014 },
      { name: 'Raspberry Pi', category: 'hardware', aliases: ['RPi'], first_seen_year: 2012 },
      { name: 'F1-Score', category: 'metric', aliases: ['F1', 'F-measure'], first_seen_year: 1992 },
    ];
    const filtered = mockKB.filter(e =>
      (!params?.category || e.category === params.category) &&
      (!params?.search || e.name.toLowerCase().includes(params.search.toLowerCase()))
    );
    return { total: filtered.length, offset: 0, limit: 100, entries: filtered };
  }
  const { data } = await apiClient.get('/entities/knowledge-base', { params });
  return data;
};

export const extractEntitiesFromText = (title: string, text: string) => {
  const fullText = (title + " " + text).toLowerCase();

  const rules: { cat: string; terms: string[] }[] = [
    { cat: 'algorithms', terms: ['Quantum Neural Network', 'QNN', 'Parameterized Quantum Circuits', 'YOLOv8', 'YOLO', 'ResNet-50', 'ResNet', 'CNN', 'SVM', 'Random Forest', 'Vision Transformer', 'Transformer', 'BERT', 'FastRP', 'Adamic-Adar', 'Graph Neural Network', 'GCN', 'Federated Learning', 'LSTM', 'GRU', 'XGBoost', 'LightGBM', 'Autoencoder', '3D U-Net', 'FaceNet', 'Support Vector Machines'] },
    { cat: 'technologies', terms: ['Qiskit', 'Pennylane', 'Edge Computing', 'GraphQL', 'REST API', 'WebSockets', 'Neo4j', 'PostgreSQL', 'SQLite', 'Docker', 'Kubernetes', 'FastAPI', 'Vite', 'React', 'TypeScript', 'Node.js', 'Redis', 'Kafka', 'Alembic', 'SQLAlchemy'] },
    { cat: 'frameworks', terms: ['PyTorch', 'TensorFlow', 'Keras', 'Scikit-Learn', 'NetworkX', 'spaCy', 'HuggingFace', 'TailwindCSS', 'Celery'] },
    { cat: 'libraries', terms: ['OpenCV', 'NumPy', 'Pandas', 'Matplotlib', 'Seaborn', 'Sentence-Transformers', 'fitz', 'PyMuPDF', 'python-docx', 'python-pptx'] },
    { cat: 'datasets', terms: ['OpenBCI Dataset', 'OpenBCI', 'WikiText-103', 'WikiText103', 'LibriSpeech', 'Librispeech', 'CelebA', 'Cityscapes', 'LFW', 'Labeled Faces in the Wild', 'IMDb Movie Reviews', 'IMDb Reviews', 'AG News', 'AGNews', 'DBpedia', 'ADE20K', 'Pascal VOC', 'VOC2012', 'Yelp Reviews', 'Yelp Academic Dataset', 'WordNet', 'ESC-50', 'FSD50K', 'UrbanSound8K', 'MovieLens', 'DailyDialog', 'Cornell Movie-Dialogs', 'Penn Treebank', 'Sentiment140', 'Common Voice', 'Waymo Open Dataset', 'Waymo Perception Dataset', 'Bot-IoT', 'WMT14', 'Multi30K', 'PubMedQA', 'MedQA', 'CheXpert', 'CASIA-WebFace', 'DeepFashion', 'ShapeNet', 'ModelNet40', 'ScanNet', 'NSL-KDD', 'NSL KDD', 'KDD Cup 99', 'COCO', 'ImageNet', 'KITTI', 'BraTS 2021', 'BraTS', 'PlantVillage', 'MNIST', 'CIFAR-10', 'CIFAR-100', 'AcadEval_FeatureKnowledgeBase', 'Semantic Scholar'] },
    { cat: 'applications', terms: ['Network Intrusion Detection', 'NIDPS', 'Cyber Security Threat Detection', 'Academic Evaluation', 'Autonomous Driving', 'Medical Diagnosis', 'Scam Website Classification', 'Herb Traceability', 'Dysgraphia Detection', 'Kabaddi Midline Crossing', 'Thyroid Classification', 'Oncology Diagnostics'] },
    { cat: 'hardware', terms: ['IBM Quantum Falcon', 'Quantum Processor', 'NVIDIA RTX 4090', 'Raspberry Pi', 'Jetson Nano', 'NVIDIA GPU', 'CUDA', 'Coral TPU'] },
    { cat: 'metrics', terms: ['Accuracy', 'F1-Score', 'Precision', 'Recall', 'mAP', 'FPS', 'Dice Score', 'Cosine Similarity', 'Graph Distance', 'Clustering Coefficient', 'Quantum Circuit Depth'] },
  ];

  const res: Record<string, string[]> = {
    algorithms: [], technologies: [], frameworks: [], libraries: [],
    datasets: [], applications: [], hardware: [], metrics: []
  };

  rules.forEach(({ cat, terms }) => {
    terms.forEach(term => {
      if (fullText.includes(term.toLowerCase())) {
        if (!res[cat].includes(term)) {
          res[cat].push(term);
        }
      }
    });
  });

  // Dynamic fallback for unmatched terms
  if (res.algorithms.length === 0) {
    if (title.toLowerCase().includes('quantum')) res.algorithms.push('Quantum Neural Network', 'QNN');
    else if (title.toLowerCase().includes('graph') || title.toLowerCase().includes('novelty')) res.algorithms.push('Graph Neural Network', 'FastRP');
    else if (title.toLowerCase().includes('vision') || title.toLowerCase().includes('image')) res.algorithms.push('YOLOv8', 'CNN');
    else if (title.toLowerCase().includes('text') || title.toLowerCase().includes('nlp')) res.algorithms.push('Transformer', 'BERT');
    else res.algorithms.push('Deep Neural Network');
  }

  if (res.technologies.length === 0) res.technologies.push('FastAPI', 'PostgreSQL');
  if (res.frameworks.length === 0) res.frameworks.push('PyTorch');
  if (res.libraries.length === 0) res.libraries.push('NumPy', 'spaCy');
  if (res.datasets.length === 0) res.datasets.push('Custom Benchmark Dataset');
  if (res.applications.length === 0) res.applications.push(title || 'Capstone Project System');
  if (res.hardware.length === 0) res.hardware.push('NVIDIA GPU');
  if (res.metrics.length === 0) res.metrics.push('Accuracy', 'F1-Score');

  return res;
};

export const getProjectEntities = async (projectId: string) => {
  if (USE_MOCK) {
    await delay(300);
    // Prefer persisted data (has abstract + githubUrl) over in-memory mockProjects
    const persisted = loadPersistedProjects().find(x => x.projectId === projectId);
    const p = persisted ?? (mockProjects as any[]).find(x => x.projectId === projectId || x.id === projectId);
    const title = p?.title || 'Academic Capstone Project Proposal';
    const abstract = (p as any)?.abstract || '';
    const githubUrl = (p as any)?.githubUrl || '';
    const text = `${title}. Domain: ${(p as any)?.domain || ''}. ${abstract} ${githubUrl}`;
    return {
      project_id: projectId,
      title,
      extracted_entities: extractEntitiesFromText(title, text),
      has_been_extracted: true,
    };
  }
  const { data } = await apiClient.get(`/entities/project/${projectId}`);
  return data;
};

export const getPendingReviewEntities = async () => {
  if (USE_MOCK) {
    await delay(300);
    return {
      total: 2,
      items: [
        { name: 'EfficientDet', category: 'algorithm', source_project_id: 'mock-proj-001' },
        { name: 'Coral Edge TPU', category: 'hardware', source_project_id: 'mock-proj-002' },
      ],
    };
  }
  const { data } = await apiClient.get('/entities/pending-review');
  return data;
};

export const approveEntityReview = async (name: string, payload: object) => {
  if (USE_MOCK) { await delay(500); return { status: 'approved', entry: { name }, pending_remaining: 1 }; }
  const { data } = await apiClient.post(`/entities/pending-review/${encodeURIComponent(name)}/approve`, payload);
  return data;
};

export const rejectEntityReview = async (name: string) => {
  if (USE_MOCK) { await delay(300); return { status: 'rejected', removed: name, pending_remaining: 1 }; }
  const { data } = await apiClient.post(`/entities/pending-review/${encodeURIComponent(name)}/reject`);
  return data;
};

// ─── Module 4 Knowledge Graph ────────────────────────────────────────────────
// Helper to build a dynamic interconnected project knowledge graph for mock mode
const buildDynamicMockGraph = () => {
  const projects = [
    ...mockProjects,
    ...loadPersistedProjects()
  ];

  const nodesMap = new Map<string, { name: string; type: string; degree: number }>();
  const rawLinks: { sourceKey: string; targetKey: string; relationship: string; confidence?: number }[] = [];

  // Helper to register node
  const registerNode = (key: string, name: string, type: string) => {
    if (!nodesMap.has(key)) {
      nodesMap.set(key, { name, type, degree: 0 });
    }
  };

  // Helper to register link
  const registerLink = (sourceKey: string, targetKey: string, relationship: string, confidence = 1.0) => {
    rawLinks.push({ sourceKey, targetKey, relationship, confidence });
    // Increment degrees
    const s = nodesMap.get(sourceKey);
    if (s) s.degree++;
    const t = nodesMap.get(targetKey);
    if (t) t.degree++;
  };

  projects.forEach((p: any) => {
    const projKey = `P_${p.projectId}`;
    registerNode(projKey, p.title, 'Project');

    // Domain
    if (p.domain) {
      const domKey = `D_${p.domain}`;
      registerNode(domKey, p.domain, 'Domain');
      registerLink(projKey, domKey, 'HAS_DOMAIN');
    }

    // Dynamic Entity Extraction
    const abstractText = p.abstract || '';
    const text = `${p.title}. ${abstractText}`;
    const entities = extractEntitiesFromText(p.title, text);

    const catMap: { list: string[]; type: string; rel: string }[] = [
      { list: entities.algorithms || [], type: 'Algorithm', rel: 'USES_ALGORITHM' },
      { list: entities.technologies || [], type: 'Technology', rel: 'USES_TECHNOLOGY' },
      { list: entities.frameworks || [], type: 'Framework', rel: 'USES_FRAMEWORK' },
      { list: entities.libraries || [], type: 'Library', rel: 'USES_LIBRARY' },
      { list: entities.datasets || [], type: 'Dataset', rel: 'USES_DATASET' },
      { list: entities.applications || [], type: 'Application', rel: 'TARGETS_APPLICATION' },
      { list: entities.hardware || [], type: 'Hardware', rel: 'RUNS_ON' },
      { list: entities.metrics || [], type: 'Metric', rel: 'EVALUATED_BY' },
    ];

    const projectEntityKeys: string[] = [];

    catMap.forEach(({ list, type, rel }) => {
      list.forEach(name => {
        if (!name) return;
        const entKey = `E_${type}_${name.toLowerCase().trim()}`;
        registerNode(entKey, name, type);
        registerLink(projKey, entKey, rel);
        projectEntityKeys.push(entKey);
      });
    });

    // Add some CO_OCCURS links between entities in this project
    for (let i = 0; i < projectEntityKeys.length; i++) {
      for (let j = i + 1; j < Math.min(projectEntityKeys.length, i + 3); j++) {
        registerLink(projectEntityKeys[i], projectEntityKeys[j], 'CO_OCCURS', 0.8);
      }
    }
  });

  // Assign numeric IDs to each unique node key
  const keyToId = new Map<string, number>();
  let nextId = 1;
  const nodes: any[] = [];

  nodesMap.forEach((val, key) => {
    const id = nextId++;
    keyToId.set(key, id);
    nodes.push({
      id,
      name: val.name,
      type: val.type,
      degree: val.degree
    });
  });

  // Map links to numeric IDs
  const links = rawLinks.map(l => ({
    source: keyToId.get(l.sourceKey)!,
    target: keyToId.get(l.targetKey)!,
    relationship: l.relationship,
    confidence: l.confidence
  })).filter(l => l.source !== undefined && l.target !== undefined);

  return { nodes, links };
};

export const getGraphSummary = async (refresh = false) => {
  if (USE_MOCK) {
    await delay(300);
    const { nodes, links } = buildDynamicMockGraph();
    
    // Count distribution
    const nodeDist: Record<string, number> = {};
    nodes.forEach(n => {
      nodeDist[n.type] = (nodeDist[n.type] || 0) + 1;
    });

    const relDist: Record<string, number> = {};
    links.forEach(l => {
      relDist[l.relationship] = (relDist[l.relationship] || 0) + 1;
    });

    // Top central nodes based on degree
    const topCentrality = [...nodes]
      .sort((a, b) => b.degree - a.degree)
      .slice(0, 5)
      .map(n => ({
        id: n.id,
        name: n.name,
        type: n.type,
        degree: n.degree,
        centrality_score: parseFloat((n.degree / Math.max(1, links.length)).toFixed(3))
      }));

    return {
      status: 'ok',
      metrics: {
        nodes_count: nodes.length,
        edges_count: links.length,
        density: parseFloat((links.length / (nodes.length * (nodes.length - 1) || 1)).toFixed(4)),
        node_type_distribution: nodeDist,
        relationship_distribution: relDist,
        top_centrality_nodes: topCentrality,
      },
    };
  }
  const { data } = await apiClient.get(`/graph/summary${refresh ? '?refresh=true' : ''}`);
  return data;
};

export const getGraphVisualization = async (limit = 300, nodeTypes?: string) => {
  if (USE_MOCK) {
    await delay(400);
    const { nodes, links } = buildDynamicMockGraph();
    return {
      status: 'ok',
      total_graph_nodes: nodes.length,
      total_graph_edges: links.length,
      returned_nodes: nodes.length,
      returned_links: links.length,
      nodes,
      links,
    };
  }
  const params = new URLSearchParams();
  if (limit) params.append('limit', limit.toString());
  if (nodeTypes) params.append('node_types', nodeTypes);
  const { data } = await apiClient.get(`/graph/visualization?${params.toString()}`);
  return data;
};

export const getNodeNeighborhood = async (query: string, radius = 1) => {
  if (USE_MOCK) {
    await delay(300);
    const { nodes, links } = buildDynamicMockGraph();
    
    // Find target node
    const qLower = query.toLowerCase();
    const targetNode = nodes.find(n => n.name.toLowerCase().includes(qLower));
    
    if (!targetNode) {
      return {
        status: 'error',
        message: `Node '${query}' not found in mock graph.`
      };
    }

    // Simple BFS to find neighborhood nodes within radius
    const visited = new Set<number>([targetNode.id]);
    let currentLevel = new Set<number>([targetNode.id]);

    for (let r = 0; r < radius; r++) {
      const nextLevel = new Set<number>();
      links.forEach(l => {
        const s = typeof l.source === 'object' ? (l.source as any).id : l.source;
        const t = typeof l.target === 'object' ? (l.target as any).id : l.target;
        if (currentLevel.has(s) && !visited.has(t)) {
          nextLevel.add(t);
          visited.add(t);
        }
        if (currentLevel.has(t) && !visited.has(s)) {
          nextLevel.add(s);
          visited.add(s);
        }
      });
      currentLevel = nextLevel;
    }

    const neighborhoodNodes = nodes.filter(n => visited.has(n.id));
    const neighborhoodLinks = links.filter(l => {
      const s = typeof l.source === 'object' ? (l.source as any).id : l.source;
      const t = typeof l.target === 'object' ? (l.target as any).id : l.target;
      return visited.has(s) && visited.has(t);
    });

    return {
      status: 'ok',
      target_node: targetNode,
      radius,
      neighborhood_nodes: neighborhoodNodes.length,
      graph: {
        nodes: neighborhoodNodes,
        links: neighborhoodLinks
      }
    };
  }
  const { data } = await apiClient.get(`/graph/node/${encodeURIComponent(query)}?radius=${radius}`);
  return data;
};

export const rebuildKnowledgeGraph = async () => {
  if (USE_MOCK) {
    await delay(600);
    const { nodes, links } = buildDynamicMockGraph();
    const projects = [
      ...mockProjects,
      ...loadPersistedProjects()
    ];
    return {
      status: 'rebuilt',
      result: {
        projects_processed: projects.length,
        relational_nodes: nodes.length,
        relational_edges: links.length
      }
    };
  }
  const { data } = await apiClient.post('/graph/rebuild');
  return data;
};

