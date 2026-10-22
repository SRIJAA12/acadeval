import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getMilestones, submitMilestone, reviewMilestone } from '../api/endpoints';
import { useAuth } from '../auth/AuthContext';
import { CheckCircle, Circle, Clock, RotateCcw, ListChecks } from 'lucide-react';
import clsx from 'clsx';

const STATUS_CONFIG: Record<string, { icon: React.ReactNode; className: string; label: string }> = {
  pending: { icon: <Circle size={14} />, className: 'text-slate-400 bg-slate-50 border-slate-200', label: 'Not started' },
  submitted: { icon: <Clock size={14} />, className: 'text-gold-700 bg-gold-50 border-gold-200', label: 'Awaiting review' },
  approved: { icon: <CheckCircle size={14} />, className: 'text-teal-700 bg-teal-50 border-teal-200', label: 'Approved' },
  revision_requested: { icon: <RotateCcw size={14} />, className: 'text-red-600 bg-red-50 border-red-200', label: 'Revision requested' },
};

interface Props {
  projectId: string;
  /** True for the assigned guide/HOD viewing a faculty-side page — shows the review controls. */
  canReview: boolean;
}

const MilestoneTracker: React.FC<Props> = ({ projectId, canReview }) => {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [openId, setOpenId] = useState<string | null>(null);
  const [draft, setDraft] = useState('');
  const [reviewComment, setReviewComment] = useState('');

  const { data: milestones, isLoading } = useQuery({
    queryKey: ['milestones', projectId],
    queryFn: () => getMilestones(projectId),
    enabled: !!projectId,
  });

  const submitMutation = useMutation({
    mutationFn: (milestoneId: string) => submitMilestone(milestoneId, draft),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['milestones', projectId] });
      setOpenId(null);
      setDraft('');
    },
  });

  const reviewMutation = useMutation({
    mutationFn: ({ milestoneId, approve }: { milestoneId: string; approve: boolean }) =>
      reviewMilestone(milestoneId, approve, reviewComment || undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['milestones', projectId] });
      setOpenId(null);
      setReviewComment('');
    },
  });

  if (isLoading) {
    return <div className="card animate-pulse h-40" />;
  }
  if (!milestones || milestones.length === 0) {
    return null;
  }

  const approvedCount = milestones.filter(m => m.status === 'approved').length;
  const progressPct = Math.round((approvedCount / milestones.length) * 100);

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-1">
        <h2 className="text-base font-semibold text-navy-900 flex items-center gap-2">
          <ListChecks size={18} className="text-teal-500" /> Project Progress
        </h2>
        <span className="text-sm font-bold text-navy-800">{progressPct}%</span>
      </div>
      <div className="w-full bg-slate-100 rounded-full h-1.5 mb-5 overflow-hidden">
        <div className="h-full bg-teal-500 rounded-full transition-all duration-700" style={{ width: `${progressPct}%` }} />
      </div>

      <div className="space-y-2">
        {milestones.map(m => {
          const cfg = STATUS_CONFIG[m.status] ?? STATUS_CONFIG.pending;
          const isOpen = openId === m.milestoneId;
          return (
            <div key={m.milestoneId} className="border border-slate-100 rounded-xl overflow-hidden">
              <button
                onClick={() => { setOpenId(isOpen ? null : m.milestoneId); setDraft(m.studentSubmission ?? ''); }}
                className="w-full flex items-center justify-between px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-colors text-left"
              >
                <div>
                  <p className="text-sm font-medium text-slate-800">{m.title}</p>
                  <p className="text-xs text-slate-400">{m.description}</p>
                </div>
                <span className={clsx('inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border', cfg.className)}>
                  {cfg.icon} {cfg.label}
                </span>
              </button>

              {isOpen && (
                <div className="p-4 space-y-3 bg-white animate-fade-in">
                  {m.studentSubmission && (
                    <div>
                      <p className="text-xs font-medium text-slate-500 mb-1">Submitted notes</p>
                      <p className="text-sm text-slate-700 bg-slate-50 rounded-lg p-3 border border-slate-100">{m.studentSubmission}</p>
                    </div>
                  )}
                  {m.guideComment && (
                    <div>
                      <p className="text-xs font-medium text-slate-500 mb-1">Guide feedback</p>
                      <p className="text-sm text-slate-700 bg-amber-50 rounded-lg p-3 border border-amber-100">{m.guideComment}</p>
                    </div>
                  )}

                  {!canReview && user?.role === 'student' && (
                    <div>
                      <textarea
                        value={draft}
                        onChange={e => setDraft(e.target.value)}
                        className="input text-sm"
                        rows={3}
                        placeholder="Describe your progress on this milestone..."
                      />
                      <button
                        onClick={() => submitMutation.mutate(m.milestoneId)}
                        disabled={!draft.trim() || submitMutation.isPending}
                        className="btn-primary text-sm mt-2"
                      >
                        Submit for Review
                      </button>
                    </div>
                  )}

                  {canReview && m.status === 'submitted' && (
                    <div>
                      <textarea
                        value={reviewComment}
                        onChange={e => setReviewComment(e.target.value)}
                        className="input text-sm"
                        rows={2}
                        placeholder="Optional feedback for the student..."
                      />
                      <div className="flex gap-2 mt-2">
                        <button
                          onClick={() => reviewMutation.mutate({ milestoneId: m.milestoneId, approve: true })}
                          disabled={reviewMutation.isPending}
                          className="btn-primary text-sm"
                        >
                          <CheckCircle size={14} /> Approve
                        </button>
                        <button
                          onClick={() => reviewMutation.mutate({ milestoneId: m.milestoneId, approve: false })}
                          disabled={reviewMutation.isPending}
                          className="btn-outline text-sm"
                        >
                          Request Revision
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default MilestoneTracker;
