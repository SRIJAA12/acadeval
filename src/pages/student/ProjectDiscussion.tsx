import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getMyProjects } from '../../api/endpoints';
import { LoadingState, ErrorState } from '../../components/States';
import GuideFeedbackPanel from '../../components/GuideFeedbackPanel';
import ProgressUpdateFeed from '../../components/ProgressUpdateFeed';
import DiscussionThread from '../../components/DiscussionThread';
import { ArrowLeft, UserCircle } from 'lucide-react';

const ProjectDiscussion: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  const { data: projects, isLoading, isError, refetch } = useQuery({
    queryKey: ['myProjects'],
    queryFn: getMyProjects,
  });

  if (isLoading) return <LoadingState message="Loading project..." />;
  if (isError) return <ErrorState retry={refetch} />;

  const project = projects?.find(p => p.projectId === projectId);
  if (!project) return <ErrorState message="Project not found." retry={() => navigate('/student/discussion')} />;

  return (
    <div className="max-w-4xl mx-auto space-y-5">
      <button onClick={() => navigate('/student/discussion')} className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700">
        <ArrowLeft size={15} /> All Discussions
      </button>

      <div className="card">
        <h1 className="text-xl font-display font-bold text-navy-900">{project.title}</h1>
        <p className="text-sm text-slate-500 mt-1 flex items-center gap-1">
          <UserCircle size={14} /> Guide: {project.guideName || 'Not assigned yet'}
        </p>
      </div>

      <GuideFeedbackPanel projectId={project.projectId} editable={false} />
      <ProgressUpdateFeed projectId={project.projectId} canPost={true} />
      <DiscussionThread projectId={project.projectId} />
    </div>
  );
};

export default ProjectDiscussion;
