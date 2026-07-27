import type {
  ProjectSummary,
  PublicEvaluationReport,
  InternalEvaluationReport,
  LeaderboardEntry,
  VivaQuestion,
  VivaAnswerResult,
  Appeal,
  Rubric,
  BatchJobStatus,
  SemesterBenchmark,
  FacultyDashboardStats,
  HODDeptStats,
  User,
  ActivityItem,
} from '../types';
import type { NoveltyReportData } from '../components/NoveltyReportView';

// ─── Mock Users ───────────────────────────────────────────────────────────────
export const mockUsers: Record<string, User[]> = {
  students: [
    { userId: 'u001', name: 'Priya Sharma', email: 'priya@college.edu', rollNo: 'CS2021001', role: 'student', department: 'CSE', isActive: true, joinedAt: '2021-07-01' },
    { userId: 'u002', name: 'Arjun Patel', email: 'arjun@college.edu', rollNo: 'CS2021002', role: 'student', department: 'CSE', isActive: true, joinedAt: '2021-07-01' },
    { userId: 'u003', name: 'Sneha Reddy', email: 'sneha@college.edu', rollNo: 'CS2021003', role: 'student', department: 'CSE', isActive: true, joinedAt: '2021-07-01' },
    { userId: 'u004', name: 'Rahul Singh', email: 'rahul@college.edu', rollNo: 'CS2021004', role: 'student', department: 'CSE', isActive: true, joinedAt: '2021-07-01' },
  ],
  faculty: [
    { userId: 'f001', name: 'Dr. Meera Krishnan', email: 'meera@college.edu', role: 'guide', department: 'CSE', isActive: true, joinedAt: '2015-06-01' },
    { userId: 'f002', name: 'Prof. Suresh Rajan', email: 'suresh@college.edu', role: 'reviewer', department: 'CSE', isActive: true, joinedAt: '2018-06-01' },
  ],
  hod: [
    { userId: 'h001', name: 'Dr. Anand Krishnamurthy', email: 'hod@college.edu', role: 'hod', department: 'CSE', isActive: true, joinedAt: '2010-06-01' },
  ],
};

// ─── Mock Projects ────────────────────────────────────────────────────────────
export const mockProjects: ProjectSummary[] = [
  {
    projectId: 'p001',
    studentName: 'Priya Sharma',
    rollNo: 'CS2021001',
    title: 'AI-Powered Crop Disease Detection Using Deep Learning',
    submissionType: 'document',
    domain: 'AI/ML',
    submittedOn: '2025-03-10',
    pipelineStatus: 'reviewed',
    overallScore: 84,
  },
  {
    projectId: 'p002',
    studentName: 'Priya Sharma',
    rollNo: 'CS2021001',
    title: 'Smart Irrigation System with IoT Sensors',
    submissionType: 'abstract',
    domain: 'IoT',
    submittedOn: '2025-04-01',
    pipelineStatus: 'awaiting_review',
    overallScore: 71,
  },
  {
    projectId: 'p003',
    studentName: 'Arjun Patel',
    rollNo: 'CS2021002',
    title: 'Blockchain-Based Academic Credential Verification',
    submissionType: 'document',
    domain: 'Web/App',
    submittedOn: '2025-03-15',
    pipelineStatus: 'reviewed',
    overallScore: 76,
  },
  {
    projectId: 'p004',
    studentName: 'Sneha Reddy',
    rollNo: 'CS2021003',
    title: 'Real-Time Sign Language Recognition Using CNN',
    submissionType: 'video',
    domain: 'AI/ML',
    submittedOn: '2025-03-20',
    pipelineStatus: 'ai_processing',
    overallScore: null,
  },
  {
    projectId: 'p005',
    studentName: 'Rahul Singh',
    rollNo: 'CS2021004',
    title: 'Federated Learning for Privacy-Preserving Healthcare',
    submissionType: 'document',
    domain: 'Healthcare',
    submittedOn: '2025-03-22',
    pipelineStatus: 'reviewed',
    overallScore: 91,
  },
];

// ─── Mock Public Evaluation Report ────────────────────────────────────────────
export const mockPublicReport: PublicEvaluationReport = {
  projectId: 'p001',
  title: 'AI-Powered Crop Disease Detection Using Deep Learning',
  domain: 'AI/ML',
  submissionType: 'document',
  pipelineStatus: 'reviewed',
  isPreliminary: false,
  overallScore: 84,
  grade: 'A',
  dimensionScores: {
    novelty: 82,
    feasibility: 88,
    completeness: 79,
    technicalDepth: 85,
    clarity: 83,
    similarityRisk: 76,
    publicationPotential: 80,
  },
  missingSections: ['Future Scope', 'Limitations'],
  similarity: {
    internalScore: 18,
    externalScore: 22,
    isDuplicate: false,
  },
  feasibilityRating: 'High',
  noveltyVerdict: 'Novel',
  writingQuality: {
    readability: 72,
    passiveVoiceCount: 14,
    toneFlags: ['Informal phrasing in Section 3.2', 'Overly casual Abstract'],
  },
  citations: {
    ieeeCompliancePercent: 86,
    missingReferences: ['[12] URL-only citation', '[17] No publication year'],
  },
  strengths: [
    'Strong literature review covering recent CNN architectures',
    'Dataset is well-curated with 12,000+ labeled disease images',
    'Clear experimental methodology with ablation studies',
    'Results benchmarked against 4 state-of-the-art models',
    'Practical deployment consideration with mobile-friendly model',
  ],
  weaknesses: [
    'Future Scope section entirely missing',
    'Limitations of the proposed model not discussed',
    'Two citations are URL-only without proper IEEE formatting',
    'Passive voice overuse in Methodology section reduces clarity',
  ],
  improvementRoadmap: [
    {
      week: 1,
      focus: 'Complete Missing Sections',
      actions: ['Write a 400-word Future Scope section covering multi-crop support', 'Add a Limitations subsection discussing dataset geographic bias'],
    },
    {
      week: 2,
      focus: 'Fix Citations & References',
      actions: ['Convert URL-only references [12] and [17] to IEEE format', 'Verify all 23 references against the IEEE citation checker'],
    },
    {
      week: 3,
      focus: 'Writing Quality Improvement',
      actions: ['Rewrite Methodology in active voice', 'Remove informal phrases from Abstract and Section 3.2'],
    },
    {
      week: 4,
      focus: 'Final Polish & Submission',
      actions: ['Peer review with a classmate', 'Run Grammarly pass on full document', 'Submit revised version for re-evaluation'],
    },
  ],
  badges: ['Novel Idea Award', 'High Feasibility', 'Top 15% Novelty 2025'],
  percentileRanks: {
    novelty: 85,
    feasibility: 91,
    completeness: 67,
    technicalDepth: 88,
    clarity: 75,
    overall: 82,
  },
};

// ─── Mock Internal Report (Faculty-only) ─────────────────────────────────────
export const mockInternalReport: InternalEvaluationReport = {
  ...mockPublicReport,
  facultyNotes: [
    {
      author: 'Dr. Meera Krishnan',
      role: 'guide',
      text: 'Student made significant improvements after the mid-semester feedback. Dataset quality is excellent.',
      timestamp: '2025-04-10T09:30:00Z',
    },
    {
      author: 'Prof. Suresh Rajan',
      role: 'reviewer',
      text: 'Minor concern: the model accuracy claims need to be verified against a separate test split. Overall solid work.',
      timestamp: '2025-04-12T14:15:00Z',
    },
  ],
  explainability: {
  explainer_mode: 'weighted_signal_analysis',
  composite_novelty_score: 84,
  novelty_band: 'High Novelty',
  overall_summary:
    'The project demonstrates strong novelty through real-world validation, measurable performance improvements, and practical agricultural relevance. The main limitation is the use of an existing model architecture without significant modification.',
  signals: [
    {
      signal_key: 'performance_claim',
      signal_name: 'Quantified Performance',
      raw_value: 97.3,
      weight: 0.92,
      weighted_contribution: 18.4,
      max_possible_contribution: 20,
      percentage_of_max: 92,
      explanation:
        'The reported 97.3% accuracy provides a strong measurable result and positively contributes to the novelty assessment.',
    },
    {
      signal_key: 'architecture_novelty',
      signal_name: 'Architecture Novelty',
      raw_value: 0.46,
      weight: 0.54,
      weighted_contribution: 5.4,
      max_possible_contribution: 10,
      percentage_of_max: 54,
      explanation:
        'The project uses a standard ResNet architecture with limited modification, reducing the architecture-level novelty contribution.',
    },
    {
      signal_key: 'real_world_validation',
      signal_name: 'Real-World Validation',
      raw_value: 0.78,
      weight: 0.78,
      weighted_contribution: 15.6,
      max_possible_contribution: 20,
      percentage_of_max: 78,
      explanation:
        'Testing under real farm conditions strengthens the practical relevance and feasibility of the proposed solution.',
    },
    {
      signal_key: 'future_scope',
      signal_name: 'Future Scope Quality',
      raw_value: 0.29,
      weight: 0.71,
      weighted_contribution: 2.9,
      max_possible_contribution: 10,
      percentage_of_max: 29,
      explanation:
        'The future work statement is too general and does not describe specific technical improvements or research directions.',
    },
    {
      signal_key: 'baseline_comparison',
      signal_name: 'Baseline Comparison',
      raw_value: 0.65,
      weight: 0.65,
      weighted_contribution: 13,
      max_possible_contribution: 20,
      percentage_of_max: 65,
      explanation:
        'The comparison against baseline models supports the technical depth of the evaluation, although more detailed evidence would improve confidence.',
    },
  ],
},
  flaggingReasons: [],
  assignedGuide: 'Dr. Meera Krishnan',
  assignedReviewer: 'Prof. Suresh Rajan',
  scoreOverrideHistory: [
    {
      dimension: 'clarity',
      oldValue: 79,
      newValue: 83,
      by: 'Dr. Meera Krishnan',
      comment: 'Revised after student corrected passive voice issues in the revision.',
      timestamp: '2025-04-10T10:00:00Z',
    },
  ],
};

// ─── Mock Leaderboard ─────────────────────────────────────────────────────────
export const mockLeaderboard: LeaderboardEntry[] = [
  { rank: 1, studentName: 'Rahul Singh', rollNo: 'CS2021004', projectTitle: 'Federated Learning for Privacy-Preserving Healthcare', domain: 'Healthcare', overallScore: 91, badges: ['Publication Ready', 'Novel Idea Award', 'Top Scorer 2025'] },
  { rank: 2, studentName: 'Priya Sharma', rollNo: 'CS2021001', projectTitle: 'AI-Powered Crop Disease Detection', domain: 'AI/ML', overallScore: 84, badges: ['Novel Idea Award', 'High Feasibility'], isCurrentUser: true },
  { rank: 3, studentName: 'Arjun Patel', rollNo: 'CS2021002', projectTitle: 'Blockchain Academic Credential Verification', domain: 'Web/App', overallScore: 76, badges: ['Most Improved'] },
  { rank: 4, studentName: 'Sneha Reddy', rollNo: 'CS2021003', projectTitle: 'Real-Time Sign Language Recognition Using CNN', domain: 'AI/ML', overallScore: 68, badges: [] },
  { rank: 5, studentName: 'Kiran Verma', rollNo: 'CS2021005', projectTitle: 'Smart Energy Management using Reinforcement Learning', domain: 'AI/ML', overallScore: 67, badges: [] },
  { rank: 6, studentName: 'Divya Nair', rollNo: 'CS2021006', projectTitle: 'NLP-Based Mental Health Chatbot', domain: 'AI/ML', overallScore: 65, badges: [] },
  { rank: 7, studentName: 'Mohan Kumar', rollNo: 'CS2021007', projectTitle: 'Automated Traffic Management Using Computer Vision', domain: 'AI/ML', overallScore: 62, badges: [] },
  { rank: 8, studentName: 'Ananya Roy', rollNo: 'CS2021008', projectTitle: 'Voice Controlled Smart Home IoT', domain: 'IoT', overallScore: 59, badges: [] },
];

// ─── Mock Viva Questions ──────────────────────────────────────────────────────
export const mockVivaQuestions: VivaQuestion[] = [
  { questionId: 'vq1', text: 'Can you explain the architecture of the CNN model you used? Why did you choose this architecture over alternatives like VGG or EfficientNet?', category: 'Technical', difficulty: 'Medium' },
  { questionId: 'vq2', text: 'How did you handle class imbalance in the PlantVillage dataset?', category: 'Methodology', difficulty: 'Hard' },
  { questionId: 'vq3', text: 'What is transfer learning, and how have you applied it in your project?', category: 'Technical', difficulty: 'Easy' },
  { questionId: 'vq4', text: 'How would your system perform in low-bandwidth field conditions where image quality is poor?', category: 'Practical', difficulty: 'Hard' },
  { questionId: 'vq5', text: 'Explain the difference between precision and recall in the context of disease detection. Which metric matters more for your application?', category: 'Evaluation', difficulty: 'Medium' },
  { questionId: 'vq6', text: 'What are the limitations of your current approach and what future improvements do you propose?', category: 'Critical Thinking', difficulty: 'Easy' },
  { questionId: 'vq7', text: 'How does your system compare to existing mobile apps like Plantix or AgriBot?', category: 'Novelty', difficulty: 'Medium' },
  { questionId: 'vq8', text: 'Walk me through your data preprocessing pipeline — what augmentation techniques did you use and why?', category: 'Methodology', difficulty: 'Medium' },
  { questionId: 'vq9', text: 'If you had to deploy this system in a production environment, what infrastructure would you need?', category: 'Practical', difficulty: 'Hard' },
  { questionId: 'vq10', text: 'Explain overfitting. How did you detect and prevent it in your model training?', category: 'Technical', difficulty: 'Easy' },
];

export const mockVivaAnswer = (questionId: string, _answer: string): VivaAnswerResult => ({
  questionId,
  score: Math.floor(Math.random() * 3) + 2 as 2 | 3 | 4,
  maxScore: 5,
  feedback: 'Good explanation of the core concept. Could include more specific examples from your project implementation to strengthen the answer.',
  keyPoints: ['Mentioned correct architecture components', 'Could elaborate on training specifics'],
});

// ─── Mock Novelty Report (AcadEval+ graph engine) ─────────────────────────────
export const mockNoveltyReport = (projectId: string): NoveltyReportData => ({
  project_id: projectId,
  title: mockPublicReport.title,
  domain: mockPublicReport.domain,
  sub_domain: 'Computer Vision',
  overall_novelty_band: 'Moderately Novel',
  overall_novelty_score: 62.4,
  signals_breakdown: {
    graph_distance: 0.61,
    feature_rarity: 0.54,
    relationship_rarity: 0.72,
    graph_density: 0.58,
    new_connection_discovery: 0.65,
  },
  extracted_entities: {
    algorithms: ['CNN', 'Vision Transformer'],
    technologies: ['Edge Computing'],
    frameworks: ['PyTorch'],
    libraries: ['OpenCV'],
    datasets: ['PlantVillage'],
    applications: ['Plant Disease Detection'],
    hardware: [],
  },
  trend_context: {
    topic: 'Plant Disease Detection',
    growth_rate_pct: 24.5,
    paper_count_3yr: 450,
    citation_velocity: 12.8,
    trend_status: 'Emerging',
    data_source: 'semantic_scholar',
  },
  most_similar_projects: [
    { project_id: 'CORPUS-P000412', title: 'CNN-Based Leaf Disease Classifier', similarity_score: 0.71 },
    { project_id: 'CORPUS-P000198', title: 'Mobile Plant Health Monitoring App', similarity_score: 0.58 },
  ],
  explanation_lines: [
    'Graph Distance Signal (61.0%, via fastrp): Measures structural separation from historical project proposals.',
    'Feature Rarity Signal (54.0%): Assesses how unique the selected algorithms/technologies are across the corpus.',
    'Relationship Rarity Signal (72.0%): Checks how rarely these specific entity pairs co-occur.',
    'Graph Density Signal (58.0%, via gds_clustering_coefficient): Evaluates domain neighborhood sparsity.',
    'New-Connection Discovery (65.0%): Adamic-Adar metric indicating novel cross-domain feature synthesis.',
  ],
});

// ─── Mock Appeals ─────────────────────────────────────────────────────────────
export const mockAppeals: Appeal[] = [
  {
    appealId: 'ap001',
    projectId: 'p001',
    projectTitle: 'AI-Powered Crop Disease Detection',
    dimension: 'completeness',
    originalScore: 79,
    studentJustification: 'The Future Scope section was present in the submitted document on pages 24–25. I believe it was not parsed correctly by the AI system.',
    status: 'under_review',
    createdAt: '2025-04-15T10:00:00Z',
  },
];

// ─── Mock Faculty Dashboard ────────────────────────────────────────────────────
export const mockFacultyDashboard: FacultyDashboardStats = {
  totalSubmissions: 24,
  pendingReview: 7,
  flaggedDuplicates: 2,
  avgScoreThisSemester: 73.4,
  recentActivity: [
    { id: 'a1', type: 'submitted', studentName: 'Sneha Reddy', projectTitle: 'Sign Language Recognition', timestamp: '2025-04-14T08:30:00Z', details: 'Video submission uploaded' },
    { id: 'a2', type: 'reviewed', studentName: 'Priya Sharma', projectTitle: 'Crop Disease Detection', timestamp: '2025-04-12T15:00:00Z', details: 'Review published' },
    { id: 'a3', type: 'appealed', studentName: 'Priya Sharma', projectTitle: 'Crop Disease Detection', timestamp: '2025-04-15T10:00:00Z', details: 'Appeal on Completeness score' },
    { id: 'a4', type: 'published', studentName: 'Arjun Patel', projectTitle: 'Blockchain Credentials', timestamp: '2025-04-11T11:00:00Z', details: 'Report published to student' },
    { id: 'a5', type: 'flagged', studentName: 'Rahul Singh', projectTitle: 'Federated Learning Healthcare', timestamp: '2025-04-10T09:00:00Z', details: 'Similarity >40% internal flag cleared' },
  ] as ActivityItem[],
};

// ─── Mock Rubric ──────────────────────────────────────────────────────────────
export const mockRubric: Rubric = {
  rubricId: 'r001',
  name: 'CSE Final Year Project Evaluation 2025',
  department: 'CSE',
  createdBy: 'Dr. Meera Krishnan',
  isApproved: true,
  criteria: [
    { criteriaId: 'c1', name: 'Novelty', weight: 20, isRequired: true, description: 'How original and innovative is the project idea?' },
    { criteriaId: 'c2', name: 'Feasibility', weight: 15, isRequired: true, description: 'Can this be realistically implemented with available resources?' },
    { criteriaId: 'c3', name: 'Completeness', weight: 15, isRequired: true, description: 'Does the document cover all required sections?' },
    { criteriaId: 'c4', name: 'Technical Depth', weight: 20, isRequired: true, description: 'Quality of technical implementation and methodology' },
    { criteriaId: 'c5', name: 'Clarity', weight: 15, isRequired: true, description: 'Writing quality, structure, and readability' },
    { criteriaId: 'c6', name: 'Similarity Risk', weight: 5, isRequired: false, description: 'Originality vs. existing works in database' },
    { criteriaId: 'c7', name: 'Publication Potential', weight: 10, isRequired: false, description: 'Could this be published in a conference/journal?' },
  ],
  createdAt: '2025-01-15',
};

// ─── Mock Benchmarks ─────────────────────────────────────────────────────────
export const mockBenchmarks: SemesterBenchmark[] = [
  { semester: 'Even', year: 2023, avgNovelty: 68, avgFeasibility: 74, avgCompleteness: 71, avgTechnicalDepth: 70, avgClarity: 69, avgOverall: 70, topScore: 89, totalProjects: 45 },
  { semester: 'Odd', year: 2023, avgNovelty: 71, avgFeasibility: 76, avgCompleteness: 73, avgTechnicalDepth: 72, avgClarity: 71, avgOverall: 73, topScore: 91, totalProjects: 52 },
  { semester: 'Even', year: 2024, avgNovelty: 74, avgFeasibility: 78, avgCompleteness: 75, avgTechnicalDepth: 75, avgClarity: 73, avgOverall: 75, topScore: 93, totalProjects: 58 },
  { semester: 'Odd', year: 2024, avgNovelty: 76, avgFeasibility: 80, avgCompleteness: 77, avgTechnicalDepth: 78, avgClarity: 75, avgOverall: 77, topScore: 95, totalProjects: 61 },
  { semester: 'Even', year: 2025, avgNovelty: 78, avgFeasibility: 82, avgCompleteness: 79, avgTechnicalDepth: 81, avgClarity: 77, avgOverall: 79, topScore: 96, totalProjects: 38 },
];

// ─── Mock HOD Stats ────────────────────────────────────────────────────────────
export const mockHODStats: HODDeptStats = {
  totalStudents: 180,
  totalFaculty: 12,
  totalSubmissions: 152,
  reviewedCount: 118,
  avgScore: 74.2,
  domainDistribution: {
    'AI/ML': 42,
    'IoT': 28,
    'Web/App': 31,
    'Healthcare': 18,
    'Cybersecurity': 12,
    'Agriculture': 11,
    'Smart Systems': 10,
  },
  trendData: [
    { month: 'Jan', avgScore: 71 },
    { month: 'Feb', avgScore: 72 },
    { month: 'Mar', avgScore: 74 },
    { month: 'Apr', avgScore: 77 },
    { month: 'May', avgScore: 76 },
  ],
};
