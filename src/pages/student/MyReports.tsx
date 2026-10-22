import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getMyProjects, deleteProject, submitToGuide, markReadyForReview } from '../../api/endpoints';
import { LoadingState, ErrorState, EmptyState } from '../../components/States';
import Badge from '../../components/Badge';
import {
  FileText, Upload, ChevronRight, Clock, Cpu, CheckCircle, Trash2, Loader2, AlertTriangle,
  ExternalLink, UserCircle, Send, Flag, Lock,
} from 'lucide-react';
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
  isDeleting: boolean;
  onSubmitToGuide: (e: React.MouseEvent) => void;
  onMarkReadyForReview: (e: React.MouseEvent) => void;
  isSubmittingToGuide: boolean;
  isMarkingReady: boolean;
}> = ({
  project, onClick, onDelete, isDeleting,
  onSubmitToGuide, onMarkReadyForReview, isSubmittingToGuide, isMarkingReady,
}) => {
  const stepIndex = statusSteps.indexOf(project.pipelineStatus);
  const isReviewed = project.pipelineStatus === 'reviewed';
  const isFailed = project.pipelineStatus === 'failed';
  const canSubmit = project.overallScore !== null && project.overallScore > 30;

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
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2">
            <span className="flex items-center gap-1 text-xs text-slate-500">
              <UserCircle size={13} /> Guide: {project.guideName || 'Not assigned yet'}
            </span>
            {project.reviewerName && (
              <span className="flex items-center gap-1 text-xs text-slate-500">
                <UserCircle size={13} /> Reviewer: {project.reviewerName}
              </span>
            )}
            {project.githubUrl && (
              <a
                href={project.githubUrl}
                target="_blank"
                rel="noreferrer"
                onClick={e => e.stopPropagation()}
                className="flex items-center gap-1 text-xs text-teal-600 hover:text-teal-700"
              >
                <ExternalLink size={13} /> Repository
              </a>
            )}
          </div>
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

          {/* Delete Button */}
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

      {/* Status message */}
      {isFailed && (
        <div className="bg-red-50 border border-red-100 rounded-xl p-3 flex items-start gap-2">
          <AlertTriangle size={14} className="text-red-600 flex-shrink-0 mt-0.5" />
          <p className="text-xs text-red-700">
            <strong>Evaluation Failed</strong> — Something went wrong while scoring this submission. Contact your guide or try re-submitting.
          </p>
        </div>
      )}
      {!isReviewed && !isFailed && project.pipelineStatus === 'awaiting_review' && project.overallScore !== null && (
        <div className="bg-gold-50 border border-gold-100 rounded-xl p-3 flex items-start gap-2">
          <Clock size={14} className="text-gold-600 flex-shrink-0 mt-0.5" />
          <p className="text-xs text-gold-700">
            <strong>Preliminary Score Ready</strong> — Your AI-generated score and feedback are already visible below.
            Awaiting guide/reviewer finalization for the official grade.
          </p>
        </div>
      )}

      {/* Submit to Guide / Mark Ready for Review — private by default until the student acts */}
      {!isFailed && project.overallScore !== null && (
        <div className="flex flex-wrap items-center gap-2 mt-3 pt-3 border-t border-slate-100" onClick={e => e.stopPropagation()}>
          {project.guideSubmittedAt ? (
            <span className="flex items-center gap-1 text-xs text-teal-700 bg-teal-50 border border-teal-200 px-2.5 py-1 rounded-lg">
              <CheckCircle size={11} /> Submitted to guide
            </span>
          ) : (
            <button
              onClick={onSubmitToGuide}
              disabled={!canSubmit || isSubmittingToGuide}
              title={!canSubmit ? 'Score must be above 30 to submit' : undefined}
              className="flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-lg border border-teal-200 text-teal-700 bg-white hover:bg-teal-50 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {isSubmittingToGuide ? <Loader2 size={11} className="animate-spin" /> : <Send size={11} />} Submit to Guide
            </button>
          )}

          {project.reviewerReadyAt ? (
            <span className="flex items-center gap-1 text-xs text-indigo-700 bg-indigo-50 border border-indigo-200 px-2.5 py-1 rounded-lg">
              <CheckCircle size={11} /> Ready for review
            </span>
          ) : (
            <button
              onClick={onMarkReadyForReview}
              disabled={!canSubmit || isMarkingReady}
              title={!canSubmit ? 'Score must be above 30 to mark ready' : undefined}
              className="flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-lg border border-indigo-200 text-indigo-700 bg-white hover:bg-indigo-50 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {isMarkingReady ? <Loader2 size={11} className="animate-spin" /> : <Flag size={11} />} Mark Ready for Review
            </button>
          )}

          {!canSubmit && (
            <span className="flex items-center gap-1 text-[11px] text-slate-400">
              <Lock size={11} /> Score must be above 30 to submit
            </span>
          )}
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

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (confirm('Are you sure you want to delete this submitted project? This action cannot be undone.')) {
      deleteMutation.mutate(id);
    }
  };

  const submitToGuideMutation = useMutation({
    mutationFn: (id: string) => submitToGuide(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['myProjects'] }),
    onError: (err: any) => alert(err.response?.data?.detail || 'Failed to submit to guide.'),
  });

  const markReadyMutation = useMutation({
    mutationFn: (id: string) => markReadyForReview(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['myProjects'] }),
    onError: (err: any) => alert(err.response?.data?.detail || 'Failed to mark ready for review.'),
  });

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
              isDeleting={deletingId === project.projectId}
              onSubmitToGuide={() => submitToGuideMutation.mutate(project.projectId)}
              onMarkReadyForReview={() => markReadyMutation.mutate(project.projectId)}
              isSubmittingToGuide={submitToGuideMutation.isPending && submitToGuideMutation.variables === project.projectId}
              isMarkingReady={markReadyMutation.isPending && markReadyMutation.variables === project.projectId}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default MyReports;
