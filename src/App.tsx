import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './auth/AuthContext';
import RoleGuard from './auth/RoleGuard';

// Layouts
import StudentLayout from './layouts/StudentLayout';
import FacultyLayout from './layouts/FacultyLayout';
import HODLayout from './layouts/HODLayout';

// Auth
import Login from './pages/auth/Login';

// Student pages
import Upload from './pages/student/Upload';
import MyReports from './pages/student/MyReports';
import ReportDetail from './pages/student/ReportDetail';
import VivaSimulation from './pages/student/VivaSimulation';
import Leaderboard from './pages/student/Leaderboard';
import Appeals from './pages/student/Appeals';

// Faculty pages
import Dashboard from './pages/faculty/Dashboard';
import StudentSubmissionsList from './pages/faculty/StudentSubmissionsList';
import ReviewQueue from './pages/faculty/ReviewQueue';
import ProjectReportView from './pages/faculty/ProjectReportView';
import UploadBatch from './pages/faculty/UploadBatch';
import ComparisonTable from './pages/faculty/ComparisonTable';
import RubricBuilder from './pages/faculty/RubricBuilder';
import AppealsInbox from './pages/faculty/AppealsInbox';
import HistoricalBenchmark from './pages/faculty/HistoricalBenchmark';
import PendingReviewQueue from './pages/faculty/PendingReviewQueue';
import { GraphExplorerView } from './pages/faculty/GraphExplorerView';

// HOD pages
import DeptOverview from './pages/hod/DeptOverview';
import HODProjectList from './pages/hod/HODProjectList';
import RubricManagement from './pages/hod/RubricManagement';
import LeaderboardAdmin from './pages/hod/LeaderboardAdmin';
import UserManagement from './pages/hod/UserManagement';

// Toast for unauthorized redirect
const UnauthorizedToast: React.FC = () => {
  const location = useLocation();
  const [show, setShow] = React.useState(false);

  useEffect(() => {
    if ((location.state as { unauthorized?: boolean })?.unauthorized) {
      setShow(true);
      const t = setTimeout(() => setShow(false), 4000);
      return () => clearTimeout(t);
    }
  }, [location]);

  if (!show) return null;

  return (
    <div className="toast">
      <div className="w-8 h-8 rounded-lg bg-red-50 flex items-center justify-center flex-shrink-0">
        <svg className="w-4 h-4 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v3m0 3h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
        </svg>
      </div>
      <p className="text-sm font-medium text-slate-700">You don't have access to that page</p>
    </div>
  );
};

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000,
      retry: 1,
    },
  },
});

const AppRoutes: React.FC = () => {
  const { user } = useAuth();

  return (
    <>
      <UnauthorizedToast />
      <Routes>
        {/* Public */}
        <Route path="/login" element={<Login />} />
        <Route path="/" element={
          user
            ? <Navigate to={
                user.role === 'student' ? '/student/reports' :
                user.role === 'hod' ? '/hod/overview' : '/faculty/dashboard'
              } replace />
            : <Navigate to="/login" replace />
        } />

        {/* Student Routes */}
        <Route path="/student/*" element={
          <RoleGuard allowedRoles={['student']}>
            <StudentLayout>
              <Routes>
                <Route path="upload" element={<Upload />} />
                <Route path="reports" element={<MyReports />} />
                <Route path="report/:projectId" element={<ReportDetail />} />
                <Route path="viva" element={<VivaSimulation />} />
                <Route path="leaderboard" element={<Leaderboard />} />
                <Route path="appeals" element={<Appeals />} />
                <Route path="profile" element={
                  <div className="card max-w-md mx-auto mt-8 text-center py-10">
                    <div className="w-20 h-20 rounded-full bg-teal-500 flex items-center justify-center text-white font-bold text-3xl mx-auto mb-4">
                      {user?.name?.charAt(0)}
                    </div>
                    <h2 className="text-xl font-semibold text-navy-900">{user?.name}</h2>
                    <p className="text-slate-500 text-sm mt-1">{user?.email}</p>
                    <span className="badge badge-teal mt-3 mx-auto">Student</span>
                  </div>
                } />
                <Route path="" element={<Navigate to="reports" replace />} />
              </Routes>
            </StudentLayout>
          </RoleGuard>
        } />

        {/* Faculty Routes (Guide + Reviewer) */}
        <Route path="/faculty/*" element={
          <RoleGuard allowedRoles={['guide', 'reviewer']}>
            <FacultyLayout>
              <Routes>
                <Route path="dashboard" element={<Dashboard />} />
                <Route path="submissions" element={<StudentSubmissionsList />} />
                <Route path="queue" element={<ReviewQueue />} />
                <Route path="report/:projectId" element={<ProjectReportView />} />
                <Route path="batch" element={<UploadBatch />} />
                <Route path="comparison" element={<ComparisonTable />} />
                <Route path="rubric" element={<RubricBuilder />} />
                <Route path="appeals" element={<AppealsInbox />} />
                <Route path="benchmarks" element={<HistoricalBenchmark />} />
                <Route path="entity-review" element={<PendingReviewQueue />} />
                <Route path="graph-explorer" element={<GraphExplorerView />} />
                <Route path="" element={<Navigate to="dashboard" replace />} />
              </Routes>
            </FacultyLayout>
          </RoleGuard>
        } />

        {/* HOD Routes */}
        <Route path="/hod/*" element={
          <RoleGuard allowedRoles={['hod']}>
            <HODLayout>
              <Routes>
                <Route path="overview" element={<DeptOverview />} />
                <Route path="projects" element={<HODProjectList />} />
                <Route path="report/:projectId" element={<ProjectReportView />} />
                <Route path="rubrics" element={<RubricManagement />} />
                <Route path="leaderboard" element={<LeaderboardAdmin />} />
                <Route path="users" element={<UserManagement />} />
                <Route path="" element={<Navigate to="overview" replace />} />
              </Routes>
            </HODLayout>
          </RoleGuard>
        } />

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
};

const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
};

export default App;
