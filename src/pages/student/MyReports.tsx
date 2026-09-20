import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getMyProjects, deleteProject, reprocessProject, getPipelineStatus } from '../../api/endpoints';
import { LoadingState, ErrorState, EmptyState } from '../../components/States';
import Badge from '../../components/Badge';
import { FileText, Upload, ChevronRight, Clock, Cpu, CheckCircle, Trash2, Loader2, RefreshCw } from 'lucide-react';
import type { ProjectSummary } from '../../types';
import clsx from 'clsx';

const statusSteps = ['uploaded', 'ai_processing', 'awaiting_review', 'reviewed'];
const statusLabels: Record<string, string> = {
  uploaded: 'Uploaded',
  ai_processing: 'AI Processing',
  awaiting_review: 'Awaiting Review',
  reviewed: 'Reviewed',
};

const ProjectCard: React.FC<{
  project: ProjectSummary;
  onClick: () => void;
  onDelete: (e: React.MouseEvent) => void;
  onReprocess: (e: React.MouseEvent) => void;
  isDeleting: boolean;
  isReprocessing: boolean;
}> = ({ project, onClick, onDelete, onReprocess, isDeleting, isReprocessing }) => {
  const stepIndex = statusSteps.indexOf(project.pipelineStatus);
  const isReviewed = project.pipelineStatus === 'reviewed';
  const isProcessing = project.pipelineStatus === 'ai_processing' || project.pipelineStatus === 'uploaded';

  // Poll live pipeline status if in processing
  const { data: pipelineData } = useQuery({
    queryKey: ['pipelineStatus', project.projectId],
    queryFn: () => getPipelineStatus(project.projectId),
    enabled: isProcessing,
    refetchInterval: isProcessing ? 3000 : false,
  });

  const stepDetail = pipelineData?.pipeline_step_detail;

  return (
    <div className="card-hover cursor-pointer relative group" onClick={onClick}>
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <Badge type="submission" value={project.submissionType} size="sm" />
            <Badge type="domain" value={project.domain} size="sm" />
          </div>
          <h3 className="font-semibold text-slate-800 text-base leading-snug">{project.title}</h3>
          <p className="text-sm text-slate-400 mt-1">Submitted {new Date(project.submittedOn).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</p>
        </div>
        
        <div className="flex flex-col items-end gap-2">
          {project.overallScore !== null ? (
            <div className="flex-shrink-0 text-center">
              <div className={clsx(
                'w-14 h-14 rounded-2xl flex items-center justify-center font-display font-bold text-xl',
                project.overallScore >= 80 ? 'bg-teal-50 text-teal-700' :
                project.overallScore >= 60 ? 'bg-gold-50 text-gold-700' : 'bg-red-50 text-red-700'
              )}>
                {project.overallScore}
              </div>
              <p className="text-xs text-slate-400 mt-1">/ 100</p>
            </div>
          ) : (
            <div className="w-14 h-14 rounded-2xl bg-slate-100 flex items-center justify-center flex-shrink-0">
              <Cpu size={22} className="text-slate-400 animate-pulse-soft" />
            </div>
          )}

          {/* Action buttons */}
          <div className="flex items-center gap-1">
            <button
              onClick={onReprocess}
              disabled={isReprocessing}
              title="Re-run AI Evaluation"
              className="p-1.5 text-slate-400 hover:text-purple-600 hover:bg-purple-50 rounded-lg transition-colors"
            >
              <RefreshCw size={15} className={clsx(isReprocessing && "animate-spin text-purple-600")} />
            </button>
            <button
              onClick={onDelete}
              disabled={isDeleting}
              title="Delete Project"
              className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            >
              {isDeleting ? <Loader2 size={16} className="animate-spin text-red-600" /> : <Trash2 size={16} />}
            </button>
          </div>
        </div>
      </div>

      {/* Pipeline progress */}
      <div className="mb-4">
        <div className="flex items-center gap-0">
          {statusSteps.map((step, i) => (
            <React.Fragment key={step}>
              <div className={clsx(
                'flex items-center justify-center w-7 h-7 rounded-full text-xs font-semibold transition-colors flex-shrink-0',
                i < stepIndex ? 'bg-teal-500 text-white' :
                i === stepIndex ? 'bg-teal-100 text-teal-700 ring-2 ring-teal-500' :
                'bg-slate-100 text-slate-400'
              )}>
                {i < stepIndex ? <CheckCircle size={14} /> : i + 1}
              </div>
              {i < statusSteps.length - 1 && (
                <div className={clsx('flex-1 h-0.5', i < stepIndex ? 'bg-teal-500' : 'bg-slate-100')} />
              )}
            </React.Fragment>
          ))}
        </div>
        <div className="flex justify-between mt-1.5">
          {statusSteps.map(step => (
            <span key={step} className={clsx(
              'text-[9px] font-medium',
              step === project.pipelineStatus ? 'text-teal-600' : 'text-slate-300'
            )}>
              {statusLabels[step]}
            </span>
          ))}
        </div>
      </div>

      {/* Step level progress detail banner */}
      {stepDetail && isProcessing && (
        <div className="mb-3 bg-purple-50 border border-purple-100 rounded-xl p-2.5 flex items-center justify-between text-xs text-purple-800">
          <div className="flex items-center gap-2">
            <Loader2 size={13} className="animate-spin text-purple-600 flex-shrink-0" />
            <span className="font-medium">{stepDetail.label}</span>
          </div>
          <span className="text-purple-600 font-bold">{stepDetail.step_number}/{stepDetail.total_steps}</span>
        </div>
      )}

      {/* Status message */}
      {!isReviewed && project.pipelineStatus === 'awaiting_review' && project.overallScore !== null && (
        <div className="bg-gold-50 border border-gold-100 rounded-xl p-3 flex items-start gap-2">
          <Clock size={14} className="text-gold-600 flex-shrink-0 mt-0.5" />
          <p className="text-xs text-gold-700">
            <strong>AI Draft Ready</strong> — Your AI-generated report is available as a preliminary view.
            Awaiting guide/reviewer finalization before full report is released.
          </p>
        </div>
      )}

      <div className="flex items-center justify-between mt-4">
        <Badge type="pipeline" value={project.pipelineStatus} />
        <button className="flex items-center gap-1 text-teal-600 text-sm font-medium hover:text-teal-700">
          {isReviewed ? 'View Full Report' : 'View Preliminary'} <ChevronRight size={15} />
        </button>
      </div>
    </div>
  );
};

const MyReports: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [reprocessingId, setReprocessingId] = useState<string | null>(null);

  const { data: projects, isLoading, isError, refetch } = useQuery({
    queryKey: ['myProjects'],
    queryFn: getMyProjects,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteProject(id),
    onMutate: (id) => setDeletingId(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['myProjects'] });
      queryClient.invalidateQueries({ queryKey: ['allProjects'] });
    },
    onError: () => alert('Failed to delete project.'),
    onSettled: () => setDeletingId(null),
  });

  const reprocessMutation = useMutation({
    mutationFn: (id: string) => reprocessProject(id),
    onMutate: (id) => setReprocessingId(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['myProjects'] });
      queryClient.invalidateQueries({ queryKey: ['allProjects'] });
    },
    onError: () => alert('Failed to trigger reprocessing.'),
    onSettled: () => setReprocessingId(null),
  });

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (confirm('Are you sure you want to delete this submitted project? This action cannot be undone.')) {
      deleteMutation.mutate(id);
    }
  };

  const handleReprocess = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    reprocessMutation.mutate(id);
  };

  if (isLoading) return <LoadingState message="Loading your submissions..." />;
  if (isError) return <ErrorState retry={refetch} />;

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-display font-bold text-navy-900">My Reports</h1>
          <p className="text-slate-500 mt-1">Track your project submissions and evaluation status</p>
        </div>
        <button onClick={() => navigate('/student/upload')} className="btn-primary">
          <Upload size={16} /> New Submission
        </button>
      </div>

      {!projects?.length ? (
        <EmptyState
          icon={<FileText size={28} />}
          title="No submissions yet"
          description="Submit your first project to get AI-powered evaluation with radar charts, improvement roadmap, and viva preparation."
          action={
            <button onClick={() => navigate('/student/upload')} className="btn-primary">
              <Upload size={16} /> Submit Project
            </button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {projects.map(project => (
            <ProjectCard
              key={project.projectId}
              project={project}
              onClick={() => navigate(`/student/report/${project.projectId}`)}
              onDelete={(e) => handleDelete(e, project.projectId)}
              onReprocess={(e) => handleReprocess(e, project.projectId)}
              isDeleting={deletingId === project.projectId}
              isReprocessing={reprocessingId === project.projectId}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default MyReports;
