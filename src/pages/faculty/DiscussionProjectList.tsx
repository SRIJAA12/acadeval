import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../../auth/AuthContext';
import { getAllProjects } from '../../api/endpoints';
import { LoadingState, ErrorState, EmptyState } from '../../components/States';
import Badge from '../../components/Badge';
import { MessageSquare, ChevronRight, GraduationCap, Info } from 'lucide-react';

const DiscussionProjectList: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { data: projects, isLoading, isError, refetch } = useQuery({
    queryKey: ['allProjects'],
    queryFn: getAllProjects,
    enabled: user?.role !== 'reviewer',
  });

  if (user?.role === 'reviewer') {
    return (
      <div className="card flex items-start gap-2 max-w-xl mx-auto mt-10">
        <Info size={15} className="text-slate-400 flex-shrink-0 mt-0.5" />
        <p className="text-sm text-slate-500">
          The discussion forum is between a student and their guide. As reviewer, you see progress
          updates and guide feedback from inside each project's report page.
        </p>
      </div>
    );
  }

  if (isLoading) return <LoadingState message="Loading your assigned projects..." />;
  if (isError) return <ErrorState retry={refetch} />;

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-display font-bold text-navy-900">Discussion</h1>
        <p className="text-slate-500 mt-1">Talk with your students, share feedback, and view their progress — pick a project to open its thread.</p>
      </div>

      {!projects?.length ? (
        <EmptyState
          icon={<MessageSquare size={28} />}
          title="No assigned projects yet"
          description="Once students are assigned to you and submit their project for your review, their discussion threads will appear here."
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {projects.map(project => (
            <div
              key={project.projectId}
              onClick={() => navigate(`/faculty/discussion/${project.projectId}`)}
              className="card-hover cursor-pointer"
            >
              <div className="flex items-center gap-2 mb-2">
                <Badge type="domain" value={project.domain} size="sm" />
                <Badge type="pipeline" value={project.pipelineStatus} size="sm" />
              </div>
              <h3 className="font-semibold text-slate-800">{project.title}</h3>
              <p className="text-xs text-slate-500 mt-2 flex items-center gap-1">
                <GraduationCap size={13} /> {project.studentName} · {project.rollNo}
              </p>
              <div className="flex justify-end mt-3">
                <span className="flex items-center gap-1 text-teal-600 text-sm font-medium">
                  Open Discussion <ChevronRight size={15} />
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default DiscussionProjectList;
