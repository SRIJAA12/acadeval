import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getMyProjects } from '../../api/endpoints';
import { LoadingState, ErrorState, EmptyState } from '../../components/States';
import Badge from '../../components/Badge';
import { MessageSquare, ChevronRight, UserCircle } from 'lucide-react';

const DiscussionProjectList: React.FC = () => {
  const navigate = useNavigate();
  const { data: projects, isLoading, isError, refetch } = useQuery({
    queryKey: ['myProjects'],
    queryFn: getMyProjects,
  });

  if (isLoading) return <LoadingState message="Loading your projects..." />;
  if (isError) return <ErrorState retry={refetch} />;

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-display font-bold text-navy-900">Discussion & Progress</h1>
        <p className="text-slate-500 mt-1">Talk with your guide and post progress updates — pick a project to open its thread.</p>
      </div>

      {!projects?.length ? (
        <EmptyState
          icon={<MessageSquare size={28} />}
          title="No projects yet"
          description="Submit a project first — then you can discuss it with your guide here."
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {projects.map(project => (
            <div
              key={project.projectId}
              onClick={() => navigate(`/student/discussion/${project.projectId}`)}
              className="card-hover cursor-pointer"
            >
              <div className="flex items-center gap-2 mb-2">
                <Badge type="domain" value={project.domain} size="sm" />
                <Badge type="pipeline" value={project.pipelineStatus} size="sm" />
              </div>
              <h3 className="font-semibold text-slate-800">{project.title}</h3>
              <p className="text-xs text-slate-500 mt-2 flex items-center gap-1">
                <UserCircle size={13} /> Guide: {project.guideName || 'Not assigned yet'}
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
